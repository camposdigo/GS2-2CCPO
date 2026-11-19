"""Experimentos reproduzíveis com EuroSAT RGB e CNNs criadas do zero."""
import argparse
import copy
import hashlib
import json
import random
import time
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from model import LandscapeCNN

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
ARTIFACTS = ROOT / 'artifacts'
DATASET_URL = ('https://huggingface.co/datasets/torchgeo/eurosat/resolve/'
               'c877bcd43f099cd0196738f714544e355477f3fd/EuroSAT.zip')
EXPECTED_MD5 = 'c8fa014336c82ac7804f0398fcb19387'
CLASS_LABELS = {
    'AnnualCrop': 'Cultivo anual', 'Forest': 'Floresta',
    'HerbaceousVegetation': 'Vegetação herbácea', 'Highway': 'Rodovia',
    'Industrial': 'Área industrial', 'Pasture': 'Pastagem',
    'PermanentCrop': 'Cultivo permanente', 'Residential': 'Área residencial',
    'River': 'Rio', 'SeaLake': 'Mar ou lago',
}
LIMITATIONS = [
    'EuroSAT contém paisagens europeias; não houve validação geográfica no Brasil.',
    'Separação aleatória estratificada por arquivo; proximidade espacial pode inflar as métricas.',
    'Somente RGB, imagens redimensionadas para 64×64; não mede potabilidade ou disponibilidade hídrica.',
    'Pontuação softmax não é probabilidade calibrada de acerto; fotos comuns e imagens fora do domínio podem enganar a rede.',
    'Resultado acadêmico experimental; não decide intervenções urbanas ou ambientais.',
]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def prepare_dataset():
    DATA.mkdir(exist_ok=True)
    archive = DATA / 'EuroSAT.zip'
    if not archive.exists():
        print('Baixando EuroSAT RGB de espelho fixado usado pelo Torchvision...', flush=True)
        with urllib.request.urlopen(DATASET_URL, timeout=120) as response, archive.open('wb') as target:
            while chunk := response.read(1024 * 1024):
                target.write(chunk)
    md5 = hashlib.md5(archive.read_bytes()).hexdigest()
    if md5 != EXPECTED_MD5:
        raise ValueError(f'Integridade EuroSAT inválida: {md5}; arquivo não será usado.')
    sha256 = hashlib.sha256(archive.read_bytes()).hexdigest()
    folder = DATA / '2750'
    if not folder.exists():
        with zipfile.ZipFile(archive) as bundle:
            # Validação antes da extração, mesmo sendo um arquivo com hash esperado.
            for member in bundle.infolist():
                resolved = (DATA / member.filename).resolve()
                if not resolved.is_relative_to(DATA.resolve()):
                    raise ValueError('Caminho inválido no dataset.')
            bundle.extractall(DATA)
    return folder, {'url': DATASET_URL, 'md5': md5, 'sha256': sha256,
                    'authors': 'Patrick Helber, Benjamin Bischke, Andreas Dengel, Damian Borth',
                    'reference': 'https://github.com/phelber/EuroSAT',
                    'license': 'MIT; também observar termos dos dados Copernicus Sentinel',
                    'verifiedAt': datetime.now(timezone.utc).isoformat(),
                    'fetchedAt': None,
                    'provenanceNote': 'Hash verificado no treino. Momento original de download do arquivo local não foi preservado.'}


def make_split(folder, per_class, seed):
    """A mesma partição é usada em TODOS os experimentos; sem augmentação no teste."""
    partitions = {'train': [], 'validation': [], 'test': []}
    classes = sorted(CLASS_LABELS)
    for class_index, name in enumerate(classes):
        files = sorted((folder / name).glob('*.jpg'))
        random.Random(seed + class_index).shuffle(files)
        selected = files[:per_class] if per_class else files
        if len(selected) < 30:
            raise ValueError(f'Classe {name} não tem amostras suficientes.')
        n_train = int(len(selected) * 0.7)
        n_val = int(len(selected) * 0.15)
        for kind, paths in (
            ('train', selected[:n_train]),
            ('validation', selected[n_train:n_train + n_val]),
            ('test', selected[n_train + n_val:]),
        ):
            partitions[kind].extend((path, class_index) for path in paths)
    paths_by_kind = [{str(path) for path, _ in rows} for rows in partitions.values()]
    assert all(not a.intersection(b) for i, a in enumerate(paths_by_kind) for b in paths_by_kind[i + 1:])
    return classes, partitions


def load_partition(rows):
    arrays, targets = [], []
    for path, target in rows:
        with Image.open(path) as image:
            arrays.append(np.array(image.convert('RGB').resize((64, 64)), dtype=np.uint8))
        targets.append(target)
    values = torch.from_numpy(np.stack(arrays)).permute(0, 3, 1, 2).float() / 255
    return TensorDataset(values, torch.tensor(targets, dtype=torch.long))


def evaluate(model, loader, classes):
    model.eval()
    matrix = np.zeros((classes, classes), dtype=np.int64)
    loss = 0.0
    criterion = nn.CrossEntropyLoss(reduction='sum')
    with torch.inference_mode():
        for images, targets in loader:
            logits = model(images)
            loss += criterion(logits, targets).item()
            predicted = logits.argmax(1)
            for actual, guess in zip(targets.tolist(), predicted.tolist()):
                matrix[actual, guess] += 1
    counts = matrix.sum(axis=1)
    precision = np.divide(matrix.diagonal(), matrix.sum(axis=0), out=np.zeros(classes), where=matrix.sum(axis=0) > 0)
    recall = np.divide(matrix.diagonal(), counts, out=np.zeros(classes), where=counts > 0)
    f1 = np.divide(2 * precision * recall, precision + recall, out=np.zeros(classes), where=(precision + recall) > 0)
    total = int(matrix.sum())
    return {'accuracy': float(matrix.trace() / total), 'macroF1': float(f1.mean()),
            'loss': loss / total, 'samples': total, 'confusionMatrix': matrix.tolist(),
            'perClass': [{'precision': float(p), 'recall': float(r), 'f1': float(f), 'support': int(n)}
                         for p, r, f, n in zip(precision, recall, f1, counts)]}


