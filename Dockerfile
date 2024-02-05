# Use an official Python runtime as a base image
FROM python:3.8

# Install ODBC driver dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        unixodbc \
        unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the local code to the container image
COPY . /app
WORKDIR /app

# Install Python dependencies
RUN pip install -r requirements.txt
