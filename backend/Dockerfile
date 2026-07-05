FROM python:3.11-slim

LABEL maintainer="SHELF/MATCH Project"
LABEL description="Book Recommendation API — FastAPI + SQLite"

WORKDIR /app/backend

# Install Python dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

ENV PYTHONUNBUFFERED=1

# Data paths — overridden by docker-compose volumes
ENV DB_PATH=/app/storage/goodbooks.db
ENV BOOKS_CSV=/app/rawdb/goodbooks10/books.csv
ENV TAGS_CSV=/app/rawdb/goodbooks10/tags.csv
ENV BOOK_TAGS_CSV=/app/rawdb/goodbooks10/book_tags.csv

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
