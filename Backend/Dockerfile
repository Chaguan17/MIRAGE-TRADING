FROM python:3.12-slim

WORKDIR /app

# Dependencias de sistema necesarias para compilar algunas libs de ML
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY Backend/ .

# El comando real se define en docker-compose (bot vs api)
CMD ["python", "main.py"]
