from flask import Flask, render_template

app = Flask(__name__, template_folder="TransitFeedbackCollect/templates", static_folder="TransitFeedbackCollect/static")

# Route to serve the main page
@app.route('/')
def home():
    return render_template("index.html")

# Routes for other HTML pages
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
    return render_template("track_status.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
