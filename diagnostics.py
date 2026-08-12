from __future__ import annotations
import importlib.util
import os
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for raw in (ROOT / '.env').read_text(encoding='utf-8').splitlines() if (ROOT / '.env').exists() else []:
    line = raw.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"\''))

print('Clyp Design Studio V5.1 diagnostics')
print('Python:', 'OK')
print('Flask:', 'OK' if importlib.util.find_spec('flask') else 'MISSING')
print('google-genai:', 'OK' if importlib.util.find_spec('google.genai') else 'MISSING')
print('Gemini key:', 'configured' if os.getenv('CLYP_GEMINI_API_KEY') else 'MISSING')
print('Design model:', os.getenv('CLYP_GEMINI_MODEL', 'gemini-2.5-flash'))
print('Image model:', os.getenv('CLYP_GEMINI_IMAGE_MODEL', 'gemini-3.1-flash-image'))
print('Minimum design layers:', os.getenv('CLYP_MIN_DESIGN_LAYERS', '12'))
print('Auto polish sparse:', os.getenv('CLYP_AUTO_POLISH_SPARSE', '1'))
print('Online assets: Openverse')
print('Storage: browser localStorage')
print('Accounts: disabled')
print('MySQL/XAMPP: not required')

editor = (ROOT / 'js' / 'editor.js').read_text(encoding='utf-8') if (ROOT / 'js' / 'editor.js').exists() else ''
html = (ROOT / 'editor.html').read_text(encoding='utf-8') if (ROOT / 'editor.html').exists() else ''
match = re.search(r"const requiredIds = \[(.*?)\];", editor, re.S)
required = re.findall(r"'([^']+)'", match.group(1)) if match else []
missing = [x for x in required if f'id="{x}"' not in html and f"id='{x}'" not in html]
print('Editor DOM contract:', 'OK' if required and not missing else f'MISMATCH {missing}')

for name, url in [
    ('Web', os.getenv('CLYP_APP_URL', 'http://127.0.0.1:8080') + '/api/health'),
    ('AI', os.getenv('CLYP_AI_ENDPOINT', 'http://127.0.0.1:8100') + '/health'),
]:
    try:
        with urllib.request.urlopen(url, timeout=1.5) as response:
            print(f'{name}: running ({response.status})')
    except Exception:
        print(f'{name}: not running')
