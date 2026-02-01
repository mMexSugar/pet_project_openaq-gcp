import json
import requests
import time
from datetime import datetime, timedelta
from google.cloud import pubsub_v1
import os

PROJECT_ID = "sublime-wavelet-485112-m9"
TOPIC_ID = "openaq-data-topic"
CREDENTIALS_PATH = os.path.join("terraform", "keys.json")

publisher = pubsub_v1.PublisherClient.from_service_account_json(CREDENTIALS_PATH)
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)

def transform_data(record):
    """Приводит данные OpenAQ к нашей схеме BigQuery"""
    coordinates = record.get('coordinates', {}) or {}
    return {
        "location_id": record.get('locationId'),
        "location": record.get('location'),
        "city": record.get('city'),
        "country": record.get('country'),
        "parameter": record.get('parameter'),
        "value": record.get('value'),
        "unit": record.get('unit'),
        "timestamp": record.get('date', {}).get('utc'),
        "latitude": coordinates.get('latitude'),
        "longitude": coordinates.get('longitude')
    }

def fetch_and_publish():
    #  записи за последние 2 минуты создает overlap, чтобы не потерять данные из-за задержек API
    time_threshold = (datetime - timedelta(minutes=2)).isoformat()
    
    url = f"https://api.openaq.org/v2/measurements?limit=100&date_from={time_threshold}&order_by=datetime"
    
    try:
        print(f"[{datetime.now()}] Запрос новых данных (после {time_threshold})...")
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        
        results = response.json().get('results', [])
        print(f"Получено {len(results)} новых записей.")

        for record in results:
            clean_data = transform_data(record)
            if clean_data["timestamp"]:
                message_bytes = json.dumps(clean_data).encode("utf-8")
                publisher.publish(topic_path, message_bytes)
        
        print("Данные отправлены в Pub/Sub.")

    except Exception as e:
        print(f"Ошибка при сборе данных: {e}")

if __name__ == "__main__":
    print("Запуск мониторинга качества воздуха (Global)...")
    while True:
        fetch_and_publish()
        print("Ожидание 60 секунд...")
        time.sleep(60)