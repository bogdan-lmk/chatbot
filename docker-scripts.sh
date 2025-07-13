#!/bin/bash
# docker-scripts.sh - Вспомогательные команды для Docker

# Функция для вывода помощи
show_help() {
    echo "AI Agent Docker Management Scripts"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  build       - Собрать Docker образ"
    echo "  dev         - Запустить в режиме разработки"
    echo "  prod        - Запустить в продакшн режиме"
    echo "  stop        - Остановить все сервисы"
    echo "  logs        - Показать логи"
    echo "  shell       - Войти в контейнер"
    echo "  clean       - Очистить данные"
    echo "  backup      - Создать бэкап данных"
    echo "  restore     - Восстановить из бэкапа"
    echo "  health      - Проверить здоровье сервисов"
    echo "  update      - Обновить и перезапустить"
    echo ""
}

# Проверка наличия .env файла
check_env() {
    if [[ ! -f ".env" ]]; then
        echo "⚠️  Файл .env не найден!"
        echo "📝 Создайте файл .env на основе .env.example:"
        echo "   cp .env.example .env"
        echo "   # Отредактируйте .env файл с вашими настройками"
        exit 1
    fi
    
    # Проверяем обязательные переменные
    source .env
    if [[ -z "$OPENAI_API_KEY" ]]; then
        echo "❌ OPENAI_API_KEY не задан в .env файле"
        exit 1
    fi
    
    if [[ -z "$VECTOR_STORE_ID" ]]; then
        echo "⚠️  VECTOR_STORE_ID не задан в .env файле"
        echo "   Некоторые функции могут не работать"
    fi
}

# Сборка образа
build() {
    echo "🔨 Сборка Docker образа..."
    docker-compose build --no-cache
    echo "✅ Образ собран"
}

# Запуск в режиме разработки
dev() {
    check_env
    echo "🚀 Запуск в режиме разработки..."
    docker-compose up --build
}

# Запуск в продакшн режиме
prod() {
    check_env
    echo "🚀 Запуск в продакшн режиме..."
    docker-compose up -d --build
    echo "✅ Сервисы запущены в фоновом режиме"
    echo "🌐 Приложение доступно по адресу: http://localhost:8000"
}

# Остановка сервисов
stop() {
    echo "🛑 Остановка сервисов..."
    docker-compose down
    echo "✅ Сервисы остановлены"
}

# Просмотр логов
logs() {
    echo "📋 Логи сервисов:"
    if [[ -n "$2" ]]; then
        docker-compose logs -f "$2"
    else
        docker-compose logs -f
    fi
}

# Вход в контейнер
shell() {
    echo "🐚 Вход в контейнер ai-agent..."
    docker-compose exec ai-agent /bin/bash
}

# Очистка данных
clean() {
    echo "🧹 Очистка данных..."
    read -p "⚠️  Удалить все данные приложения? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose down -v
        docker system prune -f
        sudo rm -rf data/faiss_index/*
        sudo rm -rf data/uploads/*
        sudo rm -rf logs/*
        echo "✅ Данные очищены"
    else
        echo "❌ Очистка отменена"
    fi
}

# Создание бэкапа
backup() {
    echo "💾 Создание бэкапа..."
    BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
    BACKUP_DIR="backups/backup_$BACKUP_DATE"
    
    mkdir -p "$BACKUP_DIR"
    
    # Бэкап данных
    if [[ -d "data" ]]; then
        cp -r data "$BACKUP_DIR/"
        echo "✅ Данные сохранены в $BACKUP_DIR/data"
    fi
    
    # Бэкап конфигурации
    cp .env "$BACKUP_DIR/" 2>/dev/null || echo "⚠️  .env файл не найден"
    cp docker-compose.yml "$BACKUP_DIR/"
    
    # Создаем архив
    tar -czf "$BACKUP_DIR.tar.gz" -C backups "backup_$BACKUP_DATE"
    rm -rf "$BACKUP_DIR"
    
    echo "✅ Бэкап создан: $BACKUP_DIR.tar.gz"
}

# Восстановление из бэкапа
restore() {
    echo "🔄 Восстановление из бэкапа..."
    
    if [[ -z "$2" ]]; then
        echo "❌ Укажите файл бэкапа:"
        echo "   $0 restore backup_YYYYMMDD_HHMMSS.tar.gz"
        exit 1
    fi
    
    if [[ ! -f "$2" ]]; then
        echo "❌ Файл бэкапа не найден: $2"
        exit 1
    fi
    
    read -p "⚠️  Восстановить данные из $2? Текущие данные будут перезаписаны! (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Останавливаем сервисы
        docker-compose down
        
        # Распаковываем бэкап
        tar -xzf "$2" -C .
        BACKUP_NAME=$(basename "$2" .tar.gz)
        
        # Восстанавливаем данные
        if [[ -d "$BACKUP_NAME/data" ]]; then
            rm -rf data
            mv "$BACKUP_NAME/data" .
            echo "✅ Данные восстановлены"
        fi
        
        # Восстанавливаем конфигурацию
        if [[ -f "$BACKUP_NAME/.env" ]]; then
            cp "$BACKUP_NAME/.env" .
            echo "✅ Конфигурация восстановлена"
        fi
        
        # Очищаем временные файлы
        rm -rf "$BACKUP_NAME"
        
        echo "✅ Восстановление завершено"
        echo "🚀 Запустите сервисы: $0 dev или $0 prod"
    else
        echo "❌ Восстановление отменено"
    fi
}

# Проверка здоровья сервисов
health() {
    echo "🏥 Проверка здоровья сервисов..."
    
    # Проверяем статус контейнеров
    docker-compose ps
    
    echo ""
    echo "📊 Использование ресурсов:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
    
    echo ""
    echo "🌐 Проверка HTTP эндпоинтов:"
    
    # Проверяем основное приложение
    if curl -f -s http://localhost:8000/ > /dev/null; then
        echo "✅ AI Agent: работает (http://localhost:8000)"
    else
        echo "❌ AI Agent: не отвечает"
    fi
    
    # Проверяем Redis
    if docker-compose exec -T redis redis-cli ping | grep -q PONG; then
        echo "✅ Redis: работает"
    else
        echo "❌ Redis: не отвечает"
    fi
}

# Обновление и перезапуск
update() {
    echo "🔄 Обновление приложения..."
    
    # Останавливаем сервисы
    docker-compose down
    
    # Обновляем код (если это Git репозиторий)
    if [[ -d ".git" ]]; then
        echo "📥 Обновление кода из Git..."
        git pull
    fi
    
    # Пересобираем и запускаем
    echo "🔨 Пересборка образов..."
    docker-compose build --no-cache
    
    echo "🚀 Запуск обновленных сервисов..."
    docker-compose up -d
    
    echo "✅ Обновление завершено"
}

# Основная логика
case "${1:-help}" in
    build)
        build
        ;;
    dev)
        dev
        ;;
    prod)
        prod
        ;;
    stop)
        stop
        ;;
    logs)
        logs "$@"
        ;;
    shell)
        shell
        ;;
    clean)
        clean
        ;;
    backup)
        backup
        ;;
    restore)
        restore "$@"
        ;;
    health)
        health
        ;;
    update)
        update
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "❌ Неизвестная команда: $1"
        echo ""
        show_help
        exit 1
        ;;
esac