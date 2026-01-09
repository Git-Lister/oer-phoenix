# Open_Educational_Resourcer/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    postgresql-client \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first (for Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Make the entrypoint executable
RUN chmod +x docker-entrypoint.sh

# Set the entry point
ENTRYPOINT ["./docker-entrypoint.sh"]
