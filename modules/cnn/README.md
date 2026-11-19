# CNN própria para paisagens — Território Vivo

Implementação em PyTorch de uma CNN criada do zero, sem pesos pré-treinados. A API local integra a classificação ao portal por `/api/classify`. Os pesos treinados e as métricas observadas estão em `artifacts/`.

## Reproduzir

Python 3.12 e CPU são suficientes. Na raiz:

```powershell
./.tools/python312/python.exe -m venv modules/cnn/.venv
./modules/cnn/.venv/Scripts/python.exe -m pip install -r modules/cnn/requirements.txt
cd modules/cnn
./.venv/Scripts/python.exe -X utf8 train.py --epochs 4 --per-class 500 --threads 4
./.venv/Scripts/python.exe -X utf8 report.py
./.venv/Scripts/python.exe -m unittest -v test_cnn.py
./.venv/Scripts/python.exe -m uvicorn app:app --host 127.0.0.1 --port 8001
```

O treino baixa EuroSAT RGB (~90 MB), verifica o MD5 publicado no [loader oficial do Torchvision](https://github.com/pytorch/vision/blob/main/torchvision/datasets/eurosat.py), calcula SHA-256 e preserva a partição por arquivo. O espelho é fixado em uma revisão. O instante original de download do arquivo já presente nesta sessão não foi preservado; o manifesto registra `fetchedAt: null` e o instante da verificação do hash, sem inventar proveniência temporal. Reinicie a API após retreinar: os pesos são mantidos em cache durante o processo.

`--per-class 0` utiliza todas as imagens; o resultado entregue é explicitamente um **experimento reduzido de 5.000 imagens**: 3.500 treino, 750 validação e 750 teste. A semente é 42. Cada classe contribui com 350/75/75 arquivos, respectivamente. Não há treino no conjunto de teste; augmentação só ocorre no treino.

## Arquitetura e experimentos

Cada bloco contém convolução 3×3, BatchNorm, ReLU e MaxPool. O classificador usa pooling adaptativo, camada densa, ReLU, dropout 0,25 e dez logits. Entrada RGB 64×64 normalizada por 255. Otimizador Adam e entropia cruzada.

| Experimento | Filtros por bloco | Taxa de aprendizado | Comparação |
|---|---|---|---|
| duas_camadas | 16, 32 | 0,001 | Referência de menor profundidade |
| tres_camadas | 16, 32, 64 | 0,001 | Adição de um bloco |
| mais_filtros | 24, 48, 96 | 0,001 | Maior largura, comparada a tres_camadas |
| taxa_menor | 16, 32, 64 | 0,0003 | Taxa menor, comparada a tres_camadas |

Mesma partição e semente para todos; quatro épocas por configuração. A melhor época de cada configuração é escolhida por macro-F1 na validação, e a configuração vencedora também. Somente então o teste é avaliado uma vez. Maior profundidade ou mais filtros não garantem melhor generalização; confira também as oscilações entre épocas no manifesto.

Resultado executado: **mais_filtros**, acurácia **68,13%**, macro-F1 **0,6892** no teste de 750 imagens; baseline da classe majoritária **10%**. Isso é o desempenho deste experimento reduzido, não o resultado do artigo original EuroSAT. [Relatório e figuras](artifacts/RESULTADOS.md).

## API e privacidade

- `GET /health`: carrega/verifica o modelo local e informa `modelReady`.
- `POST /api/classify`: multipart `file`, JPEG/PNG, até 5 MB, mínimo 32×32; rejeita imagem inválida ou dimensões excessivas.
- Retorno: classe sugerida, pontuações das dez classes, versão/métricas do modelo, limitações e `requiresHumanReview: true`.
- Sem pesos válidos, retorna 503; não cria classificação fictícia.
- Uploads não são persistidos. A inferência roda no threadpool do FastAPI; para o protótipo, mantenha o serviço no loopback e use o proxy do portal, que limita requisições.
- A pontuação softmax é **não calibrada**; não deve ser rotulada como probabilidade real de acerto.

O portal espera `CLASSIFIER_URL=http://127.0.0.1:8001` e encaminha arquivos para este serviço. Há smoke test da integração em `scripts/verificar-integracao.py`; ele depende do dataset local baixado.

## Limitações e fontes

O [EuroSAT](https://github.com/phelber/EuroSAT), de Helber, Bischke, Dengel e Borth, foi construído com imagens Sentinel-2 europeias e dez classes. O dataset é disponibilizado sob MIT pelo repositório dos autores; a licença está em `artifacts/EuroSAT-LICENSE.txt`. Também se aplicam os termos do Copernicus Sentinel, indicados pelos autores. Referência: Helber et al., *EuroSAT: A Novel Dataset and Deep Learning Benchmark for Land Use and Land Cover Classification*, 2019, [artigo](https://arxiv.org/abs/1709.00029).

A separação é estratificada por arquivo, **não por região geográfica**. Imagens próximas podem inflar métricas. Não houve validação no Brasil; uma foto comum fora do domínio ainda pode produzir pontuação alta. O modelo não mede volume, qualidade da água, potabilidade ou risco de racionamento. Uma classe isolada não comprova mudança de uso do solo: isso requer comparação temporal e validação adicional.

Uso de IA generativa: assistência na escrita/revisão do código, análise de falhas e documentação. As métricas provêm de execução do treino e teste, sem imagens sintéticas no dataset. Antes de implantação, ampliar treino, realizar divisão geográfica, avaliar calibração e detecção de imagens fora do domínio e verificar dados brasileiros autorizados.
