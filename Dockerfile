# Stage 1: Build dependencies
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
# Use --user to install to /root/.local
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH


ENV PYTHONUNBUFFERED=1

# Copy application code
COPY main.py .
COPY dv360_audience_manager.html .

# Cloud Run injects PORT at runtime
ENV PORT=8080
EXPOSE 8080

CMD uvicorn main:app --host 0.0.0.0 --port $PORT
