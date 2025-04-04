FROM python:3.10-slim

WORKDIR /app

# Install system dependencies including ffmpeg with all required libraries and git
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libavcodec-extra \
    libavformat-dev \
    libavutil-dev \
    libswresample-dev \
    libavdevice-dev \
    libavfilter-dev \
    libsndfile1 \
    build-essential \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && ldconfig  # Refresh the dynamic linker cache

# Copy requirements first for better caching
COPY requirements.txt .

# Upgrade pip and install dependencies
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn==21.2.0

# Copy application code
COPY . .

# Verify FFmpeg installation and libraries
RUN python -c "import subprocess; subprocess.run(['ffmpeg', '-version'], check=True); print('FFmpeg verification successful')" && \
    echo "Checking for FFmpeg libraries..." && \
    ls -la /usr/lib/x86_64-linux-gnu/libav* /usr/lib/x86_64-linux-gnu/libsw* || true

# Create a test script to verify torchaudio can access FFmpeg
RUN echo 'import torch\nimport torchaudio\nprint("PyTorch version:", torch.__version__)\nprint("Torchaudio version:", torchaudio.__version__)\nprint("Checking torchaudio FFmpeg availability...")\ntry:\n    torchaudio.utils.ffmpeg_utils.get_video_metadata("nonexistent.mp4")\n    print("FFmpeg libraries found by torchaudio")\nexcept FileNotFoundError:\n    print("File not found error - expected for nonexistent file")\nexcept ImportError as e:\n    print("ImportError:", str(e))\n    exit(1)\nexcept Exception as e:\n    print("Other error:", str(e))\n    if "FFmpeg" in str(e):\n        exit(1)' > /tmp/test_torchaudio.py && \
    python /tmp/test_torchaudio.py || echo "WARNING: torchaudio FFmpeg test failed but continuing build"

# Create necessary directories
RUN mkdir -p clips uploads transcriptions instance

# Set environment variables
ENV PORT=5000
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV LD_LIBRARY_PATH=/usr/local/lib:/usr/lib:/lib
EXPOSE 5000

# Make the prestart script executable
RUN chmod +x prestart.sh

# Command to run with health check
CMD ./prestart.sh && gunicorn main:app --bind 0.0.0.0:${PORT} --timeout 120 --workers 2 --threads 2 --max-requests 1000 --max-requests-jitter 50 --log-level info --preload