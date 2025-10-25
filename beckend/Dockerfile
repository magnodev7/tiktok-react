FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=America/Sao_Paulo

# Instale apenas o necessário: curl, fontes, timezone, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-liberation \
    ca-certificates \
    procps \
    tzdata \
    curl \
 && ln -fs /usr/share/zoneinfo/America/Sao_Paulo /etc/localtime \
 && dpkg-reconfigure -f noninteractive tzdata \
 && rm -rf /var/lib/apt/lists/*

# Não precisamos de CHROME_BIN nem CHROMEDRIVER — estamos usando REMOTO!
# ENV CHROME_BIN=... → REMOVA ISSO

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copia toda a estrutura do projeto
COPY . /app/

# COPY http_health.py ./
# COPY src/ ./src/
# COPY tiktok_scheduler.py ./
# COPY web/ ./web/

RUN mkdir -p /app/videos/default /app/posted/default /app/user_data/default /app/state /app/users

RUN useradd -m appuser && chown -R appuser:appuser /app
RUN chmod 755 /app/users
RUN chmod 777 /app/users

# Copia e configura script de inicialização
COPY init_container.sh /app/init_container.sh
RUN chmod +x /app/init_container.sh

USER appuser

EXPOSE 8082

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8082/health >/dev/null || exit 1

CMD ["/app/init_container.sh", "python3", "tiktok_scheduler.py"]