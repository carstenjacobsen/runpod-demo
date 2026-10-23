FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=80

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY main.py github.py summarize.py slack.py request_log.py ./

# RunPod load balancing endpoints send traffic to $PORT and poll GET /ping.
# Secrets are NOT baked into the image: set them as environment variables on the endpoint.
EXPOSE 80
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port 80"]
