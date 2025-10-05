# Use a lightweight Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (ffmpeg for pydub)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Copy requirement files first to leverage Docker caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your app
COPY . .

# Expose port Dash runs on
EXPOSE 8050

# Set environment variables (these can be overridden at runtime)
ENV PORT=8050
ENV HOST=0.0.0.0

# Run the Dash app
CMD ["python", "app.py"]


# docker build -t multivoice-rpg .
# docker run -p 8050:8050 --env-file .env multivoice-rpg
