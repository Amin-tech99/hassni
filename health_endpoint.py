import os
import logging
from flask import Flask, jsonify

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a minimal Flask app just for health checks
health_app = Flask(__name__)

@health_app.route('/health')
def health_check():
    logger.info("Health check endpoint called")
    return jsonify({
        'status': 'healthy',
        'message': 'Service is running'
    }), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    health_app.run(host="0.0.0.0", port=port, debug=False)