from flask import Flask, render_template, request, redirect, url_for, flash, get_flashed_messages, session
import os
import requests
from azure.cosmos import CosmosClient, exceptions, PartitionKey
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
import msal
import logging
from datetime import datetime, timedelta
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask setup
app = Flask(__name__, template_folder="TransitFeedbackCollect/templates", static_folder="TransitFeedbackCollect/static")
app.secret_key = os.getenv("SECRET_KEY", "your-secret-key")  # Must be set for session management

# Azure AD Configuration
CLIENT_ID = os.getenv("CLIENT_ID", "a62d6b51-5c9f-43f2-82af-21c83f48eb44")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "J2s8Q~QOBntxGMunqJyvCw.E2LXdjU-3rzb-WaL3")
TENANT_ID = os.getenv("TENANT_ID", "96b500fa-a561-403a-acc4-117f2b775b7e")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
REDIRECT_URI = "https://transit-feedback-app.azurewebsites.net/auth/callback"
SCOPE = ["User.Read"]  # Basic scope for user info

# Azure Cosmos DB setup
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
COSMOS_KEY = os.getenv("COSMOS_KEY")
DATABASE_NAME = "transitfeedbackdb"
CONTAINER_NAME = "Feedback"

# Azure Blob Storage setup
BLOB_CONNECTION_STRING = os.getenv("BLOB_CONNECTION_STRING", "DefaultEndpointsProtocol=https;AccountName=transitfeedbackstorage;AccountKey=QEcGnPHAx2UYVOq4R7GNMPwxqdeC69c3lglq+fqOmkQspHL7pEgyu/8OWidZvRua+8ou4n74hNkl+AStUCjETA==;EndpointSuffix=core.windows.net")
BLOB_CONTAINER_NAME = "feedbackimages"
STORAGE_ACCOUNT_NAME = "transitfeedbackstorage"
STORAGE_ACCOUNT_KEY = "QEcGnPHAx2UYVOq4R7GNMPwxqdeC69c3lglq+fqOmkQspHL7pEgyu/8OWidZvRua+8ou4n74hNkl+AStUCjETA=="

# Validate Cosmos DB credentials
if not COSMOS_ENDPOINT or not COSMOS_KEY:
    logger.error("Missing Cosmos DB credentials! Using app without database functionality.")
    client = None
    container = None
else:
    try:
        client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
        database = client.create_database_if_not_exists(id=DATABASE_NAME)
        container = database.create_container_if_not_exists(
            id=CONTAINER_NAME,
            partition_key=PartitionKey(path="/id"),
            offer_throughput=400
        )
        logger.info("Cosmos DB initialized successfully.")
    except exceptions.CosmosHttpResponseError as e:
        logger.error(f"Failed to initialize Cosmos DB: {str(e)}")
        client = None
        container = None

# Initialize Blob Service Client
if not BLOB_CONNECTION_STRING:
    logger.error("Missing Blob Storage connection string! Photos will not be uploaded.")
    blob_service_client = None
else:
    try:
        blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)
        container_client = blob_service_client.get_container_client(BLOB_CONTAINER_NAME)
        if not container_client.exists():
            container_client.create_container()
        logger.info("Blob Storage initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize Blob Storage: {str(e)}")
        blob_service_client = None

# MSAL setup for Azure AD
msal_app = msal.ConfidentialClientApplication(
    CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET
)

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Login route
@app.route('/login')
def login():
    auth_url = msal_app.get_authorization_request_url(
        SCOPE, redirect_uri=REDIRECT_URI, response_type="code"
    )
    return redirect(auth_url)

# Callback route for Azure AD
@app.route('/auth/callback')
def auth_callback():
    code = request.args.get('code')
    if not code:
        return "Authentication failed: No code received", 400

    token = msal_app.acquire_token_by_authorization_code(
        code, scopes=SCOPE, redirect_uri=REDIRECT_URI
    )
    if "access_token" not in token:
        logger.error(f"Token acquisition failed: {token.get('error_description', 'Unknown error')}")
        return "Authentication failed", 400

    session['user'] = token['id_token_claims']  # Store user info
    logger.info(f"User logged in: {session['user'].get('preferred_username')}")
    return redirect(url_for('home'))

# Logout route
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))  # Redirect to login instead of home

# Root route
@app.route('/')
@login_required
def home():
    try:
        response = requests.get("https://api.example.com/transit-status")
        transit_data = response.json()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch transit status: {str(e)}")
        transit_data = {"status": "Unable to fetch transit data"}
    return render_template("index.html", transit_data=transit_data, user=session.get('user'))

@app.route('/index')
@login_required
def index():
    return redirect(url_for('home'))

