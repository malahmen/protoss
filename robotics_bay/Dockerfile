# Base Python image
ARG PYTHON_VERSION=python:3.11-slim
FROM ${PYTHON_VERSION}

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
EXPOSE 8000

# Run the API
CMD ["uvicorn", "robotics_bay.disruptor:app", "--host", "0.0.0.0", "--port", "8000"]

# for debuging 
#CMD ["sh", "-c", "python ./robotics-bay/disruptor.py || sleep infinity"]
