FROM python:3.12

ENV PYTHONUNBUFFERED=1

WORKDIR /app/

COPY --from=ghcr.io/astral-sh/uv:0.4.15 /uv /bin/uv

ENV PATH="/app/.venv/bin:$PATH"

ENV UV_COMPILE_BYTECODE=1

ENV UV_LINK_MODE=copy

RUN --mount=type=cache,target=/root/.cache/uv \
   --mount=type=bind,source=uv.lock,target=uv.lock \
   --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
   uv sync --frozen --no-install-project

ENV PYTHONPATH=/app

RUN mkdir ./database

COPY ./pyproject.toml ./uv.lock ./alembic.ini /app/

COPY ./app /app/app

RUN --mount=type=cache,target=/root/.cache/uv \
   uv sync

CMD ["fastapi", "run","--app" ,"app"]
