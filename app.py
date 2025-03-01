from flask import Flask, render_template, request, redirect, url_for, jsonify
from azure.cosmos import CosmosClient, exceptions
import os
import logging

# Configure Logging
logging.basicConfig(level=logging.DEBUG)

# Initialize Flask App
app = Flask(__name__, template_folder="TransitFeedbackCollect/templates", static_folder="TransitFeedbackCollect/static")

# ✅ Securely Load Cosmos DB Credentials from Azure Environment Variables
COSMOS_DB_URL = os.getenv("COSMOS_DB_URL")
COSMOS_DB_KEY = os.getenv("COSMOS_DB_KEY")
DATABASE_NAME = "TransitFeedbackDB"
CONTAINER_NAME = "Feedback"

# ✅ Check if Cosmos DB Credentials Exist
if not COSMOS_DB_URL or not COSMOS_DB_KEY:
    logging.error("❌ Missing Cosmos DB credentials. Check environment variables!")
    raise Exception("Missing Cosmos DB credentials!")

# ✅ Connect to Cosmos DB
try:
    client = CosmosClient(COSMOS_DB_URL, COSMOS_DB_KEY)
    database = client.create_database_if_not_exists(DATABASE_NAME)
    container = database.create_container_if_not_exists(id=CONTAINER_NAME, partition_key="/type")
    logging.info("✅ Connected to Cosmos DB successfully!")
except exceptions.CosmosHttpResponseError as e:
    logging.error(f"❌ Failed to connect to Cosmos DB: {e}")
    raise Exception("Cosmos DB connection failed!")

# ✅ Home Page
@app.route('/')
def home():
    return render_template("index.html")

# ✅ Render Feedback Forms
@app.route('/contact_support')
def contact_support():
    return render_template("contact_support.html")

@app.route('/feedback')
def feedback():
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
    try:
        feedback_items = list(container.query_items(
            query="SELECT * FROM Feedback",
            enable_cross_partition_query=True
        ))
        return render_template("track_status.html", feedback=feedback_items)
    except Exception as e:
        logging.error(f"❌ Error retrieving feedback: {e}")
        return "Error retrieving feedback", 500

# ✅ Submit Feedback
@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    try:
        data = request.form
        new_feedback = {
            "id": str(data.get("message")),  # Unique ID
            "type": data.get("type"),
            "message": data.get("message"),
            "status": "Not Viewed"
        }
        container.create_item(new_feedback)
        logging.info("✅ Feedback submitted successfully!")
        return redirect(url_for("track_status"))
    except Exception as e:
        logging.error(f"❌ Error submitting feedback: {e}")
        return "Error submitting feedback", 500

# ✅ Mark Feedback as Viewed
@app.route('/mark_as_viewed/<feedback_id>')
def mark_as_viewed(feedback_id):
    try:
        for item in container.query_items(query="SELECT * FROM Feedback", enable_cross_partition_query=True):
            if item["id"] == feedback_id:
                item["status"] = "Viewed"
                container.upsert_item(item)
                logging.info(f"✅ Marked feedback {feedback_id} as viewed.")
                break
        return redirect(url_for("track_status"))
    except Exception as e:
        logging.error(f"❌ Error marking feedback as viewed: {e}")
        return "Error updating feedback status", 500

# ✅ Error Handler
@app.errorhandler(Exception)
def handle_exception(e):
    logging.error(f"❌ App Error: {e}")
    return jsonify({"error": "An error occurred", "message": str(e)}), 500

# ✅ Run the Flask App on Azure Port 8000 (for Gunicorn)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)

