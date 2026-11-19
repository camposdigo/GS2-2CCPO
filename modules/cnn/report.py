"""Figuras e relatório gerados a partir das métricas realmente publicadas."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent


def main():
    folder = ROOT / 'artifacts'
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    counts = manifest['splitCounts']
    total = sum(counts.values())
    epochs = max(experiment['epochs'] for experiment in manifest['experiments'])
    balanced = len({row['support'] for row in manifest['test']['perClass']}) == 1
    plt.rcParams.update({'font.size': 10, 'figure.dpi': 160, 'savefig.bbox': 'tight'})
    matrix = np.array(manifest['test']['confusionMatrix'])
    labels = [manifest['labels'][name] for name in manifest['classes']]
    figure, axis = plt.subplots(figsize=(10, 8))
    image = axis.imshow(matrix, cmap='Greens')
    axis.set(xticks=range(10), yticks=range(10), xticklabels=labels, yticklabels=labels,
             xlabel='Classe prevista', ylabel='Classe real', title=f"CNN própria · matriz de confusão no teste (n={counts['test']})")
    plt.setp(axis.get_xticklabels(), rotation=45, ha='right', rotation_mode='anchor')
    for row in range(10):
        for column in range(10):
            axis.text(column, row, str(matrix[row, column]), ha='center', va='center',
                      color='white' if matrix[row, column] > matrix.max() / 2 else '#153a2d', fontsize=8)
    figure.colorbar(image, ax=axis, label='Número de imagens')
    figure.savefig(folder / 'confusao.png')
    plt.close(figure)
    figure, axis = plt.subplots(figsize=(9, 4.5))
    for experiment in manifest['experiments']:
        history = experiment['history']
        axis.plot([row['epoch'] for row in history], [row['validationMacroF1'] for row in history],
                  marker='o', label=experiment['name'])
    axis.set(xlabel='Época', ylabel='Macro-F1 na validação', ylim=(0, 1), xticks=list(range(1, epochs + 1)),
             title='Experimentos · mesma partição · seleção sem consultar o teste')
    axis.grid(alpha=0.2)
    axis.legend()
    figure.savefig(folder / 'experimentos.png')
    plt.close(figure)
    rows = []
    for experiment in manifest['experiments']:
        rows.append(f"| {experiment['name']} | {experiment['filters']} | {experiment['learningRate']} | {experiment['parameters']} | {experiment['bestValidationMacroF1']:.4f} |")
    per_class = []
    for row in manifest['test']['perClass']:
        per_class.append(f"| {row['label']} | {row['precision']:.4f} | {row['recall']:.4f} | {row['f1']:.4f} | {row['support']} |")
    report = f"""# Resultado executado da CNN

Treinamento UTC: {manifest['trainedAt']}. Semente: {manifest['seed']}. PyTorch {manifest['torchVersion']}.

Dataset EuroSAT RGB; {total} imagens selecionadas, dez classes. Treino: {counts['train']}, validação: {counts['validation']}, teste: {counts['test']}. Teste balanceado: {'sim' if balanced else 'não'}. Arquivos não selecionados não participam do experimento. Divisão estratificada por arquivo, sem separação geográfica; limitações estão abaixo.

## Comparação na validação

| Configuração | Filtros | Taxa | Parâmetros | Melhor macro-F1 validação |
|---|---|---|---|---|
{chr(10).join(rows)}

Vencedor selecionado somente pela validação: **{manifest['selectedExperiment']['name']}**. A comparação de profundidade é duas_camadas vs tres_camadas; largura é tres_camadas vs mais_filtros; taxa é tres_camadas vs taxa_menor. {epochs} épocas por configuração não demonstram convergência. Oscilações indicam sensibilidade à otimização e possível sobreajuste; não é um estudo exaustivo.

![Evolução dos quatro experimentos](experimentos.png)

## Teste final do vencedor

- Acurácia: **{manifest['test']['accuracy']:.4%}**.
- Macro-F1: **{manifest['test']['macroF1']:.4f}**.
- Baseline da classe majoritária: **{manifest['majorityClassBaselineAccuracy']:.0%}**.
- Amostras: **{manifest['test']['samples']}**.

| Classe | Precisão | Recall | F1 | Suporte |
|---|---|---|---|---|
{chr(10).join(per_class)}

![Matriz de confusão no teste](confusao.png)

As métricas são classificatórias. Não medem qualidade da água, capacidade de prever crise hídrica nem benefício social em operação.

## Limitações

{chr(10).join('- ' + item for item in manifest['limitations'])}

Não há garantia de reprodutibilidade bit a bit em outras versões de PyTorch, CPU ou plataforma. O manifesto preserva versões, hashes, semente e lista dos arquivos da partição para auditoria. Comparar com o artigo original exigiria o protocolo completo; a precisão publicada pelos autores não é atribuída a este modelo.

Fonte: [EuroSAT — autores e licença](https://github.com/phelber/EuroSAT). Figuras produzidas por `report.py` a partir de `manifest.json`, sem métricas estimadas manualmente.
"""
    (folder / 'RESULTADOS.md').write_text(report, encoding='utf-8')
    print('Relatório e duas figuras gerados a partir do manifesto.')


if __name__ == '__main__':
    main()
