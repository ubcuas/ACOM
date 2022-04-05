# UBC UAS Dockerfile - ACOM

FROM python:3.8

# Create the working directory
RUN mkdir -p /uas/acom
WORKDIR /uas/acom

# Expose port 5000
EXPOSE 5000

# Install dependencies
COPY src/requirements.txt src/
RUN pip install -r src/requirements.txt

# Flask environment variables
ENV FLASK_APP src
ENV FLASK_RUN_HOST 0.0.0.0
ENV FLASK_ENV development

# Copy in the entire context
COPY instance ./instance/
COPY pytest.ini ./
COPY conftest.py ./
COPY tests ./tests/
COPY src/ ./src/

STOPSIGNAL SIGINT
CMD ["flask", "run"]
