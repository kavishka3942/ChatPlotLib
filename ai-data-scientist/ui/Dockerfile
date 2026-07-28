FROM python:3.10-slim
WORKDIR /app

ENV PYTHONPATH=/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["chainlit", "run", "app.py", "--host", "0.0.0.0", "--port", "8080"]