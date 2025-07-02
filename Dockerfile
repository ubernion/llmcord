FROM python:3.13-slim

ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["sh", "-c", "echo 'BOT_TOKEN starts with:' && echo $BOT_TOKEN | head -c 10 && echo '...' && python llmcord.py"]
