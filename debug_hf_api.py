import requests
import json

url = "https://huggingface.co/api/daily_papers"
# Try yesterday
import datetime
yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
print(f"Testing date: {yesterday}")
try:
    resp = requests.get(f"{url}?date={yesterday}")
    resp.raise_for_status()
    data = resp.json()
    print(f"Count for {yesterday}: {len(data)}")
    if data:
        print("First paper title:", data[0]['paper']['title'])
except Exception as e:
    print(f"Date fetch failed: {e}")
