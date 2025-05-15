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
COPY gateway/ /carrier/gateway
COPY .env /carrier/.env

RUN pip install --no-cache-dir -r /carrier/gateway/requirements.txt

CMD ["python", "./gateway/zealot.py"]

# for debuging 
#CMD ["sh", "-c", "python ./gateway/zealot.py || sleep infinity"]
