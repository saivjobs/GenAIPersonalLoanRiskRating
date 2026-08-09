import base64
import requests
from pathlib import Path

root = Path(__file__).resolve().parents[1]
arch = root / 'ARCHITECTURE.mmd'
out = root / 'ARCHITECTURE.png'

if not arch.exists():
    raise SystemExit('ARCHITECTURE.mmd not found')

text = arch.read_text(encoding='utf-8')
# URL-safe base64 without padding
b64 = base64.urlsafe_b64encode(text.encode('utf-8')).decode('ascii').rstrip('=')
url = f'https://mermaid.ink/img/{b64}'
print('Fetching', url)
resp = requests.get(url)
if resp.status_code != 200:
    raise SystemExit(f'Failed to render mermaid: {resp.status_code}')

out.write_bytes(resp.content)
print('Wrote', out)
