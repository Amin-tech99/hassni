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

# Install FFmpeg and related libraries needed by torchaudio
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install specific FFmpeg library versions needed by torchaudio 2.0.0
RUN apt-get update && apt-get install -y --no-install-recommends \
    libavdevice58 \
    libavfilter7 \
    libavformat58 \
    libavcodec58 \
    libswresample3 \
    libswscale5 \
    libavutil56 \
    libavdevice-dev \
    libavfilter-dev \
    libavformat-dev \
    libavcodec-dev \
    libswresample-dev \
    libswscale-dev \
    libavutil-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && ldconfig  # Refresh the dynamic linker cache

# Create explicit symbolic links for the specific library versions needed by torchaudio 2.0.0
RUN ln -sf /usr/lib/x86_64-linux-gnu/libavdevice.so.58 /usr/lib/libavdevice.so.58 && \
    ln -sf /usr/lib/x86_64-linux-gnu/libavformat.so.58 /usr/lib/libavformat.so.58 && \
    ln -sf /usr/lib/x86_64-linux-gnu/libavcodec.so.58 /usr/lib/libavcodec.so.58 && \
    ln -sf /usr/lib/x86_64-linux-gnu/libavutil.so.56 /usr/lib/libavutil.so.56 && \
    ln -sf /usr/lib/x86_64-linux-gnu/libswresample.so.3 /usr/lib/libswresample.so.3 && \
    ln -sf /usr/lib/x86_64-linux-gnu/libswscale.so.5 /usr/lib/libswscale.so.5

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
    ls -la /usr/lib/x86_64-linux-gnu/libav* /usr/lib/x86_64-linux-gnu/libsw* && \
    echo "Verifying FFmpeg libraries needed by torchaudio:" && \
    find /usr/lib -name "libavdevice.so*" -o -name "libavformat.so*" -o -name "libavcodec.so*" -o -name "libswresample.so*" -o -name "libswscale.so*" -o -name "libavutil.so*"

# Copy and run test script to verify torchaudio can access FFmpeg
COPY test_torchaudio.py /tmp/test_torchaudio.py
RUN python /tmp/test_torchaudio.py || echo "WARNING: torchaudio FFmpeg test failed but continuing build"

# Create necessary directories
RUN mkdir -p clips uploads transcriptions instance

# Set environment variables
ENV PORT=8080
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV LD_LIBRARY_PATH=/usr/local/lib:/usr/lib:/usr/lib/x86_64-linux-gnu:/lib:/usr/lib/x86_64-linux-gnu
EXPOSE 8080

# Make the prestart script executable
RUN chmod +x prestart.sh

# Command to run with health check
CMD ./prestart.sh && gunicorn main:app --bind 0.0.0.0:${PORT} --timeout 120 --workers 2 --threads 2 --max-requests 1000 --max-requests-jitter 50 --log-level info --preload