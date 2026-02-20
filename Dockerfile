FROM python:3.10-slim AS base

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY data/ /app/data/
COPY pytest.ini .
COPY .coveragerc .

# Copy .env if exists (optional - can use env vars from docker-compose)
COPY .env* ./
RUN if [ -f .env.example ] && [ ! -f .env ]; then cp .env.example .env; fi

RUN mkdir -p /app/data

EXPOSE 8000

# ===== STAGE 1: Production =====
FROM base AS production

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ===== STAGE 2: Test (with Playwright) =====
FROM base AS test

RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libdbus-1-3 libxcb1 libxkbcommon0 \
    libx11-6 libxcomposite1 libxdamage1 libxext6 libxfixes3 \
    libxrandr2 libgbm1 libasound2 libpango-1.0-0 libcairo2 \
    fonts-liberation && rm -rf /var/lib/apt/lists/*

COPY tests/ tests/
RUN playwright install chromium

CMD ["pytest", "tests/", "--tb=short"]
