import requests, json
from urllib.parse import unquote

s = requests.Session()
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
})

with open("cookies.json") as f:
    c = json.load(f)

for k, v in c.items():
    s.cookies.set(k, unquote(v), domain="www.ivasms.com")

r = s.get("https://www.ivasms.com/portal/sms/received")
print("Status:", r.status_code)
print("URL:", r.url)
print("HTML:", r.text[:500])
