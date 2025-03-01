from flask import Flask, render_template, request, redirect, url_for, flash, get_flashed_messages
import os
import requests
from azure.cosmos import CosmosClient, exceptions, PartitionKey
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask setup
app = Flask(__name__, template_folder="TransitFeedbackCollect/templates", static_folder="TransitFeedbackCollect/static")
app.secret_key = os.getenv("SECRET_KEY", "your-secret-key")  # Needed for flash messages

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
                "id": str(hash(comment + route)),  # Unique ID based on comment and route
                "route": route,
                "stop": stop,
                "issue_type": issue_type,
                "comment": comment,
                "date": datetime.utcnow().isoformat(),  # Use current UTC time
                "photo": photo.filename if photo else None
            }

            # Handle photo upload (placeholder for now)
            photo_url = None
            if photo:
                logger.info(f"Photo uploaded: {photo.filename}")
                photo_url = photo.filename  # Replace with Azure Blob Storage logic later

            # Save to Cosmos DB if available
            if container:
                try:
                    container.create_item(body=feedback_item)
                    logger.info(f"Feedback saved: {feedback_item}")
                except exceptions.CosmosHttpResponseError as e:
                    logger.error(f"Error saving feedback to Cosmos DB: {str(e)}")
                    return render_template("feedback.html", message="Error saving feedback to database.")

            # No need to flash; feedback will persist in Cosmos DB
            return redirect(url_for('thank_you'))

        except Exception as e:
            logger.error(f"Unexpected error in feedback submission: {str(e)}")
            return render_template("feedback.html", message="An unexpected error occurred. Please try again.")
    
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

@app.route('/track_status')
def track_status():
    try:
        # Get current date and time
        current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        status_message = f"Current Status as of {current_time}: All submissions are being reviewed."

        # Fetch all feedback from Cosmos DB
        feedback_list = []
        if container:
            try:
                query = "SELECT * FROM c"
                items = list(container.query_items(query=query, enable_cross_partition_query=True))
                feedback_list = items
                logger.info(f"Fetched {len(feedback_list)} feedback items from Cosmos DB.")
            except exceptions.CosmosHttpResponseError as e:
                logger.error(f"Error querying feedback: {str(e)}")

        # Try to get external transit status (optional)
        try:
            response = requests.get("https://api.example.com/transit-status")
            status_data = response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch transit status: {str(e)}")
            status_data = {"status": status_message}

        return render_template("track_status.html", status_data=status_data, feedback_list=feedback_list)
    
    except Exception as e:
        logger.error(f"Error in track_status route: {str(e)}")
        return render_template("track_status.html", status_data={"status": "Error loading status"}, feedback_list=[])

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=True)
