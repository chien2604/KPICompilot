FROM python:3.10-slim-bookworm AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/venv

RUN apt-get update \
    && apt-get install --yes --no-install-recommends build-essential gcc g++ libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip setuptools wheel \
    && pip install \
        --index-url https://download.pytorch.org/whl/cpu \
        torch==2.5.1+cpu \
        torchvision==0.20.1+cpu \
    && pip install --requirement /tmp/requirements.txt


FROM python:3.10-slim-bookworm AS runtime

ENV DEBIAN_FRONTEND=noninteractive \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        gosu \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        libmagic1 \
        libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 kpi \
    && useradd --uid 10001 --gid kpi --create-home --shell /usr/sbin/nologin kpi

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

COPY --chown=kpi:kpi backend/ /app/
COPY --chown=kpi:kpi ["Danh sách CB, CC , VC đến ngày 01.8.2026.xlsx", "/app/import-data/personnel.xlsx"]
COPY --chown=kpi:kpi ["DM công việc gửi kèm QĐ 15.6.xlsx", "/app/import-data/work-catalog.xlsx"]
COPY --chmod=755 backend/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

RUN mkdir -p /app/storage/uploads /app/storage/kuzu_db /app/storage/imports \
    && chown -R kpi:kpi /app/storage /app/import-data

EXPOSE 8017

HEALTHCHECK --interval=15s --timeout=5s --start-period=45s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8017/health', timeout=3)" || exit 1

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8017", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips=*"]
