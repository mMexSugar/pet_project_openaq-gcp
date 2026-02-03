import json
import requests
import time
import os
from datetime import datetime
from google.cloud import pubsub_v1
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = "sublime-wavelet-485112-m9"
TOPIC_ID = "openaq-data-topic"
CREDENTIALS_PATH = os.path.join("terraform", "keys.json")

OPENAQ_API_KEY = os.getenv("OPENAQ_API_KEY")
# Мониторим основные параметры: PM2.5 (2), PM10 (1), NO2 (11), O3 (6)
PARAMETERS_TO_WATCH = [2, 1, 11, 6]

publisher = pubsub_v1.PublisherClient.from_service_account_json(CREDENTIALS_PATH)
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)

# def transform_to_fact_table(location_record):
#     fact_messages = []
#     location_id = location_record.get('id')
#     sensors = location_record.get('sensors', [])

#     for sensor in sensors:
#         latest = sensor.get('latest')
#         parameter = sensor.get('parameter', {})
#         param_id = parameter.get('id')
        
#         # Пропускаем, если нет данных или параметр нам не интересен
#         if not latest or param_id not in PARAMETERS_TO_WATCH:
#             continue
            
#         fact_messages.append({
#             "location_id": int(location_id),
#             "parameter_id": int(param_id),
#             "value": float(latest.get('value')),
#             "timestamp": latest.get('datetime', {}).get('utc')
#         })
        
#     return fact_messages

# def fetch_and_publish():
#     url = "https://api.openaq.org/v3/locations?limit=100&monitor=true"
#     headers = {"X-API-Key": OPENAQ_API_KEY}
    
#     try:
#         print(f"[{datetime.now()}] Запрос к OpenAQ v3 API...")
#         response = requests.get(url, headers=headers, timeout=15)
#         response.raise_for_status()
        
#         results = response.json().get('results', [])
#         total_sent = 0

#         for record in results:
#             fact_messages = transform_to_fact_table(record)
            
#             for msg in fact_messages:
#                 message_bytes = json.dumps(msg).encode("utf-8")
#                 publisher.publish(topic_path, message_bytes)
#                 total_sent += 1
        
#         print(f"Успешно отправлено {total_sent} фактов в Pub/Sub (направляются в measurements_fact).")

#     except Exception as e:
#         print(f"Ошибка при сборе данных: {e}")

# if __name__ == "__main__":
#     print(f"Запуск Producer (Проект: {PROJECT_ID})")
#     while True:
#         fetch_and_publish()
#         print("Ожидание 60 секунд...")
#         time.sleep(60)

def fetch_latest_by_parameters():
    headers = {"X-API-Key": OPENAQ_API_KEY}
    total_count = 0

    for p_id in PARAMETERS_TO_WATCH:
        # Эндпоинт /parameters/{id}/latest — ЕДИНСТВЕННЫЙ способ получить 
        # глобальный список свежих замеров в v3
        url = f"https://api.openaq.org/v3/parameters/{p_id}/latest?limit=50"
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                print(f"Ошибка параметра {p_id}: {response.status_code}")
                continue

            results = response.json().get('results', [])
            
            for record in results:
                # В v3/latest поле называется locationsId
                payload = {
                    "location_id": record.get('locationsId'),
                    "parameter_id": p_id,
                    "value": float(record.get('value')),
                    "timestamp": record.get('datetime', {}).get('utc')
                }

                if all(payload.values()):
                    message_bytes = json.dumps(payload).encode("utf-8")
                    publisher.publish(topic_path, message_bytes)
                    total_count += 1
                    
        except Exception as e:
            print(f"Ошибка запроса для {p_id}: {e}")

    return total_count

if __name__ == "__main__":
    print(f"Запуск глобального мониторинга v3 (Параметры: {PARAMETERS_TO_WATCH})")
    while True:
        sent = fetch_latest_by_parameters()
        print(f"[{datetime.now()}] Отправлено фактов: {sent}")
        print("Ожидание 60 секунд...")
        time.sleep(60)