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

RUN mkdir -p logs

CMD ["streamlit", "run", "dashboard.py", "--server.port=8080", "--server.address=0.0.0.0", "--server.headless=true"]
