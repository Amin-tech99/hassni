#!/usr/bin/env python

import os
import sys
import time
import requests
from urllib.parse import urlparse

def main():
    # Get the PORT from environment or default to 5000
    port = os.environ.get("PORT", 5000)
    
    # Construct the health check URL
    health_url = f"http://localhost:{port}/health"
    
    print(f"Checking health at: {health_url}")
    
    # Try to connect with retries
    max_retries = 5
    retry_delay = 2
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"Attempt {attempt}/{max_retries}...")
            response = requests.get(health_url, timeout=5)
            
            if response.status_code == 200:
                print(f"Health check successful! Response: {response.text}")
                return 0
            else:
                print(f"Health check failed with status code: {response.status_code}")
                print(f"Response: {response.text}")
        except requests.RequestException as e:
            print(f"Connection error: {e}")
        
        if attempt < max_retries:
            print(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            retry_delay *= 1.5  # Increase delay with each retry
        else:
            print(f"Health check failed after {max_retries} attempts")
            return 1

if __name__ == "__main__":
    sys.exit(main())