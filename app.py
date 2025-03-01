from flask import Flask, render_template, request, redirect, url_for, flash, get_flashed_messages, session
import os
import requests
from azure.cosmos import CosmosClient, exceptions, PartitionKey
import logging
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask setup
app = Flask(__name__, template_folder="TransitFeedbackCollect/templates", static_folder="TransitFeedbackCollect/static")
app.secret_key = os.getenv("SECRET_KEY", "your-secret-key")

# Admin credentials
ADMIN_USERNAME = "transitadmin"
ADMIN_PASSWORD_HASH = generate_password_hash("transitadmin")  # Password: transitadmin

# Azure Cosmos DB setup
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
COSMOS_KEY = os.getenv("COSMOS_KEY")
DATABASE_NAME = "transitfeedbackdb"
CONTAINER_NAME = "Feedback"

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

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session['logged_in'] = True
            return redirect(url_for('track_status'))
        else:
            return render_template("login.html", message="Invalid credentials.")
    return render_template("login.html")

# Logout route
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('home'))

# Root route
@app.route('/')
def home():
    try:
        response = requests.get("https://api.example.com/transit-status")
        transit_data = response.json()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch transit status: {str(e)}")
        transit_data = {"status": "Unable to fetch transit data"}
    return render_template("index.html", transit_data=transit_data)

@app.route('/index')
def index():
    return redirect(url_for('home'))

# Bus Feedback route
@app.route('/feedback', methods=['GET', 'POST'])
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
                "photo": photo.filename if photo else None,
                "status": "pending"
            }

            if photo:
                photo_path = os.path.join('TransitFeedbackCollect/static/uploads', photo.filename)
                photo.save(photo_path)
                feedback_item["photo"] = photo.filename
                logger.info(f"Photo saved locally: {photo_path}")

            if container:
                try:
                    container.create_item(body=feedback_item)
                    logger.info(f"Bus Feedback saved: {feedback_item}")
                except exceptions.CosmosHttpResponseError as e:
                    logger.error(f"Error saving bus feedback: {str(e)}")
                    return render_template("feedback.html", message="Error saving feedback to database.")

            return redirect(url_for('thank_you'))

        except Exception as e:
            logger.error(f"Unexpected error in bus feedback submission: {str(e)}")
            return render_template("feedback.html", message="An unexpected error occurred.")
    
    return render_template("feedback.html")

# Maintenance route
@app.route('/maintenance', methods=['GET', 'POST'])
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
                "photo": photo.filename if photo else None,
                "status": "pending"
            }

            if photo:
                photo_path = os.path.join('TransitFeedbackCollect/static/uploads', photo.filename)
                photo.save(photo_path)
                feedback_item["photo"] = photo.filename
                logger.info(f"Photo saved locally: {photo_path}")

            if container:
                try:
                    container.create_item(body=feedback_item)
                    logger.info(f"Maintenance report saved: {feedback_item}")
                except exceptions.CosmosHttpResponseError as e:
                    logger.error(f"Error saving maintenance report: {str(e)}")
                    return render_template("maintenance.html", message="Error saving report to database.")

            return redirect(url_for('thank_you'))

        except Exception as e:
            logger.error(f"Unexpected error in maintenance submission: {str(e)}")
            return render_template("maintenance.html", message="An unexpected error occurred.")
    
    return render_template("maintenance.html")

# Suggestions route
@app.route('/suggestions', methods=['GET', 'POST'])
def suggestions():
    if request.method == 'POST':
        try:
            category = request.form.get('category')
            location = request.form.get('location', '')  # Optional field
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
                "photo": None,  # No photo field in this form
                "status": "pending"
            }

            if container:
                try:
                    container.create_item(body=feedback_item)
                    logger.info(f"Suggestion saved: {feedback_item}")
                except exceptions.CosmosHttpResponseError as e:
                    logger.error(f"Error saving suggestion: {str(e)}")
                    return render_template("suggestions.html", message="Error saving suggestion to database.")

            return redirect(url_for('thank_you'))

        except Exception as e:
            logger.error(f"Unexpected error in suggestion submission: {str(e)}")
            return render_template("suggestions.html", message="An unexpected error occurred.")
    
    return render_template("suggestions.html")

@app.route('/thank_you')
def thank_you():
    return render_template("thank_you.html")

@app.route('/track_status', methods=['GET', 'POST'])
def track_status():
    try:
        current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        status_message = f"Current Status as of {current_time}: All submissions are being reviewed."

        if request.method == 'POST' and session.get('logged_in'):
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
                if session.get('logged_in'):
                    query = "SELECT * FROM c"
                else:
                    query = "SELECT * FROM c WHERE c.status = 'pending'"
                feedback_list = list(container.query_items(query=query, enable_cross_partition_query=True))
                logger.info(f"Fetched {len(feedback_list)} feedback items.")
            except exceptions.CosmosHttpResponseError as e:
                logger.error(f"Error querying feedback: {str(e)}")

        try:
            response = requests.get("https://api.example.com/transit-status")
            status_data = response.json()
        except requests.RequestException:
            status_data = {"status": status_message}

        return render_template("track_status.html", status_data=status_data, feedback_list=feedback_list, logged_in=session.get('logged_in', False))
    
    except Exception as e:
        logger.error(f"Error in track_status: {str(e)}")
        return render_template("track_status.html", status_data={"status": "Error loading status"}, feedback_list=[])

@app.route('/feedback_summary')
def feedback_summary():
    try:
        feedback_list = []
        if container:
            try:
                query = "SELECT * FROM c WHERE c.status = 'approved'"
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
