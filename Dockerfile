FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1 \
    FLASK_APP=app.py \
    SOCKETIO_ASYNC_MODE=eventlet \
    PORT=5001

EXPOSE 5001

# Один воркер eventlet — требование Flask-SocketIO
CMD gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:${PORT} --timeout 120 wsgi:application
