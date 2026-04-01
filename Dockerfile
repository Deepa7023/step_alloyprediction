FROM python:3.11-slim

# Install system dependencies for OCP (OpenCascade) and OpenGL
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglx-mesa0 \
    libx11-6 \
    libxext6 \
    libxrender1 \
    libglu1-mesa \
    libsm6 \
    libice6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set environment variables
ENV PORT=5000
ENV FLASK_APP=backend.app:app

# Expose port
EXPOSE 5000

# Start command with 1 worker to stay within 512MB RAM
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "2", "backend.app:app"]
