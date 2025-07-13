# Dockerfile - обновленная версия для AI Agent
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создаем пользователя для безопасности
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# Устанавливаем переменные окружения для Python
ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Копируем и устанавливаем зависимости
COPY --chown=app:app requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY --chown=app:app src/ ./src/
COPY --chown=app:app scripts/ ./scripts/

# Создаем необходимые директории для данных
RUN mkdir -p /app/data/docs \
    /app/data/faiss_index \
    /app/data/uploads \
    /app/logs

# Делаем скрипты исполняемыми
RUN chmod +x /app/scripts/*.py

# Проверяем структуру проекта
RUN echo "Структура проекта:" && find /app -type f -name "*.py" | head -20

# Настраиваем переменные окружения для приложения
ENV PATH="/home/app/.local/bin:$PATH"

# Открываем порт
EXPOSE 8000

# Проверка здоровья приложения
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Команда по умолчанию
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]