import json
import requests
from google.cloud import pubsub_v1


project_id = "sublime-wavelet-485112-m9"
topic_id = "openaq-data-topic"

credentials_path = "terraform/keys.json"

publisher = pubsub_v1.PublisherClient.from_service_account_json(credentials_path)
topic_path = publisher.topic_path(project_id, topic_id)

def fetch_and_publish():
    url = "https://api.openaq.org/v2/measurements?limit=10&country=UA"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()['results']
        
        for record in data:
            message_data = json.dumps(record).encode("utf-8")
            
            future = publisher.publish(topic_path, message_data)
            print(f"Опубликовано сообщение: {future.result()}")
    else:
        print(f"Ошибка API: {response.status_code}")

if __name__ == "__main__":
    fetch_and_publish()