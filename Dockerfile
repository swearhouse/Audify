FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AUDIFY_DATA_DIR=/var/lib/bragi

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN python -m pip install --no-cache-dir . \
    && useradd --system --no-create-home --shell /usr/sbin/nologin bragi \
    && mkdir -p /var/lib/bragi \
    && chown bragi:bragi /var/lib/bragi

USER bragi

EXPOSE 8000

CMD ["python", "-m", "audify"]
