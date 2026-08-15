FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /code

RUN addgroup --system app \
    && adduser --system --ingroup app app \
    && chown app:app /code

COPY requirements.txt .
RUN python -m pip install -r requirements.txt

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=2)"]

FROM base AS development

COPY requirements-dev.txt pyproject.toml ./
RUN python -m pip install -r requirements-dev.txt

COPY --chown=app:app app ./app
COPY --chown=app:app test ./test

USER app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base AS production

COPY --chown=app:app app ./app

USER app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
