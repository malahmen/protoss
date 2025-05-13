# Base Python image
ARG PYTHON_VERSION=python:3.11-slim
FROM ${PYTHON_VERSION}

# Set API port argument and environment variable
ARG API_PORT=8000
ENV API_PORT=${API_PORT}

# Set working directory
WORKDIR /carrier

# Install system dependencies
RUN apt-get update && apt-get install -y libmagic1

# Set PYTHONPATH so imports from /carrier work
ENV PYTHONPATH=/carrier

# Copy the required project files - might be possible to replace /carrier by .
COPY pylon/ /carrier/pylon
COPY robotics_bay/ /carrier/robotics_bay
COPY .env /carrier/.env

RUN pip install --no-cache-dir -r /carrier/robotics_bay/requirements.txt

# Expose FastAPI port (optional but good practice)
EXPOSE ${API_PORT}

# Run the API
CMD ["sh", "-c", "uvicorn robotics_bay.disruptor:app --host 0.0.0.0 --port ${API_PORT}"]

# for debuging 
#CMD ["sh", "-c", "python ./robotics-bay/disruptor.py || sleep infinity"]
