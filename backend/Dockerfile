# Backend image — local development (Python 3.12 to match the project floor).
# A production multi-stage build is introduced later (ops hardening); this image
# is dev-oriented (editable install + autoreload).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Copy the full backend so the editable (hatchling) install can resolve the
# `app` package, then install runtime + dev dependencies.
COPY . .
RUN python -m pip install --upgrade pip && pip install -e ".[dev]"

EXPOSE 8000

# The FastAPI `app` object is implemented in Slice 3; this command serves it
# from then on.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
