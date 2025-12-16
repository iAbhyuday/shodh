import requests
import json
import datetime

BASE_URL = "http://localhost:8000/api/feed"

def test_feed():
    print("--- Testing Standard Feed ---")
    try:
        resp = requests.get(f"{BASE_URL}?limit=5")
        resp.raise_for_status()
        data = resp.json()
        print(f"Feed Count: {len(data)}")
        if data:
            print(f"First Paper: {data[0]['title']}")
            return data[0]['title'].split()[0] # Return a keyword
    except Exception as e:
        print(f"Feed failed: {e}")
        return None

def test_keyword(keyword):
    print(f"\n--- Testing Keyword: '{keyword}' ---")
    try:
        resp = requests.get(f"{BASE_URL}?q={keyword}&limit=5")
        resp.raise_for_status()
        data = resp.json()
        print(f"Filtered Count: {len(data)}")
        for p in data:
            print(f" - {p['title']}")
    except Exception as e:
        print(f"Keyword failed: {e}")

def test_date(date_str):
    print(f"\n--- Testing Date: {date_str} ---")
    try:
        resp = requests.get(f"{BASE_URL}?date={date_str}&limit=5")
        resp.raise_for_status()
        data = resp.json()
        print(f"Date Count: {len(data)}")
        if data:
            print(f"First Paper Date: {data[0]['published_date']}")
    except Exception as e:
        print(f"Date failed: {e}")

if __name__ == "__main__":
    keyword = test_feed()
    if keyword:
        test_keyword(keyword)
    
    # Test a known date
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    test_date(yesterday)
