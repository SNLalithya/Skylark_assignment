FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY monday_client.py agent.py app.py ./

# Expose Chainlit default port
EXPOSE 8000

# Start command — Railway injects $PORT automatically
CMD ["chainlit", "run", "app.py", "--host", "0.0.0.0", "--port", "8000"]