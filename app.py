<!DOCTYPE html>
<html>
<head>
    <title>Feedback Summary - Transit Feedback Portal</title>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap" rel="stylesheet">
    <style>
        body { background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); font-family: 'Roboto', sans-serif; color: #333; min-height: 100vh; padding: 40px 20px; }
        .container { max-width: 800px; margin: 0 auto; background: #fff; border-radius: 15px; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2); padding: 30px; }
        h1 { color: #2a5298; text-align: center; font-weight: 700; margin-bottom: 20px; font-size: 2em; }
        h2 { color: #2a5298; font-weight: 700; margin-top: 30px; margin-bottom: 15px; font-size: 1.5em; }
        p { font-size: 16px; color: #333; margin-bottom: 10px; }
        .feedback-box { background: #e8f0fe; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .feedback-box p { margin: 5px 0; }
        .back-link { text-align: center; margin-top: 20px; }
        .back-link a { color: #2a5298; text-decoration: none; font-weight: 700; transition: color 0.3s ease; }
        .back-link a:hover { color: #1e3c72; }
        img { max-width: 100%; height: auto; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Feedback Summary</h1>
        
        {% if feedback_list %}
            <h2>Approved Feedback</h2>
            {% for feedback in feedback_list %}
                <div class="feedback-box">
                    <p><strong>Type:</strong> {{ feedback.type }}</p>
                    {% if feedback.type == "Bus Feedback" %}
                        <p><strong>Route:</strong> {{ feedback.route }}</p>
                        <p><strong>Stop:</strong> {{ feedback.stop }}</p>
                        <p><strong>Issue:</strong> {{ feedback.issue_type }}</p>
                        <p><strong>Comment:</strong> {{ feedback.comment }}</p>
                    {% elif feedback.type == "Maintenance" %}
                        <p><strong>Location:</strong> {{ feedback.location }}</p>
                        <p><strong>Issue:</strong> {{ feedback.maintenance_type }}</p>
                        <p><strong>Message:</strong> {{ feedback.message }}</p>
                    {% elif feedback.type == "Suggestion" %}
                        <p><strong>Category:</strong> {{ feedback.category }}</p>
                        <p><strong>Location:</strong> {{ feedback.location }}</p>
                        <p><strong>Suggestion:</strong> {{ feedback.suggestion }}</p>
                    {% endif %}
                    <p><strong>Date:</strong> {{ feedback.date }}</p>
                    {% if feedback.photo %}
                        <p><strong>Photo:</strong></p>
                        <img src="{{ url_for('static', filename='uploads/' + feedback.photo) }}" alt="Feedback Image">
                    {% endif %}
                </div>
            {% endfor %}
        {% else %}
            <p>No approved feedback yet.</p>
        {% endif %}

        <div class="back-link">
            <a href="{{ url_for('track_status') }}">Back to Track Status</a>
        </div>
    </div>
</body>
</html>
