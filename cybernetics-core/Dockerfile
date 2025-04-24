# Base Python image
ARG PYTHON_VERSION=python:3.11-slim
FROM ${PYTHON_VERSION}

# Set working directory
WORKDIR /carrier

# Install system dependencies
RUN apt-get update && apt-get install -y libmagic1

# Install Python dependencies first (before copying all project files)
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project files
COPY . .

# Launch a sentry unit
CMD ["python", "./sentry.py"]