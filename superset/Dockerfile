FROM apache/superset:latest

USER root

# Cài psycopg2-binary vào venv của Superset
RUN /app/.venv/bin/python -m ensurepip --upgrade || true && \
    pip install --target=/app/.venv/lib/python3.10/site-packages psycopg2-binary

USER superset
