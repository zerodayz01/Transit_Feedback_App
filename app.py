from flask import Flask, render_template, request, redirect, url_for
from azure.cosmos import CosmosClient
import os

app = Flask(__name__, template_folder="TransitFeedbackCollect/templates", static_folder="TransitFeedbackCollect/static")

# Azure Cosmos DB Configuration
COSMOS_DB_URL = os.getenv("COSMOS_DB_URL", "https://transitfeedbackdb.documents.azure.com:443/")  # Default to your Cosmos DB URI
COSMOS_DB_KEY = os.getenv("COSMOS_DB_KEY", "hlBfsP8hDXPuIa6B6unAUcVYc34vKZtVS40X0FxjqItfOhABkkM23ZxmS4y3XQTAKDAwkihN6bRnACDbN7m6JQ==")  # Default to your Primary Key
DATABASE_NAME = "TransitFeedbackDB"
CONTAINER_NAME = "Feedback"

# Initialize Cosmos DB Client
client = CosmosClient(COSMOS_DB_URL, COSMOS_DB_KEY)
database = client.create_database_if_not_exists(DATABASE_NAME)
container = database.create_container_if_not_exists(id=CONTAINER_NAME, partition_key="/type")

# Route to serve the main page
@app.route('/')
def home():
    return render_template("index.html")

# Routes for other HTML pages
@app.route('/contact_support')
def render_contact_support():
    return render_template("contact_support.html")

@app.route('/feedback')
def render_feedback():
    return render_template("feedback.html")

@app.route('/feedback_summary')
def feedback_summary():
    return render_template("feedback_summary.html")

@app.route('/maintenance')
def maintenance():
    return render_template("maintenance.html")

@app.route('/suggestions')
def suggestions():
    return render_template("suggestions.html")

@app.route('/track_status')
def track_status():
    feedback_items = list(container.query_items(
        query="SELECT * FROM Feedback",
        enable_cross_partition_query=True
    ))
    return render_template("track_status.html", feedback=feedback_items)

# Feedback submission route
@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    data = request.form
    new_feedback = {
        "id": str(data.get("message")),  # Unique ID based on message content
        "type": data.get("type"),
        "message": data.get("message"),
        "status": "Not Viewed"
    }
    container.create_item(new_feedback)  # Save feedback to Cosmos DB
    return redirect(url_for("track_status"))

# Mark feedback as viewed
@app.route('/mark_as_viewed/<feedback_id>')
def mark_as_viewed(feedback_id):
    for item in container.query_items(query="SELECT * FROM Feedback", enable_cross_partition_query=True):
        if item["id"] == feedback_id:
            item["status"] = "Viewed"
            container.upsert_item(item)
            break
    return redirect(url_for("track_status"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

