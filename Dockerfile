FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY frontend ./frontend
RUN pip install --no-cache-dir .

RUN useradd --create-home --uid 10001 labboard \
    && mkdir -p /app/data /app/uploads \
    && chown -R labboard:labboard /app
USER labboard

EXPOSE 8000
CMD ["uvicorn", "labboard.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
