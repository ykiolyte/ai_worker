FROM python:3.12-slim

WORKDIR /app
COPY backend/pyproject.toml /app/pyproject.toml
RUN pip install --no-cache-dir -e .
COPY backend/app /app/app
COPY docs/ooo.md /app/docs/ooo.md

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
