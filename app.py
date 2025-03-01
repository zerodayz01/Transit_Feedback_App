from flask import Flask, render_template, request, redirect, url_for
import os
import requests
from azure.cosmos import CosmosClient, exceptions, PartitionKey

# Flask setup
app = Flask(__name__, template_folder="TransitFeedbackCollect/templates", static_folder="TransitFeedbackCollect/static")

# Azure Cosmos DB setup
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT", "https://transitfeedbackdb.documents.azure.com:443/")
COSMOS_KEY = os.getenv("COSMOS_KEY", "hlBfsP8hDXPuIa6B6unAUcVYc34vKZtVS40X0FxjqItfOhABkkM23ZxmS4y3XQTAKDAwkihN6bRnACDbN7m6JQ==")
DATABASE_NAME = "transitfeedbackdb"  # Updated database name
CONTAINER_NAME = "Feedback"

# Initialize Cosmos DB client
client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)

# Create or get database
try:
    database = client.create_database_if_not_exists(id=DATABASE_NAME)
except exceptions.CosmosHttpResponseError as e:
    print(f"Error creating database: {e}")
    raise

# Create or get container
try:
    container = database.create_container_if_not_exists(
        id=CONTAINER_NAME,
        partition_key=PartitionKey(path="/id"),
        offer_throughput=400  # Minimum throughput
    )
except exceptions.CosmosHttpResponseError as e:
    print(f"Error creating container: {e}")
    raise

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
        feedback_text = request.form.get('feedback')
        if feedback_text:
            feedback_item = {
                "id": str(hash(feedback_text)),  # Unique ID
                "feedback": feedback_text,
                "date": "2025-03-01"  # Update as needed
            }
            try:
                container.create_item(body=feedback_item)
                message = "Feedback submitted successfully!"
            except exceptions.CosmosHttpResponseError as e:
                message = f"Error saving feedback: {e.message}"
        else:
            message = "No feedback provided."
        return render_template("feedback.html", message=message)
    return render_template("feedback.html")

@app.route('/suggestions')
def suggestions():
    return render_template("suggestions.html")

@app.route('/maintenance')
def maintenance():
    return render_template("maintenance.html")

@app.route('/track_status')
def track_status():
    try:
        response = requests.get("https://api.example.com/transit-status")
        status_data = response.json()
    except requests.RequestException:
        status_data = {"status": "Status unavailable"}
    return render_template("track_status.html", status_data=status_data)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))  # Default to 8000 for Azure
    app.run(host="0.0.0.0", port=port, debug=True)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)

