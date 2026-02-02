import json
import requests
import time
from datetime import datetime
from google.cloud import pubsub_v1
import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = "sublime-wavelet-485112-m9"
TOPIC_ID = "openaq-data-topic"
CREDENTIALS_PATH = os.path.join("terraform", "keys.json")

OPENAQ_API_KEY = os.getenv("OPENAQ_API_KEY")

publisher = pubsub_v1.PublisherClient.from_service_account_json(CREDENTIALS_PATH)
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)

def transform_v3_data(location):
    messages = []
    sensors = location.get('sensors', [])
    
    for sensor in sensors:
        latest = sensor.get('latest')
        if not latest:
            continue
            
        messages.append({
            "location_id": location.get('id'),
            "location": location.get('name'),
            "city": location.get('locality'),
            "country": location.get('country', {}).get('code'),
            "parameter": sensor.get('parameter', {}).get('name'),
            "value": latest.get('value'),
            "unit": sensor.get('parameter', {}).get('units'),
            "timestamp": latest.get('datetime', {}).get('utc'),
            "latitude": location.get('coordinates', {}).get('latitude'),
            "longitude": location.get('coordinates', {}).get('longitude')
        })
    return messages

def fetch_and_publish():
    url = "https://api.openaq.org/v3/locations?limit=100&monitor=true"
    headers = {"X-API-Key": OPENAQ_API_KEY}
    
    try:
        print(f"[{datetime.now()}] Запрос к OpenAQ v3 API...")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        if response.status_code != 200:
            print(f"Детали ошибки от сервера: {response.text}")
        
        
        locations = response.json().get('results', [])
        print(f"API вернуло {len(locations)} локаций.")
        count = 0

        if len(locations) > 0:
            # Посмотрим на структуру первой локации, если данных 0
            print(f"Пример данных первой локации: {json.dumps(locations[0], indent=2)}")
            pass

        for loc in locations:
            clean_messages = transform_v3_data(loc)
            for msg in clean_messages:
                message_bytes = json.dumps(msg).encode("utf-8")
                publisher.publish(topic_path, message_bytes)
                count += 1
        
        print(f"Успешно отправлено {count} измерений в Pub/Sub.")

    except Exception as e:
        print(f"Ошибка при сборе данных: {e}")

if __name__ == "__main__":
    print("Запуск мониторинга (OpenAQ v3 Global)...")
    while True:
        fetch_and_publish()
        print("Ожидание 60 секунд...")
        time.sleep(60)