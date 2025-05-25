FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y  \
    build-essential \
    libssl-dev \
    libffi-dev \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt

RUN python -m venv venv &&  \
venv/bin/pip install --upgrade pip &&  \
venv/bin/pip install -r requirements.txt

COPY . .
# ✅ Добавь эту строку:
RUN chmod +x /app/start.sh

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["/app/start.sh"]
