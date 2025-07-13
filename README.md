# AI Agent - CF Anatolik

Умный помощник с поиском по документам на базе OpenAI Assistants API и Vector Stores.

## Возможности

- 💬 Чат с AI-ассистентом CF Anatolik
- 📄 Загрузка и обработка PDF документов
- 🔍 Поиск по загруженным документам
- 🧠 Интеграция с OpenAI Vector Stores
- 📱 Веб-интерфейс для удобного использования

## Быстрый старт

### 1. Настройка окружения

```bash
# Клонируйте репозиторий
git clone <repository-url>
cd ai-agent

# Создайте .env файл
cp .env.example .env
```

### 2. Настройте переменные в .env

```env
OPENAI_API_KEY=sk-proj-your-api-key-here
ASSISTANT_ID=asst_your-assistant-id-here
VECTOR_STORE_ID=vs_your-vector-store-id-here
```

### 3. Запуск с Docker

```bash
# Дайте права на выполнение скрипту
chmod +x docker-scripts.sh

# Запуск в режиме разработки
./docker-scripts.sh dev

# Или в продакшн режиме
./docker-scripts.sh prod
```

### 4. Запуск без Docker

```bash
# Установите зависимости
pip install -r requirements.txt

# Запустите приложение
uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8000
```

## Использование

1. Откройте браузер: `http://localhost:8000`
2. Загрузите PDF файлы через вкладку "Загрузка PDF"
3. Задавайте вопросы в чате по содержимому документов

## Структура проекта

```
├── src/app/                    # Основное приложение
│   ├── api/v1/endpoints/      # API эндпоинты
│   ├── core/                  # Конфигурация и логирование
│   ├── db/                    # База данных
│   ├── services/              # Бизнес-логика
│   └── templates/             # Веб-интерфейс
├── scripts/                   # Вспомогательные скрипты
├── data/                      # Данные приложения
└── docker-scripts.sh          # Управление Docker
```

## API

### Основные эндпоинты

- `GET /` - Веб-интерфейс
- `POST /api/v1/message/` - Отправка сообщения ассистенту
- `GET /api/v1/history/` - История сообщений
- `POST /api/v1/upload/pdf` - Загрузка PDF файла
- `GET /api/v1/upload/pdf/info` - Информация о Vector Store

### Пример запроса

```bash
curl -X POST "http://localhost:8000/api/v1/message/" \
  -H "Content-Type: application/json" \
  -d '{"thread_id": "main", "message": "Что содержится в загруженных документах?"}'
```

## Управление Docker

```bash
# Все доступные команды
./docker-scripts.sh help

# Основные команды
./docker-scripts.sh dev      # Разработка
./docker-scripts.sh prod     # Продакшн
./docker-scripts.sh logs     # Просмотр логов
./docker-scripts.sh health   # Проверка состояния
./docker-scripts.sh backup   # Создание бэкапа
```

## Требования

- Python 3.11+
- Docker и docker-compose (для Docker-запуска)
- OpenAI API ключ
- Настроенный OpenAI Assistant
- Настроенный OpenAI Vector Store

## Настройка OpenAI

1. Создайте Assistant в OpenAI Platform
2. Создайте Vector Store для хранения документов
3. Добавьте соответствующие ID в .env файл

## Тестирование

```bash
# Запуск тестов
pytest

# Тест OpenAI API
python tests/test.py

# Проверка загрузки
python tests/test_upload.py
```

## Разработка

```bash
# Линтер
flake8 src

# Локальный запуск
make run
```

## Лицензия

MIT License