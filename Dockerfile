# UBC UAS Dockerfile - ACOM

FROM ubcuas/pyuuas:latest

# Create the working directory
RUN mkdir -p /uas/acom
WORKDIR /uas/acom

# Expose port 5000
EXPOSE 5000

# Install dependencies
COPY src/requirements.txt src/
RUN pip install -r src/requirements.txt

# Copy in the entire context
COPY instance ./instance/
COPY tests ./tests/
COPY conftest.py ./
COPY src/ ./src/

# Flask environment variables
ENV FLASK_APP src
ENV FLASK_RUN_HOST 0.0.0.0
ENV FLASK_ENV development

STOPSIGNAL SIGINT
CMD ["flask", "run"]
