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
app.secret_key = os.getenv("SECRET_KEY", "your-secret-key")  # Needed for session and flash

# Hardcoded admin credentials (replace with secure storage in production)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = generate_password_hash("your-admin-password")  # Replace with your password

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
                logger.warning("Missing required fields in feedback form.")
                return render_template("feedback.html", message="All fields except photo are required.")

            # Prepare feedback item for Cosmos DB
            feedback_item = {
                "id": str(hash(comment + route)),  # Unique ID
                "route": route,
                "stop": stop,
                "issue_type": issue_type,
                "comment": comment,
                "date": datetime.utcnow().isoformat(),
                "photo": photo.filename if photo else None,
                "status": "pending"  # New field to track approval
            }

            # Handle photo upload (placeholder for now)
            photo_url = None
            if photo:
                logger.info(f"Photo uploaded: {photo.filename}")
                photo_url = photo.filename  # Replace with Azure Blob Storage URL later
                feedback_item["photo"] = photo_url

            # Save to Cosmos DB
            if container:
                try:
                    container.create_item(body=feedback_item)
                    logger.info(f"Feedback saved: {feedback_item}")
                except exceptions.CosmosHttpResponseError as e:
                    logger.error(f"Error saving feedback: {str(e)}")
                    return render_template("feedback.html", message="Error saving feedback to database.")

            return redirect(url_for('thank_you'))

        except Exception as e:
            logger.error(f"Unexpected error in feedback submission: {str(e)}")
            return render_template("feedback.html", message="An unexpected error occurred.")
    
    return render_template("feedback.html")

@app.route('/thank_you')
def thank_you():
    return render_template("thank_you.html")

@app.route('/suggestions')
def suggestions():
    return render_template("suggestions.html")

@app.route('/maintenance')
def maintenance():
    return render_template("maintenance.html")

@app.route('/track_status', methods=['GET', 'POST'])
def track_status():
    try:
        # Get current date and time
        current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        status_message = f"Current Status as of {current_time}: All submissions are being reviewed."

        # Handle feedback approval (POST request)
        if request.method == 'POST' and session.get('logged_in'):
            feedback_id = request.form.get('feedback_id')
            if feedback_id and container:
                try:
                    # Update status to approved
                    item = container.read_item(item=feedback_id, partition_key=feedback_id)
                    item["status"] = "approved"
                    container.replace_item(item=feedback_id, body=item)
                    logger.info(f"Feedback {feedback_id} approved.")
                except exceptions.CosmosHttpResponseError as e:
                    logger.error(f"Error approving feedback: {str(e)}")

        # Fetch pending feedback
        feedback_list = []
        if container:
            try:
                query = "SELECT * FROM c WHERE c.status = 'pending'"
                feedback_list = list(container.query_items(query=query, enable_cross_partition_query=True))
                logger.info(f"Fetched {len(feedback_list)} pending feedback items.")
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
        # Fetch approved feedback
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
