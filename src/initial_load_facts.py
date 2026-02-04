import os
import json
import requests
import time
from datetime import datetime
from google.cloud import pubsub_v1
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = "sublime-wavelet-485112-m9"
TOPIC_ID = "openaq-data-topic"
CREDENTIALS_PATH = os.path.join("terraform", "keys.json")
OPENAQ_API_KEY = os.getenv("OPENAQ_API_KEY")

PARAMETERS = {
    2: "PM2.5",
    1: "PM10",
    11: "NO2",
    6: "O3"
}

publisher = pubsub_v1.PublisherClient.from_service_account_json(CREDENTIALS_PATH)
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)

def initial_load():
    headers = {"X-API-Key": OPENAQ_API_KEY}
    overall_count = 0

    print(f"[{datetime.now()}] Начало глобальной загрузки фактов...")

    for p_id, p_name in PARAMETERS.items():
        page = 1
        limit = 1000
        param_total = 0
        
        print(f"\n--- Сбор данных для параметра: {p_name} (ID: {p_id}) ---")

        while True:
            url = f"https://api.openaq.org/v3/parameters/{p_id}/latest?limit={limit}&page={page}"
            
            try:
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                results = response.json().get('results', [])

                if not results:
                    break

                for record in results:
                    payload = {
                        "location_id": record.get('locationsId'),
                        "parameter_id": p_id,
                        "value": float(record.get('value')),
                        "timestamp": record.get('datetime', {}).get('utc')
                    }

                    if all(payload.values()):
                        message_bytes = json.dumps(payload).encode("utf-8")

                        publisher.publish(topic_path, message_bytes)
                        param_total += 1
                
                print(f"Страница {page}: обработано {len(results)} записей...")
                page += 1
                
                time.sleep(0.5)

            except Exception as e:
                print(f"Ошибка на странице {page} для параметра {p_id}: {e}")
                break
        
        print(f"Итого для {p_name}: {param_total} фактов отправлено.")
        overall_count += param_total

    print(f"\n{'='*40}")
    print(f"Глобальная загрузка завершена!")
    print(f"Всего отправлено в Pub/Sub: {overall_count} сообщений.")
    print(f"{'='*40}")

if __name__ == "__main__":
    initial_load()