"""API local de classificação. Não retém uploads nem executa pesos externos."""
import hashlib
import io
import json
import warnings
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, UnidentifiedImageError
import torch
from fastapi import FastAPI, File, HTTPException, UploadFile

from model import LandscapeCNN

ROOT = Path(__file__).resolve().parent
MAX_UPLOAD = 5 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 16_000_000
torch.set_num_threads(2)
app = FastAPI(title='Território Vivo — CNN', version='1.0.0')


@lru_cache(maxsize=1)
def load_model():
    manifest_path, weights_path = ROOT / 'artifacts/manifest.json', ROOT / 'artifacts/landscape.pt'
    if not manifest_path.exists() or not weights_path.exists():
        raise HTTPException(503, 'CNN ainda não treinada. Execute train.py antes da classificação.')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if hashlib.sha256(weights_path.read_bytes()).hexdigest() != manifest['weightsSha256']:
        raise HTTPException(503, 'Integridade do modelo inválida; execute novamente o treinamento.')
    model = LandscapeCNN(manifest['selectedExperiment']['filters'], len(manifest['classes']))
    # Apenas pesos locais produzidos pelo treino, com modo seguro do PyTorch.
    model.load_state_dict(torch.load(weights_path, map_location='cpu', weights_only=True))
    model.eval()
    return model, manifest


@app.get('/health')
def health():
    try:
        load_model()
        ready = True
    except (HTTPException, OSError, KeyError, ValueError, RuntimeError):
        ready = False
    return {'status': 'ok' if ready else 'training_required', 'modelReady': ready}


@app.post('/api/classify')
def classify(file: UploadFile = File(...)):
    # Rota síncrona: FastAPI executa decodificação/inferência no threadpool.
    try:
        contents = file.file.read(MAX_UPLOAD + 1)
    finally:
        file.file.close()
    if not contents or len(contents) > MAX_UPLOAD:
        raise HTTPException(413, 'Envie uma imagem JPEG ou PNG com até 5 MB.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(contents)) as image:
                if image.format not in {'JPEG', 'PNG'}:
                    raise HTTPException(415, 'Somente JPEG e PNG são aceitos.')
                if image.width < 32 or image.height < 32:
                    raise HTTPException(422, 'A imagem deve ter pelo menos 32×32 pixels.')
                values = np.array(image.convert('RGB').resize((64, 64)), dtype=np.float32) / 255
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(422, 'Arquivo inválido ou imagem com dimensões excessivas.') from None
    model, manifest = load_model()
    tensor = torch.from_numpy(values).permute(2, 0, 1).unsqueeze(0)
    with torch.inference_mode():
        scores = torch.softmax(model(tensor), dim=1)[0].tolist()
    probabilities = sorted([
        {'className': name, 'label': manifest['labels'][name], 'score': score}
        for name, score in zip(manifest['classes'], scores)
    ], key=lambda item: item['score'], reverse=True)
    prediction = probabilities[0]
    return {
        'dataMode': 'trained_model',
        'model': {'name': manifest['name'], 'version': manifest['version'],
                  'testAccuracy': manifest['test']['accuracy'], 'testMacroF1': manifest['test']['macroF1']},
        'prediction': prediction, 'probabilities': probabilities,
        'confidence': {'type': 'softmax_uncalibrated', 'value': prediction['score'],
                       'label': 'Pontuação do modelo; não é confiança calibrada de acerto.'},
        'limitations': manifest['limitations'], 'requiresHumanReview': True,
        'disclaimer': 'Análise acadêmica de paisagem; não valida risco hídrico, potabilidade ou ações públicas.',
    }
