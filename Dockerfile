# Imagem da API Super Benfica (HTTP + WebSocket via Daphne).
# Tag de versão específica (nunca "latest") para builds reprodutíveis.
FROM python:3.13.7-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Usuário sem privilégios para executar a aplicação.
RUN groupadd --system app && useradd --system --gid app --home /app app

COPY requirements.txt .
RUN pip install -r requirements.txt

# Copia somente o código necessário (.env, .git e testes ficam de fora via .dockerignore).
COPY --chown=app:app manage.py ./
COPY --chown=app:app config ./config
COPY --chown=app:app apps ./apps

# Pasta das fotos enviadas: precisa existir com o dono certo para o volume herdar a permissão.
RUN mkdir -p /app/media && chown app:app /app/media

USER app

EXPOSE 8000

CMD ["daphne", "--bind", "0.0.0.0", "--port", "8000", "--proxy-headers", "config.asgi:application"]
