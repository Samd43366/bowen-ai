# Use official Python 3.11 slim image for minimal footprint
FROM python:3.11-slim

# Set environment variables natively to optimize python execution
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python requirements first As Root globally
COPY requirement.txt .
RUN pip install --no-cache-dir -r requirement.txt

# --- HUGGING FACE SPACES SPECIFIC SETUP ---
# Create an unprivileged user (UID 1000) for security
RUN useradd -m -u 1000 user

# Switch to the new secure user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Pre-cache the Sentence Transformer Model
# This downloads the gigabytes of AI models during the 'Build' phase so the live app boots instantly
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# Copy the actual AI application into the container securely assigning ownership to 'user'
COPY --chown=user . $HOME/app

EXPOSE 7860

# Specify how to run the application
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860} --workers 4
