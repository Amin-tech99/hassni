FROM python:3.10-slim

WORKDIR /app

# Install system dependencies including ffmpeg and git
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    build-essential \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Upgrade pip and install dependencies
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn==21.2.0

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p clips uploads transcriptions instance

# Set environment variables
ENV PORT=5000
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
EXPOSE 5000

# Make the prestart script executable
RUN chmod +x prestart.sh

# Command to run with health check
CMD ./prestart.sh && gunicorn main:app --bind 0.0.0.0:${PORT} --timeout 120 --workers 2 --threads 2 --max-requests 1000 --max-requests-jitter 50 --log-level info --preload