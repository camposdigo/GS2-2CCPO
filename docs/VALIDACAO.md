# Verificações executadas — Território Vivo

Execução no Windows em **9 de novembro de 2026, horário de São Paulo**. Artefatos com timestamps UTC podem mostrar 10/11, pois o teste atravessou a meia-noite UTC. Isto não altera a data local nem a data de observação dos dados. Resultados abaixo vêm das execuções e evidências, não de estimativas.

## Aplicação web e MongoDB

- **13 testes de API aprovados**: validação de corpo/filtros, persistência de demonstração após reabertura, gravações concorrentes, falha explícita de MongoDB, cabeçalhos/limites, dados hídricos, proxy CNN e CORS com allowlist/preflight.
- **MongoDB Community 8.2.12 real** executado como processo local em loopback, sem instalar serviço global. Cadastro HTTP retornou 201; API e banco foram reiniciados; a mesma ID reapareceu e uma consulta direta confirmou o documento. Banco de QA removido depois do teste. Evidência: [mongo-smoke.json](../web/evidence/mongo-smoke.json).
- Chrome desktop 1440 px e mobile 390 px: navegação, modal, formulário, dados reais e gráfico; sem exceções JavaScript nem rolagem horizontal da página. [browser-qa.json](../web/evidence/browser-qa.json), [desktop](../web/evidence/painel-desktop.png), [mobile](../web/evidence/painel-mobile.png).
- **Atualização visual em 10/11/2026:** menu lateral removido, navegação no topo, painel centralizado e cartões/tipografia revistos. Verificação em 1440, 390 e 320 px: quatro telas acessíveis pela navegação, seleção ativa, formulário e filtros funcionando, sem rolagem horizontal, erros JavaScript ou novas ocorrências gravadas. Cabeçalho também verificado em 960 e 1120 px e durante a rolagem. [Relatório do novo layout](../web/evidence/redesenho-qa.json), [verificação do cabeçalho](../web/evidence/redesenho-header-qa.json), [desktop](../web/evidence/redesenho-desktop.png), [celular](../web/evidence/redesenho-mobile.png).
- Dependências npm verificadas pelo agente responsável: zero vulnerabilidades reportadas no momento da instalação. Isso não é garantia permanente.
- O script `scripts/iniciar.ps1 -Demo` foi executado em uma porta isolada: iniciou o portal e a CNN com `/health` válido e modelo pronto. [Evidência de inicialização](evidence/inicializacao.json). Os processos de verificação foram encerrados depois.
- Docker Compose é uma opção documentada, mas **o teste real executado usou o binário portátil**, não Docker. A imagem do Compose segue o exemplo oficial MongoDB 9.0 e não foi executada nesta máquina.

## Dados hídricos

- Coleta real: **3.235 linhas diárias**, de 01/01/2018 a 09/11/2026, Cantareira, API oficial Sabesp. URLs, respostas brutas e SHA-256 preservados.
- **11 testes aprovados**, reprodução do snapshot offline e auditoria independente de métricas sobre **465 previsões** de teste.
- Modelo escolhido na validação: Ridge, alpha 10; horizonte sete dias. MAE **0,717844 p.p.**, RMSE **1,175562 p.p.**; persistência MAE **1,231190 p.p.**; deriva MAE **0,895677 p.p.**
- Intervalo nominal 90%: cobertura efetiva **83,871%** no teste completo, **83,5821%** em origens não sobrepostas. Limitação explicitada nos alertas; sem garantia de cobertura futura.
- Notebook de exploração executado e três gráficos científicos gerados. [Relatório](dados-hidricos.md), [avaliação](../modules/water/artifacts/evaluation.json).
- O snapshot entregue foi reproduzido offline a partir do cache oficial, o que está registrado em `freshness.offline`. Não se trata de dados sintéticos nem de nova coleta ao abrir o painel.

## CNN e integração

