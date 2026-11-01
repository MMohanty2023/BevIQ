import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding='utf-8')
from app import app

client = app.test_client()
res = client.post('/api/chat', json={
    'message': 'beer, wine, rtd or spirits missing upc kon kon se hai check karo master brands me se jo hai nahi vo batao or count bhi or csv bhi chaiye mujhe'
})
print('Status Code:', res.status_code)
data = res.get_json()
print('Answer:\n', data['answer'])
print('\nDownload Token:', data['download_token'])
print('Records Count:', data['record_count'])

# Test CSV download
token = data['download_token']
csv_res = client.get(f'/api/export-csv/{token}')
print('\nCSV Export Status Code:', csv_res.status_code)
print('CSV Export Content-Type:', csv_res.content_type)
print('CSV Export Size:', len(csv_res.data), 'bytes')
print('CSV First 3 Lines:\n', '\n'.join(csv_res.data.decode('utf-8').splitlines()[:4]))

