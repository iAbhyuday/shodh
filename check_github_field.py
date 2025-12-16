import requests
import json

url = "https://huggingface.co/api/daily_papers"
try:
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    if data:
        print("First paper structure:")
        paper = data[0]['paper']
        print("Available keys:", paper.keys())
        print("\nGitHub-related fields:")
        print("- githubRepo:", paper.get('githubRepo'))
        print("- projectPage:", paper.get('projectPage'))
        print("\nFull first paper sample:")
        print(json.dumps(data[0], indent=2)[:1000])
except Exception as e:
    print(f"Error: {e}")
