import os
import requests
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()
PROJECT_ID = "sublime-wavelet-485112-m9"
DATASET_ID = "openaq_analysis"
TABLE_ID = "locations_dim"
CREDENTIALS_PATH = os.path.join("terraform", "keys.json")
OPENAQ_API_KEY = os.getenv("OPENAQ_API_KEY")

# Указываем путь к ключам для клиента BigQuery
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDENTIALS_PATH

def sync_locations():
    client = bigquery.Client(project=PROJECT_ID)
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
    
    url = "https://api.openaq.org/v3/locations?limit=500"
    headers = {"X-API-Key": OPENAQ_API_KEY}
    
    try:
        print("Запрос списка локаций из OpenAQ v3...")
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        results = response.json().get('results', [])
        
        rows_to_insert = []
        for loc in results:
            rows_to_insert.append({
                "location_id": loc.get('id'),
                "country_code": loc.get('country', {}).get('code'),
                "latitude": loc.get('coordinates', {}).get('latitude'),
                "longitude": loc.get('coordinates', {}).get('longitude'),
                "last_seen": loc.get('datetimeLast', {}).get('utc') if loc.get('datetimeLast') else None
            })
        
        job_config = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
        
        job = client.load_table_from_json(rows_to_insert, table_ref, job_config=job_config)
        job.result() 
        
        print(f"Синхронизация завершена. Обновлено {len(rows_to_insert)} локаций.")

    except Exception as e:
        print(f"Ошибка при синхронизации: {e}")

if __name__ == "__main__":
    sync_locations()