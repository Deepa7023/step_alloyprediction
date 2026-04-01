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
    libfontconfig1 \
    libxcursor1 \
    libxft2 \
    libxkbcommon0 \
    libxkbcommon-x11-0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libxinerama1 \
    libxi6 \
    libxtst6 \
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
ENV PYTHONPATH=/app

# Expose port
EXPOSE 5000

# Start command with preload and increased timeout for heavy CAD geometry engines
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "--timeout", "300", "--preload", "backend.app:app"]
