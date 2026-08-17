FROM python:3.12-slim-bookworm
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
COPY frontend ./frontend
ENV PYTHONPATH=/app/src
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=3 CMD python -c "from urllib.request import urlopen; assert urlopen('http://127.0.0.1:8000/healthz', timeout=2).status == 200" || exit 1
CMD ["uvicorn", "interviewer_api.app:app", "--host", "0.0.0.0", "--port", "8000"]
