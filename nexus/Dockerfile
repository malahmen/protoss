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
COPY nexus/ /carrier/nexus
COPY .env /carrier/.env

RUN pip install --no-cache-dir -r /carrier/nexus/requirements.txt

# Launch a probe unit
CMD ["python", "./nexus/probe.py"]

# for debuging 
#CMD ["sh", "-c", "python ./nexus/probe.py || sleep infinity"]
