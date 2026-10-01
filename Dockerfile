ARG PYTHON_IMAGE=python:3.13-alpine
FROM ${PYTHON_IMAGE} AS builder

WORKDIR /build
RUN python -m venv /opt/venv
COPY requirements.txt .
RUN /opt/venv/bin/python -m pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/python -m pip install --no-cache-dir --only-binary=:all: -r requirements.txt \
    && /opt/venv/bin/python -m pip check \
    && /opt/venv/bin/python -m pip uninstall -y setuptools wheel pip

FROM ${PYTHON_IMAGE} AS runtime

RUN apk upgrade --no-cache && apk add --no-cache libpq libstdc++
# Installation tools belong to the build stage, not the running API.
RUN python -m pip uninstall -y setuptools wheel pip \
    && python -c "import shutil, sysconfig; shutil.rmtree(sysconfig.get_path('stdlib') + '/ensurepip')"

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