# Bus Feedback route
@app.route('/feedback', methods=['GET', 'POST'])
@login_required
def feedback():
    if request.method == 'POST':
        try:
            route = request.form.get('route')
            stop = request.form.get('stop')
            issue_type = request.form.get('issue_type')
            comment = request.form.get('comment')
            photo = request.files.get('photo')

            if not all([route, stop, issue_type, comment]):
                logger.warning("Missing required fields in bus feedback form.")
                return render_template("feedback.html", message="All fields except photo are required.")

            feedback_item = {
                "id": str(hash(comment + route)),
                "type": "Bus Feedback",
                "route": route,
                "stop": stop,
                "issue_type": issue_type,
                "comment": comment,
                "date": datetime.utcnow().isoformat(),
                "photo": None,
                "status": "pending"
            }

            if photo and blob_service_client:
                blob_name = f"{feedback_item['id']}_{photo.filename}"
                blob_client = blob_service_client.get_blob_client(container=BLOB_CONTAINER_NAME, blob=blob_name)
                blob_client.upload_blob(photo, overwrite=True)
                sas_token = generate_blob_sas(
                    account_name=STORAGE_ACCOUNT_NAME,
                    container_name=BLOB_CONTAINER_NAME,
                    blob_name=blob_name,
                    account_key=STORAGE_ACCOUNT_KEY,
                    permission=BlobSasPermissions(read=True),
                    expiry=datetime.utcnow() + timedelta(days=365)
                )
                feedback_item["photo"] = f"{blob_client.url}?{sas_token}"
                logger.info(f"Photo uploaded to Blob Storage with SAS: {blob_name}")

            if container:
                try:
                    container.create_item(body=feedback_item)
                    logger.info(f"Bus Feedback saved: {feedback_item}")
                except exceptions.CosmosHttpResponseError as e:
                    logger.error(f"Error saving bus feedback: {str(e)}")
                    return render_template("feedback.html", message="Error saving feedback to database.")

            return redirect(url_for('thank_you', submission_type="Bus Feedback"))

        except Exception as e:
            logger.error(f"Unexpected error in bus feedback submission: {str(e)}")
            return render_template("feedback.html", message="An unexpected error occurred.")
    
    return render_template("feedback.html")

# Maintenance route
@app.route('/maintenance', methods=['GET', 'POST'])
@login_required
def maintenance():
    if request.method == 'POST':
        try:
            location = request.form.get('location')
            maintenance_type = request.form.get('maintenance_type')
            message = request.form.get('message')
            photo = request.files.get('photo')

            if not all([location, maintenance_type, message]):
                logger.warning("Missing required fields in maintenance form.")
                return render_template("maintenance.html", message="All fields except photo are required.")

            feedback_item = {
                "id": str(hash(message + location)),
                "type": "Maintenance",
                "location": location,
                "maintenance_type": maintenance_type,
                "message": message,
                "date": datetime.utcnow().isoformat(),
                "photo": None,
                "status": "pending"
            }

            if photo and blob_service_client:
                blob_name = f"{feedback_item['id']}_{photo.filename}"
                blob_client = blob_service_client.get_blob_client(container=BLOB_CONTAINER_NAME, blob=blob_name)
                blob_client.upload_blob(photo, overwrite=True)
                sas_token = generate_blob_sas(
                    account_name=STORAGE_ACCOUNT_NAME,
                    container_name=BLOB_CONTAINER_NAME,
                    blob_name=blob_name,
                    account_key=STORAGE_ACCOUNT_KEY,
                    permission=BlobSasPermissions(read=True),
                    expiry=datetime.utcnow() + timedelta(days=365)
                )
                feedback_item["photo"] = f"{blob_client.url}?{sas_token}"
                logger.info(f"Photo uploaded to Blob Storage with SAS: {blob_name}")

            if container:
                try:
                    container.create_item(body=feedback_item)
                    logger.info(f"Maintenance report saved: {feedback_item}")
                except exceptions.CosmosHttpResponseError as e:
                    logger.error(f"Error saving maintenance report: {str(e)}")
                    return render_template("maintenance.html", message="Error saving report to database.")

            return redirect(url_for('thank_you', submission_type="Maintenance"))

        except Exception as e:
            logger.error(f"Unexpected error in maintenance submission: {str(e)}")
            return render_template("maintenance.html", message="An unexpected error occurred.")
    
    return render_template("maintenance.html")