- Quatro CNNs/configurações treinadas do zero em PyTorch 2.15.0+cpu, quatro épocas cada, mesma partição e semente 42.
- EuroSAT RGB: subconjunto de **5.000 imagens**, 3.500 treino / 750 validação / 750 teste. Seleção pelo macro-F1 da validação; teste avaliado apenas para a configuração vencedora.
- Vencedora: `mais_filtros`, 78.282 parâmetros; acurácia de teste **68,1333%**, macro-F1 **0,689223**. Baseline majoritário: 10%.
- **6 testes aprovados**: formas/gradientes, rejeição de arquivo inválido/grande/pequeno, partição reproduzível e disjunta e inferência real com dez classes/pontuações normalizadas.
- **Integração HTTP real portal → FastAPI → pesos treinados** aprovada, incluindo `/health` e artefato hídrico real: [integracao.json](evidence/integracao.json). Uma imagem de teste foi classificada; isso verifica o encadeamento, não substitui a avaliação das 750 imagens.
- [Manifesto](../modules/cnn/artifacts/manifest.json), [relatório/figuras](../modules/cnn/artifacts/RESULTADOS.md) e pesos incluídos. Sem teste geográfico no Brasil; softmax não calibrada.

## Flutter

- Flutter **3.47.9**, Dart **3.13.7**, SDK isolado no projeto.
- **9 testes aprovados**: serialização/UTF-8, erro real da API, cache agregado/offline, preferência, resposta antiga de filtro descartada, limpeza de cache durante refresh, formulário inválido/falha de servidor e layout de 320×568 com texto 2×.
- **Análise estática final sem problemas** e **compilação web de produção concluída**. O compilador emitiu um aviso de fonte Cupertino não utilizada; os ícones Material usados pelo app foram incluídos e verificados nas telas. Nenhum APK é apresentado como gerado.
- Chrome com API real: dados oficiais, gráfico, alertas/limitações, consulta de ocorrências, preferência mantida após reload e cadastro de ocorrência sintética via formulário. OPTIONS 204 e POST 201 observados; sem erros JavaScript, requisições falhadas ou CORS. [Evidência](../mobile/evidence/flutter-web-qa.json), [painel](../mobile/evidence/flutter-web.png), [alertas](../mobile/evidence/flutter-alerts.png), [ocorrências](../mobile/evidence/flutter-occurrences.png).
- **Não executados:** APK, instalação em aparelho Android, emulador, testes físicos de leitor de tela e iOS. O projeto contém Android e web; Flutter não depende de Figma.

## POO, redes e Edge

- Java compilado com **OpenJDK 21.0.8**; **18 verificações aprovadas**. Classes abstratas, interface, encapsulamento, herança, estratégias, alertas explicados e recusa de leituras inválidas.
- Simulador Edge: **9 testes aprovados**, incluindo intertravamento, travessia, justiça, conservação e tratamento de dados censurados. No cenário sintético fixo, conflitos de sinal passaram de 24 para 0 segundos; conflitos com pedestres durante travessia, de 150 para 0. Há custos de espera para NS/pedestres, documentados. [Resultado](../modules/edge/results/demo-seed42.json).
- Núcleo C++ do controlador compilado com MSVC/C++17 e executado; verificações de intertravamento, justiça, manutenção, falha e rollover passaram.
- **Não executados:** compilação completa do sketch com core ESP32, gravação/OTA na placa ou validação na maquete. Referência de firmware não equivale a atualização física concluída.
- Redes: relatório é um cenário didático explicitamente identificado; nenhuma alteração foi feita em usuários, grupos, discos ou permissões deste computador. Aplicar ao caso específico do professor continua necessário.

## Limites de conclusão

Não foram acessados o portal acadêmico, rubricas restritas, hardware ou contas externas. Os nomes, RMs e a turma **2CCPO** foram preenchidos com as informações fornecidas pelos integrantes em [EQUIPE.md](EQUIPE.md). Não foi enviado trabalho, gravado vídeo ou publicado repositório. O código e a documentação são uma entrega integrada executável, mas os itens externos de [ENTREGA.md](ENTREGA.md) precisam ser atendidos antes de afirmar que todas as avaliações foram formalmente concluídas.
