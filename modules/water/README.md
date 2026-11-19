# Território Vivo — dados hídricos e aprendizado de máquina

Este módulo trabalha exclusivamente com observações reais do **Sistema Cantareira (ID 64)** do Portal dos Mananciais da SABESP. O recorte não equivale à totalidade da RMSP: o resumo diário também preserva os demais sistemas, mas o modelo estima apenas o Cantareira.

## Executar no Windows / PowerShell

Python 3.12 recomendado; a coleta e a auditoria de métricas usam somente a biblioteca padrão. O treino usa as versões de `requirements.txt`.

```powershell
# Na raiz do projeto; ou use py -3.12 em uma instalação própria.
./.tools/python312/python.exe -m venv modules/water/.venv
./modules/water/.venv/Scripts/python.exe -m pip install -r modules/water/requirements.txt

# Coleta oficial até a data local desejada. Não consulta datas posteriores ao corte.
python modules/water/update.py --as-of 2026-11-09

# Reproduzir exatamente a coleta entregue, sem acesso à rede, verificando SHA-256.
python modules/water/update.py --as-of 2026-11-09 --offline

# Seleção por validação, calibração, teste temporal e geração de dashboard.json.
./modules/water/.venv/Scripts/python.exe modules/water/train.py --as-of 2026-11-09

# Auditoria independente dos erros e cobertura, sem sklearn.
python modules/water/evaluate.py

# Exploração e figuras SVG a partir dos dados reais e do teste publicado.
./modules/water/.venv/Scripts/python.exe modules/water/analyze.py

# Testes: integridade de cache, falta de dados, limites, ausência de vazamento.
./modules/water/.venv/Scripts/python.exe -m unittest discover -s modules/water -p test_water.py -v
```

Em Linux/macOS, use `python3.12 -m venv modules/water/.venv` e `modules/water/.venv/bin/python`. A pasta `.tools` e os ambientes não são necessários para usar o código em outra máquina; são facilidades locais.

## Arquivos entregues

| Arquivo | Conteúdo |
|---|---|
| `data/raw/<sha256>.json` | Respostas oficiais exatas, sem correção ou substituição de valores |
| `data/manifest.json` | URL, instante UTC da coleta, HTTP status, tamanho, SHA-256 e caminho de cada resposta |
| `data/cantareira.csv` | Série diária normalizada com unidades nos nomes das colunas |
| `data/current_rmsp.json` | Resumo oficial dos sistemas produtores RMSP no corte |
| `data/quality.json` | Cobertura, nulos, lacunas, hash CSV e data de observação |
| `artifacts/evaluation.json` | Divisões, candidatos, seleção, baselines e avaliação reproduzível |
| `artifacts/model.json` | Modelo ajustado e congelado, em JSON inspecionável, sem pickle |
| `artifacts/test_predictions.csv` | Uma previsão a sete dias por origem do teste, alvo real e intervalos |
| `artifacts/dashboard.json` | Contrato do site, proveniência, volume real, estimativa e alertas |
| `analise.ipynb` | Notebook de exploração e leitura comentada dos resultados |

Não há série sintética no módulo. Os pequenos números construídos em `test_water.py` são apenas casos unitários e não entram no treino, métricas ou produto.

## Modelo e avaliação

O alvo é a **variação do volume útil em pontos percentuais entre t e t+7**. A previsão de volume soma essa variação ao volume observado em t. Cada entrada usa dados disponíveis até t: volumes defasados, variações de 1/7/14 dias, chuva acumulada de 7/14 dias, vazão afluente/captada média de sete dias e seno/cosseno anual. Não usa chuva futura nem dados do alvo como entrada.

Seis candidatos são treinados: Ridge com `alpha` 0,1 / 1 / 10 / 100, e Random Forest com duas configurações de profundidade/folha, 180 árvores e semente 42. O `StandardScaler` do Ridge é ajustado somente no treino. O modelo com menor MAE na validação é congelado; calibração e teste não ajustam o modelo nem escolhem hiperparâmetros.

As observações são divididas cronologicamente em 60% treino, 15% validação, 10% calibração e 15% teste. **A janela inteira de entrada (14 dias anteriores) e o alvo (+7) precisam estar dentro da mesma partição.** Isso exclui 21 origens por fronteira e impede sobreposição de janelas brutas entre partições. Observações incompletas ou datas faltantes descartam a janela, sem interpolação. O teste compara os mesmos alvos e datas contra persistência `V(t+7)=V(t)` e deriva de sete dias. MAE/RMSE estão em pontos percentuais, não em porcentagem relativa.

O intervalo de 90% usa o quantil superior dos resíduos absolutos da calibração com origens a cada sete dias. A cobertura é medida no teste completo e também em origens do teste a cada sete dias. Como resíduos hidrológicos têm dependência temporal e mudanças de regime, **90% é o nível nominal; não existe garantia estatística de cobertura futura neste projeto**. O artefato publica a cobertura efetivamente obtida, largura e tamanho das amostras.

`evaluate.py` recalcula MAE/RMSE e cobertura diretamente do CSV de previsões e exige correspondência com as métricas publicadas; não precisa retreinar. Para atualizar a previsão, execute coleta e treino novamente. Um novo resultado deve ser versionado: mudar os dados altera também as datas da divisão proporcional.

## Fontes, licença e responsabilidade

- [Portal dos Mananciais — SABESP](https://mananciais.sabesp.com.br/), API pública usada pelo próprio portal: `/api/v4/dados/ultima-data`, `/api/v4/parametros`, `/api/v4/sistemas/64/dados/diario/{inicio}/{fim}` e `/api/v4/sistemas/dados/resumo-diario/{data}`. As URLs concretas estão no manifesto.
- [Resolução Conjunta ANA/DAEE 925/2017, art. 4º e 6º](https://www.gov.br/ana/pt-br/legislacao/resolucoes/resolucoes-regulatorias/2017/925): referência numérica das faixas. O enquadramento operacional é mensal e depende da autoridade competente; o rótulo diário no protótipo não substitui essa decisão.
- [Sala de Situação SP-Águas](https://hub.spaguas.sp.gov.br/): conferência de contexto e situação do sistema; não foi usada para fabricar/mesclar observações da série Sabesp.

Licença específica de reutilização não foi localizada no portal SABESP. O manifesto registra `not-specified-by-source`; acesso público não é declaração de licença aberta. Os arquivos são evidência acadêmica com atribuição; confirmar termos antes de redistribuição comercial. Dados ambientais não contêm dados pessoais.

O modelo não estima potabilidade, não autoriza captação/restrição de água e não decide por municípios. Alertas sempre têm justificativa, limitações, `requiresHumanReview: true` e `confidence: null`: cobertura histórica não é probabilidade de acerto de um caso individual. A estimativa perde validade operacional no protótipo após dois dias sem nova observação; o site deve recalcular essa idade a partir de `observedAt` na data atual de São Paulo.

Falha na fonte ou treino gera `dataMode: "unavailable"`, sem números/previsões inventados, e código de saída 1. O CSV anterior é preservado para auditoria, mas não publicado como se a coleta tivesse sido bem-sucedida. `--offline` é uma reprodução explícita de um snapshot e não uma nova consulta à fonte.
