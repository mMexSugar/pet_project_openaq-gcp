import functions_framework
import json
import requests
import os
from google.cloud import pubsub_v1

PROJECT_ID = "sublime-wavelet-485112-m9"
TOPIC_ID = "openaq-data-topic"
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)

@functions_framework.http
def fetch_incremental_data(request):
    """
    HTTP Cloud Function. 
    Принимает запрос от Cloud Scheduler и собирает дельту данных.
    """
    api_key = os.environ.get("OPENAQ_API_KEY")
    params = [2, 1, 11, 6, 7, 8, 3]
    headers = {"X-API-Key": api_key}
    total_sent = 0

    for p_id in params:
        url = f"https://api.openaq.org/v3/parameters/{p_id}/latest?limit=20"
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                continue

            results = response.json().get('results', [])
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
                    total_sent += 1
        except Exception as e:
            print(f"Error fetching param {p_id}: {e}")

    return f"Successfully sent {total_sent} measurements to Pub/Sub.", 200