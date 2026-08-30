# ============================================================
#  Sen NoneBot2 Dockerfile
#  多阶段构建：builder 装依赖，runtime 只拷贝产物
# ============================================================

# ---- Builder ----
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

# ---- Runtime ----
FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/sen_bot /app/sen_bot
COPY --from=builder /app/bot.py /app/bot.py

RUN mkdir -p /app/data

ENV PATH="/app/.venv/bin:$PATH" \
    TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8003

CMD ["python", "bot.py"]

