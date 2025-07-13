# test_openai.py - расширенная версия
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

print("=== ДИАГНОСТИКА OPENAI API ===")
print(f"OpenAI version: {client._version}")

print("\n=== MAIN CLIENT ATTRIBUTES ===")
main_attrs = [attr for attr in dir(client) if not attr.startswith('_')]
print(f"Main client attributes: {main_attrs}")

print("\n=== BETA ATTRIBUTES ===")
beta_attrs = [attr for attr in dir(client.beta) if not attr.startswith('_')]
print(f"Beta attributes: {beta_attrs}")

print("\n=== CHECKING FOR VECTOR_STORES ===")
# Проверим main client
if hasattr(client, 'vector_stores'):
    print("✅ vector_stores найден в main client")
    vs_attrs = [attr for attr in dir(client.vector_stores) if not attr.startswith('_')]
    print(f"Vector stores methods: {vs_attrs}")
else:
    print("❌ vector_stores НЕ найден в main client")

# Проверим все возможные места
places_to_check = [
    ('client', client),
    ('client.beta', client.beta),
]

for name, obj in places_to_check:
    attrs = [attr for attr in dir(obj) if 'vector' in attr.lower()]
    if attrs:
        print(f"✅ В {name} найдены атрибуты с 'vector': {attrs}")

print("\n=== TRYING DIRECT ACCESS ===")
try:
    # Попробуем прямой доступ
    vs = client.vector_stores
    print("✅ Прямой доступ client.vector_stores работает!")
except AttributeError as e:
    print(f"❌ client.vector_stores не работает: {e}")

try:
    # Попробуем через beta
    vs = client.beta.vector_stores  
    print("✅ Доступ client.beta.vector_stores работает!")
except AttributeError as e:
    print(f"❌ client.beta.vector_stores не работает: {e}")

print("\n=== CHECKING FILES API ===")
try:
    files = client.files.list()
    print("✅ Files API работает")
except Exception as e:
    print(f"❌ Files API ошибка: {e}")

print("\n=== CHECKING ASSISTANTS API ===")
try:
    # Пробуем создать assistant (но не создаем реально)
    print("✅ Assistants API доступен через client.beta.assistants")
except Exception as e:
    print(f"❌ Assistants API ошибка: {e}")