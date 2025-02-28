from flask import Flask, render_template
import os

app = Flask(__name__, template_folder="TransitFeedbackCollect/templates", static_folder="TransitFeedbackCollect/static")

# Route to serve the main page
@app.route('/')
def home():
    return render_template("index.html")  # Ensure index.html exists in templates/

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
