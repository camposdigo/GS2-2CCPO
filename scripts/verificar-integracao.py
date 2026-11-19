"""Smoke test somente leitura e inferência: portal -> dados reais e CNN treinada."""
import json
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def get_json(url):
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)


def main():
    base = 'http://localhost:3000'
    health = get_json(base + '/api/health')
    dashboard = get_json(base + '/api/dashboard')
    water = dashboard['water']
    assert water['dataMode'] == 'real', 'Dados hídricos reais indisponíveis.'
    assert water['observedAt'] and isinstance(water['metrics']['volumePct'], (float, int))
    model_health = get_json('http://127.0.0.1:8001/health')
    assert model_health['modelReady'], 'CNN sem pesos válidos.'
    cnn = ROOT / 'modules/cnn'
    split = json.loads((cnn / 'artifacts/split.json').read_text(encoding='utf-8'))
    relative = split['test'][0]
    sample = cnn / 'data/2750' / relative
    boundary = 'TerritorioVivo' + uuid.uuid4().hex
    header = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="sample.jpg"\r\n'
              'Content-Type: image/jpeg\r\n\r\n').encode('ascii')
    body = header + sample.read_bytes() + f'\r\n--{boundary}--\r\n'.encode('ascii')
    request = urllib.request.Request(base + '/api/classify', data=body,
        headers={'Content-Type': 'multipart/form-data; boundary=' + boundary}, method='POST')
    with urllib.request.urlopen(request, timeout=30) as response:
        classification = json.load(response)
    assert classification['dataMode'] == 'trained_model'
    assert classification['requiresHumanReview'] is True
    assert len(classification['probabilities']) == 10
    assert abs(sum(item['score'] for item in classification['probabilities']) - 1) < 0.0001
    result = {'verifiedAt': datetime.now(timezone.utc).isoformat(), 'portalStatus': health,
              'water': {'dataMode': water['dataMode'], 'observedAt': water['observedAt'],
                        'volumePct': water['metrics']['volumePct'], 'source': water['source']['name']},
              'cnn': {'health': model_health, 'testSample': relative,
                      'actualClass': relative.split('/')[0], 'result': classification},
              'checksPassed': True,
              'note': 'O portal usa ocorrências de demonstração nesta verificação. MongoDB foi validado separadamente em web/evidence/mongo-smoke.json.'}
    evidence = ROOT / 'docs/evidence/integracao.json'
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'checksPassed': True, 'waterVolumePct': water['metrics']['volumePct'],
                      'classification': classification['prediction'], 'evidence': str(evidence)}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
