FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    bash \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.runtime.txt .
RUN pip install --no-cache-dir -r requirements.runtime.txt

COPY dashboard.py .
COPY pages/ pages/
COPY core/ core/
COPY config.py alpaca_client.py run_daily.py ./
COPY *.py ./
COPY start_app.sh ./

RUN mkdir -p logs && \
    chmod +x start_app.sh

# Set timezone to America/New_York for market hours
ENV TZ=America/New_York

CMD ["./start_app.sh"]
