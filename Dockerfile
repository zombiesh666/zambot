# Use a slim Python image for a small footprint
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Environment variables to optimize Python for Docker
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 1. Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Copy the source code into the /app/src folder
# This matches your local structure
COPY src/ ./src/

# 3. Create the data directory for the SQLite volume
RUN mkdir -p /app/data

# 4. Set the PYTHONPATH so Python can find your modules inside /src
ENV PYTHONPATH=/app

# Expose FastAPI port
EXPOSE 8000

# 5. Updated CMD to point to the main.py inside the src directory
# Syntax: module_name:app_variable
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
