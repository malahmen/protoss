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
COPY twilight_council/ /carrier/twilight_council
COPY .env /carrier/.env

RUN pip install --no-cache-dir -r /carrier/twilight_council/requirements.txt

CMD ["python", "./twilight_council/stalker.py"]

# for debuging 
#CMD ["sh", "-c", "python ./twilight-council/stalker.py || sleep infinity"]