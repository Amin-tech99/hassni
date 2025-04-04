#!/usr/bin/env python

import os
import sys
import time
import logging
from flask import Flask, jsonify
from threading import Thread

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Create a minimal Flask app just for health checks
app = Flask(__name__)

@app.route('/health')
def health_check():
    logger.info("Health check endpoint called")
    # Always return healthy during initialization
    return jsonify({
        'status': 'healthy',
        'message': 'Service is initializing',
        'timestamp': time.time()
    }), 200

def run_server():
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting standalone health check server on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    run_server()