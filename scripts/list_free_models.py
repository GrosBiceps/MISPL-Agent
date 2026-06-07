import os, urllib.request, json
from dotenv import load_dotenv
load_dotenv(r"C:\Users\Florian Travail\Documents\MISPL Agent\MISPL\.env")

key = os.environ["OPENROUTER_API_KEY"]
req = urllib.request.Request(
    "https://openrouter.ai/api/v1/models",
    headers={"Authorization": f"Bearer {key}", "HTTP-Referer": "https://mispl-agent.lab"}
)
with urllib.request.urlopen(req, timeout=15) as r:
    data = json.loads(r.read())

free = [m for m in data["data"] if float(m.get("pricing", {}).get("prompt", "1") or "1") == 0]
print(f"Modeles gratuits disponibles: {len(free)}")
for m in sorted(free, key=lambda x: x["id"]):
    mid = m["id"]
    ctx = m.get("context_length", "?")
    print(f"  {mid} (ctx={ctx})")
