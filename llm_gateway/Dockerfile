FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 7860 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 CMD curl -f http://localhost:8000/health || exit 1

CMD bash -c "python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000 &> /tmp/api.log & sleep 2 && python app.py --host 0.0.0.0 --port 7860"
