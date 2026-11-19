# Território Vivo — Global Solution 2026.2

Projeto integrado das **oito disciplinas** do PDF `GS2026.2 - FEV.pdf`. Tema: **Territory Predictive Insights**. Portal de ocorrências urbanas, inteligência hídrica da RMSP, aplicativo Flutter e classificação experimental de paisagens, com laboratórios de redes, POO e Edge.

O código e os relatórios ficam nesta pasta. O estado das verificações está em [docs/VALIDACAO.md](docs/VALIDACAO.md); o que precisa ser conferido com cada professor está em [docs/ENTREGA.md](docs/ENTREGA.md). O projeto é acadêmico e local; nenhuma ocorrência é enviada a uma prefeitura e nenhuma decisão de racionamento é executada.

## Abrir o portal nesta máquina

Na raiz, pelo PowerShell:

```powershell
# Visualização com ocorrências de demonstração identificadas como sintéticas.
# Os indicadores hídricos continuam sendo os dados oficiais identificados no painel.
powershell -ExecutionPolicy Bypass -File scripts/iniciar.ps1 -Demo
```

Abra **http://localhost:3000**. O script inicia também a API local da CNN, quando o ambiente está disponível. Ctrl+C encerra essa execução. O classificador exige os pesos de treinamento em `modules/cnn/artifacts/`.

Atalho no Windows: dê dois cliques em `INICIAR-DEMO.cmd` e depois abra esse endereço no navegador.

Para validar **MongoDB**, requisito de Application Development:

```powershell
# Opção com Docker instalado; banco restrito ao loopback local.
docker compose up -d mongo
powershell -ExecutionPolicy Bypass -File scripts/iniciar.ps1
```

Também é possível iniciar MongoDB Community diretamente ou informar uma instância própria em `MONGO_URI`. Não é necessário Docker quando há um `mongod` funcionando. Sem banco, o modo MongoDB retorna indisponibilidade; ele não troca silenciosamente para demonstração. A URI padrão é `mongodb://127.0.0.1:27017/territorio_vivo`. O modo demo grava JSON separado e **não substitui MongoDB**.

## Estrutura das oito disciplinas

| Disciplina | Entrega |
|---|---|
| Operating Systems and Computer Networks | [Relatório de grupos, SMB/NTFS, herança, RAID e backup](docs/redes.md) |
| Software Engineering | [Requisitos](docs/REQUISITOS.md), [engenharia e arquitetura](docs/ENGENHARIA.md), [roteiro de pitch](docs/PITCH.md) |
| Data Science and Analytics | [Pipeline e notebook](modules/water/README.md), [relatório dos dados hídricos](docs/dados-hidricos.md) |
| Application Development | [Portal Node.js + Express + MongoDB](web/README.md) |
| Object-Oriented Programming | [Java: sensores, abstrações, encapsulamento e estratégias](modules/poo/README.md) |
| Cross-Platform Application Development | [App Flutter](mobile/README.md) |
| Edge Computing | [Simulação, análise e firmware ESP32 com OTA](modules/edge/README.md) |
| Aprendizado Profundo com CNN | [CNN própria, experimentos, métricas e inferência web](modules/cnn/README.md) |

## Dados e modelos

O módulo hídrico usa **3.235 observações diárias reais do Cantareira, de 01/01/2018 a 09/11/2026**, obtidas da [API pública do Portal dos Mananciais da Sabesp](https://mananciais.sabesp.com.br/). Mantém respostas brutas, URLs, hashes, dados tratados e avaliação. O modelo selecionado na validação temporal estima volume útil em sete dias; o teste é separado do treino e da calibração. Não se deve tratar a projeção como previsão oficial, disponibilidade por bairro ou indicação de potabilidade. Leia os limites e a cobertura observada no relatório.

A CNN é criada do zero em PyTorch, com quatro configurações controladas de profundidade, filtros e taxa de aprendizado. O [EuroSAT RGB](https://github.com/phelber/EuroSAT) contém paisagens europeias; não há comprovação de desempenho na RMSP. Pontuações softmax não são probabilidades calibradas de acerto. O manifesto e a matriz de confusão registram os resultados efetivamente obtidos.

## Preparar em outra máquina

Requisitos: Node.js 22+, Python **3.12**, MongoDB Community, JDK 17+ e Flutter estável para os respectivos módulos. Docker é opcional. Os SDKs e ambientes locais em `.tools/` e `.venv/` ficam fora do pacote de entrega.

```powershell
# Python install manager moderno: extração local, sem mudar o Python padrão.
py install --target=.\.tools\python312 3.12
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1

# Somente dependências do portal:
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1 -OnlyWeb
```

Sem o Python install manager, crie manualmente os ambientes com Python 3.12 e instale `modules/water/requirements.txt` e `modules/cnn/requirements.txt`, conforme os READMEs dos módulos. Não instale dependências de ML no Python global.

```powershell
# API web sozinha, em demonstração explícita:
cd web
npm.cmd ci
$env:DEMO_MODE = 'true'
npm.cmd start
```

Para executar Flutter, use um SDK instalado ou `.tools/flutter/bin/flutter.bat` nesta máquina; o guia de `mobile/` inclui emulador Android e execução web.

## Testar e reproduzir

```powershell
# Portal
cd web
npm.cmd test
cd ..

# Dados hídricos: auditoria independente e testes
python modules/water/evaluate.py
./modules/water/.venv/Scripts/python.exe -m unittest discover -s modules/water -p test_water.py -v

# CNN: o treino baixa EuroSAT (~90 MB) se necessário
cd modules/cnn
./.venv/Scripts/python.exe -X utf8 train.py --epochs 4 --per-class 500
./.venv/Scripts/python.exe -m unittest -v test_cnn.py
cd ../..

# POO e Edge
powershell -ExecutionPolicy Bypass -File modules/poo/run.ps1 -Test
python -m unittest discover -s modules/edge -p test_simulate.py -v

# Flutter: com flutter no PATH
cd mobile
flutter analyze
flutter test
flutter build web --dart-define=API_BASE_URL=http://localhost:3000
```

Após retreinar a CNN, reinicie a API de inferência para carregar os novos pesos. Atualizar dados hídricos exige executar os scripts de coleta e treino; a plataforma não promete atualização contínua sem agendamento.

## Entrega e identificação

A identificação dos três integrantes da turma **2CCPO** está em [docs/EQUIPE.md](docs/EQUIPE.md). Confira os enunciados complementares e siga [docs/ENTREGA.md](docs/ENTREGA.md). O PDF informa **19/11/2026** como prazo máximo geral e pitch de até três minutos para concorrer ao prêmio.

```powershell
python scripts/empacotar.py
```

O ZIP é gerado em `dist/Territorio-Vivo-GS2026.2.zip`, com código, documentação, evidências e pesos; exclui segredos, dependências, SDKs, registros de execução e o dataset completo da CNN. O EuroSAT pode ser baixado novamente pelo script de treino. Não há publicação externa automática.
