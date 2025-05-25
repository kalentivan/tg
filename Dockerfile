FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y  \
    build-essential \
    libssl-dev \
    libffi-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt

RUN python -m venv venv && 
venv/bin/pip install --upgrade pip && 
venv/bin/pip install -r requirements.txt

COPY . .

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["/app/start.sh"]
