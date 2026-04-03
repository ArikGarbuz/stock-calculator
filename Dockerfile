# Dockerfile — TradeIQ Streamlit App
FROM python:3.11-slim

WORKDIR /app

# Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir flask apscheduler gunicorn

# App files
COPY . .

# Download NLTK data (for sentiment_scorer)
RUN python -c "import nltk; nltk.download('vader_lexicon', quiet=True)"

EXPOSE 8501 5000

# Default: Streamlit dashboard
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
