#!/usr/bin/env python3
# test_openai.py
"""
Комплексный тестовый скрипт для проверки работоспособности OpenAI API
"""

import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv
import traceback

def print_section(title):
    """Красивый вывод секции"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_status(message, status="info"):
    """Вывод с статусом"""
    icons = {
        "success": "✅",
        "error": "❌",
        "warning": "⚠️",
        "info": "ℹ️",
        "loading": "🔄"
    }
    print(f"{icons.get(status, 'ℹ️')} {message}")

def test_environment():
    """Проверка окружения и переменных"""
    print_section("ПРОВЕРКА ОКРУЖЕНИЯ")
    
    # Загружаем .env
    load_dotenv()
    
    # Проверяем наличие .env файла
    env_file = ".env"
    if os.path.exists(env_file):
        print_status(f"Файл {env_file} найден", "success")
    else:
        print_status(f"Файл {env_file} не найден", "warning")
        print("  Создайте файл .env с содержимым:")
        print("  OPENAI_API_KEY=ваш_ключ_здесь")
    
    # Проверяем API ключ
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        print_status("API ключ найден в переменных окружения", "success")
        print(f"  Тип ключа: {api_key.split('-')[1] if '-' in api_key else 'unknown'}")
        print(f"  Длина: {len(api_key)} символов")
        print(f"  Начинается с: {api_key[:15]}...")
        print(f"  Заканчивается на: ...{api_key[-10:]}")
        
        # Проверяем формат ключа
        if api_key.startswith('sk-'):
            if api_key.startswith('sk-proj-'):
                print_status("Формат ключа: новый проектный ключ", "success")
            else:
                print_status("Формат ключа: стандартный ключ", "success")
        else:
            print_status("Неправильный формат ключа (должен начинаться с 'sk-')", "error")
            return None
            
        return api_key
    else:
        print_status("API ключ не найден", "error")
        print("  Убедитесь, что:")
        print("  1. Файл .env существует")
        print("  2. В нем есть строка OPENAI_API_KEY=ваш_ключ")
        print("  3. Ключ не содержит лишних пробелов")
        return None

def test_openai_import():
    """Проверка импорта OpenAI"""
    print_section("ПРОВЕРКА БИБЛИОТЕК")
    
    try:
        import openai
        print_status(f"openai импортирован успешно (версия: {openai.__version__})", "success")
        return True
    except ImportError as e:
        print_status(f"Ошибка импорта openai: {e}", "error")
        print("  Установите библиотеку: pip install openai>=1.0.0")
        return False
    except Exception as e:
        print_status(f"Неожиданная ошибка при импорте: {e}", "error")
        return False

def test_basic_api_call(api_key):
    """Базовый тест API"""
    print_section("БАЗОВЫЙ ТЕСТ API")
    
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=api_key)
        print_status("OpenAI клиент создан", "success")
        
        print_status("Отправляем тестовый запрос...", "loading")
        start_time = time.time()
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "Привет! Скажи одно слово на русском языке."}
            ],
            max_tokens=10,
            temperature=0.5
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        print_status("API запрос выполнен успешно!", "success")
        print(f"  Время ответа: {response_time:.2f} секунд")
        print(f"  Модель: {response.model}")
        print(f"  Использовано токенов: {response.usage.total_tokens}")
        print(f"  Ответ: '{response.choices[0].message.content.strip()}'")
        
        return True
        
    except Exception as e:
        print_status(f"Ошибка API запроса: {e}", "error")
        print(f"  Тип ошибки: {type(e).__name__}")
        if hasattr(e, 'status_code'):
            print(f"  HTTP код: {e.status_code}")
        return False

def test_models_availability(api_key):
    """Проверка доступных моделей"""
    print_section("ПРОВЕРКА ДОСТУПНЫХ МОДЕЛЕЙ")
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        print_status("Получаем список доступных моделей...", "loading")
        models = client.models.list()
        
        gpt_models = [m for m in models.data if 'gpt' in m.id.lower()]
        embedding_models = [m for m in models.data if 'embedding' in m.id.lower()]
        
        print_status(f"Найдено {len(models.data)} моделей всего", "success")
        print(f"  GPT моделей: {len(gpt_models)}")
        print(f"  Embedding моделей: {len(embedding_models)}")
        
        print("\n  Доступные GPT модели:")
        for model in sorted(gpt_models, key=lambda x: x.id)[:10]:  # Показываем первые 10
            print(f"    - {model.id}")
        
        return True
        
    except Exception as e:
        print_status(f"Ошибка получения моделей: {e}", "error")
        return False

def test_embeddings(api_key):
    """Тест embedding API"""
    print_section("ТЕСТ EMBEDDINGS")
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        print_status("Тестируем embedding API...", "loading")
        start_time = time.time()
        
        response = client.embeddings.create(
            model="text-embedding-ada-002",
            input="Тестовый текст для создания эмбеддинга"
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        embedding = response.data[0].embedding
        
        print_status("Embeddings API работает!", "success")
        print(f"  Время ответа: {response_time:.2f} секунд")
        print(f"  Размер вектора: {len(embedding)}")
        print(f"  Использовано токенов: {response.usage.total_tokens}")
        print(f"  Первые 5 значений: {embedding[:5]}")
        
        return True
        
    except Exception as e:
        print_status(f"Ошибка Embeddings API: {e}", "error")
        return False

def test_rate_limits(api_key):
    """Тест ограничений скорости"""
    print_section("ТЕСТ ЛИМИТОВ СКОРОСТИ")
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        print_status("Отправляем несколько быстрых запросов...", "loading")
        
        requests_count = 3
        successful_requests = 0
        
        for i in range(requests_count):
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": f"Тест {i+1}"}],
                    max_tokens=5
                )
                successful_requests += 1
                print(f"  Запрос {i+1}: ✅")
                time.sleep(0.5)  # Небольшая пауза
                
            except Exception as e:
                print(f"  Запрос {i+1}: ❌ {e}")
        
        print_status(f"Успешных запросов: {successful_requests}/{requests_count}", 
                    "success" if successful_requests == requests_count else "warning")
        
        return successful_requests > 0
        
    except Exception as e:
        print_status(f"Ошибка теста лимитов: {e}", "error")
        return False

def test_langchain_integration(api_key):
    """Тест интеграции с LangChain"""
    print_section("ТЕСТ ИНТЕГРАЦИИ С LANGCHAIN")
    
    try:
        from langchain_openai import OpenAIEmbeddings, ChatOpenAI
        
        print_status("Тестируем LangChain OpenAI интеграцию...", "loading")
        
        # Тест эмбеддингов
        embeddings = OpenAIEmbeddings(
            openai_api_key=api_key,
            model="text-embedding-ada-002"
        )
        
        test_texts = ["Привет мир", "Hello world"]
        embedding_result = embeddings.embed_documents(test_texts)
        
        print_status("LangChain embeddings работают!", "success")
        print(f"  Обработано текстов: {len(test_texts)}")
        print(f"  Размер каждого вектора: {len(embedding_result[0])}")
        
        # Тест чата
        chat = ChatOpenAI(
            openai_api_key=api_key,
            model="gpt-3.5-turbo",
            temperature=0
        )
        
        from langchain.schema import HumanMessage
        response = chat([HumanMessage(content="Скажи 'тест прошел успешно'")])
        
        print_status("LangChain chat работает!", "success")
        print(f"  Ответ: '{response.content}'")
        
        return True
        
    except ImportError as e:
        print_status(f"LangChain не установлен: {e}", "warning")
        print("  Установите: pip install langchain-openai")
        return False
    except Exception as e:
        print_status(f"Ошибка LangChain интеграции: {e}", "error")
        return False

def generate_report(results):
    """Генерация итогового отчета"""
    print_section("ИТОГОВЫЙ ОТЧЕТ")
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    
    print(f"📊 Тестов пройдено: {passed_tests}/{total_tests}")
    print(f"📈 Успешность: {passed_tests/total_tests*100:.1f}%")
    print(f"⏰ Время тестирования: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("\n📋 Детали:")
    for test_name, result in results.items():
        status = "✅ ПРОШЕЛ" if result else "❌ ПРОВАЛЕН"
        print(f"  {test_name}: {status}")
    
    if passed_tests == total_tests:
        print_status("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! OpenAI API готов к использованию", "success")
    elif passed_tests > 0:
        print_status("⚠️ Частичная работоспособность. Проверьте проваленные тесты", "warning")
    else:
        print_status("❌ API не работает. Проверьте ключ и соединение", "error")
    
    # Рекомендации
    print("\n💡 РЕКОМЕНДАЦИИ:")
    if not results.get("environment"):
        print("  • Проверьте файл .env и формат API ключа")
    if not results.get("basic_api"):
        print("  • Проверьте интернет соединение и валидность ключа")
    if not results.get("models"):
        print("  • Возможно, у вас ограниченный доступ к API")
    if not results.get("langchain"):
        print("  • Установите langchain-openai для полной интеграции")

def main():
    """Основная функция"""
    print("🚀 ТЕСТИРОВАНИЕ OPENAI API")
    print(f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    try:
        # 1. Проверка окружения
        api_key = test_environment()
        results["environment"] = api_key is not None
        
        if not api_key:
            print_status("Дальнейшее тестирование невозможно без API ключа", "error")
            generate_report(results)
            return
        
        # 2. Проверка библиотек
        results["libraries"] = test_openai_import()
        
        if not results["libraries"]:
            print_status("Установите библиотеку OpenAI для продолжения", "error")
            generate_report(results)
            return
        
        # 3. Базовый тест API
        results["basic_api"] = test_basic_api_call(api_key)
        
        # 4. Тест моделей (только если базовый тест прошел)
        if results["basic_api"]:
            results["models"] = test_models_availability(api_key)
            results["embeddings"] = test_embeddings(api_key)
            results["rate_limits"] = test_rate_limits(api_key)
        else:
            results["models"] = False
            results["embeddings"] = False
            results["rate_limits"] = False
        
        # 5. Тест LangChain (опционально)
        results["langchain"] = test_langchain_integration(api_key)
        
    except KeyboardInterrupt:
        print_status("\nТестирование прервано пользователем", "warning")
    except Exception as e:
        print_status(f"Неожиданная ошибка: {e}", "error")
        traceback.print_exc()
    
    finally:
        generate_report(results)

if __name__ == "__main__":
    main()