def run(args):
    torch.set_num_threads(args.threads)
    torch.use_deterministic_algorithms(True)
    folder, source = prepare_dataset()
    classes, partitions = make_split(folder, args.per_class, args.seed)
    datasets = {key: load_partition(value) for key, value in partitions.items()}
    loaders = {key: DataLoader(dataset, batch_size=64, shuffle=False)
               for key, dataset in datasets.items()}
    split_manifest = {key: [str(path.relative_to(folder)).replace('\\', '/') for path, _ in rows]
                      for key, rows in partitions.items()}
    write_json(ARTIFACTS / 'split.json', split_manifest)
    experiments = [
        {'name': 'duas_camadas', 'filters': [16, 32], 'learningRate': 0.001},
        {'name': 'tres_camadas', 'filters': [16, 32, 64], 'learningRate': 0.001},
        {'name': 'mais_filtros', 'filters': [24, 48, 96], 'learningRate': 0.001},
        {'name': 'taxa_menor', 'filters': [16, 32, 64], 'learningRate': 0.0003},
    ]
    results, best_state, selected, best_score = [], None, None, -1.0
    for config in experiments:
        torch.manual_seed(args.seed)
        np.random.seed(args.seed)
        random.seed(args.seed)
        model = LandscapeCNN(config['filters'], classes=len(classes))
        optimizer = torch.optim.Adam(model.parameters(), lr=config['learningRate'])
        criterion = nn.CrossEntropyLoss()
        generator = torch.Generator().manual_seed(args.seed)
        training = DataLoader(datasets['train'], batch_size=64, shuffle=True, generator=generator)
        history, checkpoint, local_best = [], None, -1.0
        started = time.monotonic()
        for epoch in range(args.epochs):
            model.train()
            for images, targets in training:
                # Rotação em múltiplos de 90 graus e espelho somente no treino.
                if random.random() < 0.5:
                    images = images.flip(-1)
                images = images.rot90(random.randrange(4), (-2, -1))
                optimizer.zero_grad()
                loss = criterion(model(images), targets)
                loss.backward()
                optimizer.step()
            validation = evaluate(model, loaders['validation'], len(classes))
            history.append({'epoch': epoch + 1, 'validationAccuracy': validation['accuracy'],
                            'validationMacroF1': validation['macroF1'], 'validationLoss': validation['loss']})
            if validation['macroF1'] > local_best:
                local_best = validation['macroF1']
                checkpoint = copy.deepcopy(model.state_dict())
            print(f"{config['name']} época {epoch + 1}/{args.epochs}: val F1={validation['macroF1']:.3f}", flush=True)
        result = {**config, 'epochs': args.epochs, 'bestValidationMacroF1': local_best,
                  'parameters': sum(p.numel() for p in model.parameters()),
                  'seconds': round(time.monotonic() - started, 2), 'history': history}
        results.append(result)
        if local_best > best_score:
            best_score, selected, best_state = local_best, config, checkpoint
    # Só o modelo escolhido pela validação vê o teste, uma única vez.
    final_model = LandscapeCNN(selected['filters'], classes=len(classes))
    final_model.load_state_dict(best_state)
    test_metrics = evaluate(final_model, loaders['test'], len(classes))
    for name, scores in zip(classes, test_metrics['perClass']):
        scores['className'], scores['label'] = name, CLASS_LABELS[name]
    ARTIFACTS.mkdir(exist_ok=True)
    torch.save(best_state, ARTIFACTS / 'landscape.pt')
    manifest = {
        'name': 'TerritorioVivoCNN', 'version': '1.0.0', 'dataMode': 'trained_model',
        'trainedAt': datetime.now(timezone.utc).isoformat(), 'seed': args.seed,
        'classes': classes, 'labels': CLASS_LABELS, 'selectedExperiment': selected,
        'input': {'width': 64, 'height': 64, 'channels': 3, 'normalization': 'RGB / 255'},
        'dataset': source, 'splitCounts': {key: len(value) for key, value in partitions.items()},
        'selectionCriterion': 'Maior macro-F1 na validação; melhor época por esse critério.',
        'experiments': results, 'test': test_metrics,
        'majorityClassBaselineAccuracy': max(np.bincount([target for _, target in partitions['test']])) / len(partitions['test']),
        'limitations': LIMITATIONS, 'torchVersion': torch.__version__,
        'weightsSha256': hashlib.sha256((ARTIFACTS / 'landscape.pt').read_bytes()).hexdigest(),
    }
    write_json(ARTIFACTS / 'manifest.json', manifest)
    print(json.dumps({'selected': selected['name'], 'testAccuracy': test_metrics['accuracy'],
                      'macroF1': test_metrics['macroF1'], 'samples': manifest['splitCounts']}, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--epochs', type=int, default=4)
    parser.add_argument('--per-class', type=int, default=500, help='0 usa todo EuroSAT; default é experimento reduzido.')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--threads', type=int, default=4)
    arguments = parser.parse_args()
    if arguments.epochs < 1 or arguments.per_class < 0 or arguments.threads < 1:
        parser.error('Parâmetros inválidos.')
    run(arguments)
