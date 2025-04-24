import logging
from flask import Flask, request, jsonify
from functools import wraps
import time

# Local imports
from utils import validate_request_data, setup_logging
from mastodon_service import get_mastodon_posts
from sentiment_service import analyze_sentiment
from summary_service import generate_summary_and_keywords
from config import HOST, PORT

# Set up logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Middleware for request logging and timing
@app.before_request
def log_request_info():
    app.logger.info(f"Request: {request.method} {request.path} from {request.remote_addr}")
    request.start_time = time.time()

# Middleware for response logging and timing
@app.after_request
def log_response_info(response):
    if hasattr(request, 'start_time'):
        duration = time.time() - request.start_time
        app.logger.info(f"Response time: {duration:.2f}s, Status: {response.status_code}")
    return response

# Error handling decorator
def handle_errors(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.exception("Unexpected error")
            return jsonify({"error": "Internal server error", "details": str(e)}), 500
    return decorated_function

# Main analyze endpoint
@app.route('/analyze', methods=['POST'])
@handle_errors
def analyze():
    # Get and validate request data
    data = request.get_json(force=True)
    validated_data = validate_request_data(data)
    
    keyword = validated_data["text"]
    max_results = validated_data["maxResults"]
    
    logger.info(f"Received request to analyze '{keyword}' with max_results={max_results}")
    
    # Fetch Mastodon posts
    try:
        posts = get_mastodon_posts(keyword, max_results=max_results)
    except Exception as e:
        return jsonify({"error": "Mastodon fetch error", "details": str(e)}), 502

    if not posts:
        return jsonify({"error": f"No Mastodon posts found for '{keyword}'."}), 200

    # Analyze sentiment
    sentiment_results = analyze_sentiment(posts, time_interval='day')

    # Generate summary and keywords
    summary_text, related_keywords = generate_summary_and_keywords(posts, keyword)
    
    # Return the results
    return jsonify({
    "summary": summary_text,
    "sentiment": sentiment_results["overall"],
    "sentimentOverTime": sentiment_results["overTime"],
    "relatedKeywords": related_keywords
})

if __name__ == '__main__':
    logger.info(f"Starting server on {HOST}:{PORT}")
    app.run(host=HOST, port=PORT)
