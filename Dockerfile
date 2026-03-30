# Use official Python 3.10 slim image for minimal footprint
FROM python:3.10-slim

# Set environment variables natively to optimize python execution
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Create application directory
WORKDIR /app

# Install system dependencies (needed for certain python packages like PyMuPDF)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install via pip
COPY requirement.txt .
RUN pip install --no-cache-dir -r requirement.txt

# Copy all project files into the image
COPY . .

# Expose backend API port
EXPOSE 8000

# Specify how to run the application securely and scalably
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
