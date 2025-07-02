FROM python:3.13-slim

ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["sh", "-c", "cat config.yaml && echo '---END CONFIG---' && python llmcord.py"]
