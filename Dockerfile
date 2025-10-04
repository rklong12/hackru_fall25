# Use a lightweight Python image
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Install system dependencies needed for HTTPS requests
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies file first (caching)
COPY requirements.txt ./

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy all app files into container
COPY . .

# Create folder for cached audio (defensive)
# RUN mkdir -p /app/audio_cache

# Expose port Dash will run on
EXPOSE 8050

# Command to run the app
CMD ["python", "app.py"]


# docker build -t adventure-rpg .
# docker run --env-file .env -p 8050:8050 adventure-rpg
