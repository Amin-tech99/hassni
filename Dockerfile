FROM python:3.10

WORKDIR /app

RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY . .

# Upgrade pip to the latest version
RUN python -m pip install --upgrade pip

RUN python -m venv /opt/venv && . /opt/venv/bin/activate && pip install --no-cache-dir -r requirements.txt

ENV PORT=5000
EXPOSE 5000

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000"]