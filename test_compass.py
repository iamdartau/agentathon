import os
import requests
import urllib3
from dotenv import load_dotenv

load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_KEY = os.environ["OPENAI_API_KEY"]
url = os.environ.get("OPENAI_BASE_URL", "https://api.core42.ai/v1") + "/chat/completions"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "model": "gpt-4.1",
    "stream": False,
    "messages": [
        {
            "role": "user",
            "content": "what is national sport of UAE"
        }
    ]
}

response = requests.post(url, headers=headers, json=payload, verify=False, timeout=30)

print(response.status_code)
if response.status_code == 200:
    print(response.json()['choices'][0]['message']['content'])
else:
    print(response.json())