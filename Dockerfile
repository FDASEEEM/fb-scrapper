FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema para Playwright/Chromium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    libgconf-2-4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libgdk-pixbuf2.0-0 \
    libgtk-3-0 \
    libgbm1 \
    libnss3 \
    libxss1 \
    libasound2 \
    fonts-liberation \
    libappindicator3-1 \
    xdg-utils \
    chromium \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar browsers de Playwright
RUN playwright install chromium

COPY .env .
COPY build_state.py .
COPY src/ ./src/

CMD sh -c "python build_state.py && python -m src.main"
