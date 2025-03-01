from flask import Flask, render_template, request, redirect, url_for, flash
import os
import requests
from azure.cosmos import CosmosClient, exceptions, PartitionKey
import logging

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
    except exceptions.CosmosHttpResponseError as e:
        logger.error(f"Failed to initialize Cosmos DB: {e}")
        client = None
        container = None

# Root route
@app.route('/')
def home():
    try:
        response = requests.get("https://api.example.com/transit-status")
        transit_data = response.json()
    except requests.RequestException:
        transit_data = {"status": "Unable to fetch transit data"}
    return render_template("index.html", transit_data=transit_data)

@app.route('/index')
def index():
    return redirect(url_for('home'))

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        route = request.form.get('route')
        stop = request.form.get('stop')
        issue_type = request.form.get('issue_type')
        comment = request.form.get('comment')
        photo = request.files.get('photo')

        if not all([route, stop, issue_type, comment]):
            return render_template("feedback.html", message="All fields except photo are required.")

        # Prepare feedback item for Cosmos DB
        feedback_item = {
            "id": str(hash(comment + route)),  # Unique ID based on comment and route
            "route": route,
            "stop": stop,
            "issue_type": issue_type,
            "comment": comment,
            "date": "2025-03-01",
            "photo": photo.filename if photo else None
        }

        # Handle photo upload (optional)
        photo_url = None
        if photo:
            # In a real app, save to Azure Blob Storage and get URL
            # For now, just log the filename
            logger.info(f"Photo uploaded: {photo.filename}")
            photo_url = photo.filename  # Placeholder; replace with actual storage logic

        if container:
            try:
                container.create_item(body=feedback_item)
                logger.info(f"Feedback saved: {feedback_item}")
            except exceptions.CosmosHttpResponseError as e:
                logger.error(f"Error saving feedback: {e}")
                return render_template("feedback.html", message="Error saving feedback due to database issue.")
        
        # Flash feedback details for track_status
        feedback_display = f"Route: {route}, Stop: {stop}, Issue: {issue_type}, Comment: {comment}" + (f", Photo: {photo_url}" if photo_url else "")
        flash(feedback_display)
        return redirect(url_for('thank_you'))
    
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
    feedback = None
    flashed_messages = get_flashed_messages()
    if flashed_messages:
        feedback = flashed_messages[0]  # Display the formatted feedback
    try:
        response = requests.get("https://api.example.com/transit-status")
        status_data = response.json()
    except requests.RequestException:
        status_data = {"status": "Status unavailable"}
    return render_template("track_status.html", status_data=status_data, feedback=feedback)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=True)
