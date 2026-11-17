FROM python:3.15-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /bin/uv

WORKDIR /app/

# use the image's python, put the venv outside /app so COPY . can't clobber it
ENV UV_PYTHON_DOWNLOADS=0 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml uv.lock /app/
RUN uv sync --locked --no-dev --no-install-project

COPY . /app/

CMD ["python", "main.py"]
