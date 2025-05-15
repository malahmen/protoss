# Base Python image
ARG PYTHON_VERSION=python:3.11-slim
FROM ${PYTHON_VERSION}

# Set working directory
WORKDIR /carrier

# System dependencies
RUN apt-get update && apt-get install -y libmagic1

# Set PYTHONPATH so imports from /carrier work
ENV PYTHONPATH=/carrier

# Copy the required project files - might be possible to replace /carrier by .
COPY pylon/ /carrier/pylon
COPY cybernetics_core/ /carrier/cybernetics_core
COPY .env /carrier/.env

RUN pip install --no-cache-dir -r /carrier/cybernetics_core/requirements.txt

CMD ["python", "./cybernetics_core/sentry.py"]

# for debuging 
#CMD ["sh", "-c", "python ./cybernetics-core/sentry.py || sleep infinity"]
