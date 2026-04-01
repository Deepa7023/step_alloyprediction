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
    libglu1-mesa \
    libxmu6 \
    gmsh \
    libgl1-mesa-dri \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set environment variables for production performance and RAM stability
ENV PORT=5000
ENV FLASK_APP=backend.app:app
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV MALLOC_ARENA_MAX=2

# Expose port
EXPOSE 5000

# Start command with reduced concurrency and increased timeout for the 512MB RAM floor
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "2", "--timeout", "300", "--preload", "backend.app:app"]