# Suggestions route
@app.route('/suggestions', methods=['GET', 'POST'])
@login_required
def suggestions():
    if request.method == 'POST':
        try:
            category = request.form.get('category')
            location = request.form.get('location', '')
            suggestion = request.form.get('suggestion')

            if not all([category, suggestion]):
                logger.warning("Missing required fields in suggestion form.")
                return render_template("suggestions.html", message="Category and suggestion are required.")

            feedback_item = {
                "id": str(hash(suggestion + category)),
                "type": "Suggestion",
                "category": category,
                "location": location,
                "suggestion": suggestion,
                "date": datetime.utcnow().isoformat(),
                "photo": None,
                "status": "pending"
            }

            if container:
                try:
                    container.create_item(body=feedback_item)
                    logger.info(f"Suggestion saved: {feedback_item}")
                except exceptions.CosmosHttpResponseError as e:
                    logger.error(f"Error saving suggestion: {str(e)}")
                    return render_template("suggestions.html", message="Error saving suggestion to database.")

            return redirect(url_for('thank_you', submission_type="Suggestion"))

        except Exception as e:
            logger.error(f"Unexpected error in suggestion submission: {str(e)}")
            return render_template("suggestions.html", message="An unexpected error occurred.")
    
    return render_template("suggestions.html")

# Contact Support route
@app.route('/contact_support', methods=['GET', 'POST'])
@login_required
def contact_support():
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            email = request.form.get('email')
            message = request.form.get('message')

            if not all([name, email, message]):
                logger.warning("Missing required fields in contact support form.")
                return render_template("contact_support.html", message="All fields are required.")

            feedback_item = {
                "id": str(hash(message + name)),
                "type": "Contact Support",
                "name": name,
                "email": email,
                "message": message,
                "date": datetime.utcnow().isoformat(),
                "photo": None,
                "status": "pending"
            }

            if container:
                try:
                    container.create_item(body=feedback_item)
                    logger.info(f"Contact support request saved: {feedback_item}")
                except exceptions.CosmosHttpResponseError as e:
                    logger.error(f"Error saving contact support request: {str(e)}")
                    return render_template("contact_support.html", message="Error saving request to database.")

            return redirect(url_for('thank_you', submission_type="Contact Support"))

        except Exception as e:
            logger.error(f"Unexpected error in contact support submission: {str(e)}")
            return render_template("contact_support.html", message="An unexpected error occurred.")
    
    return render_template("contact_support.html")

# Thank You route with dynamic message
@app.route('/thank_you')
@login_required
def thank_you():
    submission_type = request.args.get('submission_type', 'General')
    if submission_type == "Contact Support":
        thank_you_message = "A member from customer support will be in contact soon."
    else:
        thank_you_message = "Thank you for your submission!"
    return render_template("thank_you.html", message=thank_you_message, submission_type=submission_type)

@app.route('/track_status', methods=['GET', 'POST'])
@login_required
def track_status():
    try:
        current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        status_message = f"Current Status as of {current_time}: All submissions are being reviewed."

        if request.method == 'POST':
            feedback_id = request.form.get('feedback_id')
            action = request.form.get('action')
            if feedback_id and container:
                try:
                    item = container.read_item(item=feedback_id, partition_key=feedback_id)
                    if action == "approve":
                        item["status"] = "approved"
                        logger.info(f"Feedback {feedback_id} approved.")
                    elif action == "deny":
                        item["status"] = "denied"
                        logger.info(f"Feedback {feedback_id} denied.")
                    container.replace_item(item=feedback_id, body=item)
                except exceptions.CosmosHttpResponseError as e:
                    logger.error(f"Error updating feedback status: {str(e)}")

        feedback_list = []
        if container:
            try:
                query = "SELECT * FROM c WHERE c.type != 'Contact Support'"
                feedback_list = list(container.query_items(query=query, enable_cross_partition_query=True))
                logger.info(f"Fetched {len(feedback_list)} feedback items.")
            except exceptions.CosmosHttpResponseError as e:
                logger.error(f"Error querying feedback: {str(e)}")

        try:
            response = requests.get("https://api.example.com/transit-status")
            status_data = response.json()
        except requests.RequestException:
            status_data = {"status": status_message}

        return render_template("track_status.html", status_data=status_data, feedback_list=feedback_list, logged_in=True)
    
    except Exception as e:
        logger.error(f"Error in track_status: {str(e)}")
        return render_template("track_status.html", status_data={"status": "Error loading status"}, feedback_list=[])

@app.route('/feedback_summary')
@login_required
def feedback_summary():
    try:
        feedback_list = []
        if container:
            try:
                query = "SELECT * FROM c WHERE c.status = 'approved' AND c.type != 'Contact Support'"
                feedback_list = list(container.query_items(query=query, enable_cross_partition_query=True))
                logger.info(f"Fetched {len(feedback_list)} approved feedback items.")
            except exceptions.CosmosHttpResponseError as e:
                logger.error(f"Error querying approved feedback: {str(e)}")
        
        return render_template("feedback_summary.html", feedback_list=feedback_list)
    
    except Exception as e:
        logger.error(f"Error in feedback_summary: {str(e)}")
        return render_template("feedback_summary.html", feedback_list=[])

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=True)
