# Global Solution 2026.2 — Software Engineering
## Planejamento Scrum: Território Vivo / Territory Predictive Insights

**Turma:** 2CCPO (FIAP, Ciência da Computação)  
**Equipe:** Rodrigo Campos Cordeiro (RM 566386), Gabriel De Biasi Couto (RM 563247) e João Pedro da Silva Costa (RM 565031)  
**Projeto:** [GS2-2CCPO](https://github.com/camposdigo/GS2-2CCPO)  
**Quadro Trello:** [GS 2026.2 — Território Vivo — Software Engineering](https://trello.com/b/oeQWcKWh/gs-20262-territ%C3%B3rio-vivo-software-engineering)  
**Data de organização do plano:** 19/11/2026

> **Nota de evidência:** este plano foi organizado a partir do estado do código e dos relatórios de validação já publicados. As entregas marcadas como feitas são os *incrementos técnicos demonstrados* na documentação, e não uma afirmação de que cerimônias Scrum ocorreram em cada data. Responsabilidades abaixo são uma **proposta de distribuição**, a validar com os integrantes. A data limite geral de 19/11 consta da apresentação da GS; o horário exato deve ser confirmado no portal.

## Visão do produto

A plataforma CitizenTech Território Vivo reúne relatos de infraestrutura urbana e dados hídricos oficiais da RMSP (Cantareira), analisa padrões e previsões com modelos estatísticos, apresenta dashboards e alertas explicados, e inclui uma CNN experimental de paisagens integrada ao portal. O protótipo não envia ocorrências à prefeitura, não realiza decisões de racionamento e não afirma impactos sociais já medidos.

**Usuários-alvo:** cidadão que registra problemas, analista que avalia padrões/dados e gestor que interpreta evidências sob revisão humana.

**Resultados sociais pretendidos (não comprovados no protótipo):** melhorar triagem de ocorrências, transparência de indicadores, planejamento e capacidade de análise de alertas, a medir futuramente por tempo de triagem, cobertura territorial, falso alarme e antecedência de alerta. Ver [Engenharia](ENGENHARIA.md).

## Quadro obrigatório

O Trello contém exatamente as três listas solicitadas pelo enunciado de Software Engineering:

1. **PRODUCT BACKLOG** — itens priorizados fora do escopo da entrega corrente, com prioridade P1/P2, responsável proposto, sprint futura, data indicativa, riscos e critérios de aceite.
2. **SPRINT EM ANDAMENTO** — objetivos e atividades da Sprint 3 (fechamento do projeto e da entrega).
3. **SPRINTS FEITAS** — incrementos demonstráveis das Sprints 1 e 2, ligados ao código, testes e documentação do repositório.

**Ordenação:** P0 = crítico para entrega; P1 = importante / com dependência; P2 = evolução opcional. Os cartões do backlog estão em ordem P1 → P2, e os já selecionados para S3 foram movidos para andamento. Datas de cartão são *metas internas*, não o horário oficial da FIAP.

## Planejamento das sprints

| Sprint | Janela planejada | Objetivo | Incremento demonstrável | Responsabilidade proposta |
|---|---|---|---|---|
| **S1 — Dados e serviços** | **04–09/11** (6 dias corridos) | Definir escopo, contratos, dados e persistência | RF01–03 documentados, API de ocorrências/MongoDB, fonte Sabesp tratada e rastreável | Rodrigo (requisitos), Gabriel (dados), João (API) |
| **S2 — Inteligência e UX** | **10–15/11** (6 dias corridos) | Construir análises, modelos, dashboards e apps | modelo temporal e métricas, CNN/inferência, web/Flutter e evidências | Gabriel (modelos), João (UI/Flutter), Rodrigo (QA/integração) |
| **S3 — Validação e entrega** | **16–19/11** (4 dias corridos) | Conferir enunciado, limites, integração e entregável Scrum | documentação com Trello, rastreabilidade, PDF com link e prints reais, pendências explicitadas | Rodrigo (rubrica/PDF), Gabriel (atualidade hídrica), João (smoke test) |

**Capacidade:** trio de estudantes; distribuição qualitativa por especialidade e paralelismo, sem alegar horas disponíveis ou velocidade medida. Tarefas dependentes podem avançar após liberação técnica. Limite de trabalho em andamento recomendado: uma atividade principal por pessoa.

### Sprint 1 — escopo, dados e persistência

**Meta:** possibilitar fluxo mínimo de observações urbanas e dados hídricos com procedência, sem dados fabricados.  
**Itens selecionados:** requisitos e arquitetura; coleta/tratamento Cantareira; portal API/MongoDB.  
**Dependências:** API Sabesp, ambiente Node/MongoDB, interpretação do PDF.  
**Riscos:** falha de fonte, dados desatualizados e validação apenas em modo de demonstração.  
**Definition of Done:** RF01–RF03 com critérios de aceite; cadastro e consulta persistentes em banco real; origem/unidade/período e hash dos dados documentados; teste reproduzível e link de evidência.  
**Evidência técnica:** [REQUISITOS.md](REQUISITOS.md), [ENGENHARIA.md](ENGENHARIA.md), [dados-hidricos.md](dados-hidricos.md), [VALIDACAO.md](VALIDACAO.md), [mongo-smoke.json](../web/evidence/mongo-smoke.json).

### Sprint 2 — padrões, predição e experiência

**Meta:** transformar dados em informações contextualizadas e acessíveis, com avaliação e alertas fundamentados.  
**Itens selecionados:** previsão temporal 7 dias + baselines e intervalos; CNN própria; dashboards web/Flutter; QA técnico.  
**Dependências:** dados e API de S1, pesos treinados, validação temporal correta.  
**Riscos:** vazamento temporal, falsa confiança de softmax, domínio europeu de treinamento da CNN, cobertura de previsão inferior à nominal, limitações mobile.  
**Definition of Done:** métricas de validação/teste publicadas, comparação de baseline, ausência de automação de decisões de alto impacto, fontes e incertezas visíveis, inferência real e verificações web/Flutter documentadas.  
**Evidência técnica:** [VALIDACAO.md](VALIDACAO.md), [avaliação hídrica](../modules/water/artifacts/evaluation.json), [CNN](../modules/cnn/README.md), [QA web](../web/evidence/redesenho-qa.json) e [QA Flutter](../mobile/evidence/flutter-web-qa.json).

### Sprint 3 — revisão, auditoria e entrega acadêmica

**Meta:** organizar formalmente o Scrum, revisar a aderência ao enunciado específico e produzir o documento de entrega.

**Itens selecionados:** leitura da rubrica; verificação da atualidade hídrica; smoke test do conjunto; capturas reais do Trello e PDF.  
**Dependências:** acesso ao portal FIAP, Trello navegável, repositório e ambientes para reexecução.  
**Riscos/impedimentos atuais:** horário oficial de envio não confirmado; artefato hídrico observado apenas até 09/11; validações físicas de Android e ESP32 indisponíveis; capturas autenticadas do Trello dependem de navegador conectado.  
**Definition of Done:** quadro público com 3 listas, objetivos/duração/cronograma e responsáveis propostos, backlog priorizado, critérios claros e atualização por progresso; rubricagem conferida no portal; PDF legível com **capturas reais**, não apenas diagramas; envio pelo estudante antes do prazo oficial.

**Regra para fechamento:** somente mover um cartão à lista SPRINTS FEITAS quando tiver DoD satisfeito e evidência verificável. Uma data vencida não significa conclusão.

## Rotina Scrum e gestão de impedimentos

- **Planejamento:** no início de cada sprint, definir objetivo, capacidade qualitativa, dependências e cartões; revisão do escopo à medida que surjam novos critérios do professor.
- **Daily assíncrona sugerida (10 min):** cada pessoa registra o que concluiu, próximo passo e impedimento nos comentários do cartão. Esta é uma política proposta, não relato de reuniões anteriores.
- **Impedimentos:** registrar bloqueio no cartão, responsável, próximo teste e impacto no DoD; redirecionar capacidade; não marcar feito quando falta evidência.
- **Review:** demonstrar incremento, conferir critérios de aceite e salvar links dos testes.
- **Retrospectiva:** registrar gargalos, qualidade de integração e mudanças para a sprint seguinte.
- **Refinamento de backlog:** ordenar por risco e valor social, dividir tarefas grandes e passar itens selecionados para SPRINT EM ANDAMENTO.

## Priorização e recorte do escopo

**P0 selecionado para S3:** conferência da rubrica; qualidade/data de corte dos dados; smoke test; PDF e prints.

**P1 pós-GS (não bloqueante para a versão web):** testes Android, firmware em ESP32 físico e acessibilidade assistiva.  
**P2 futuro:** moderação e autenticação administrativa; validação nacional/territorial dos modelos; integração com órgãos e mensuração prospectiva do benefício social.

**Política de qualidade:** informações sintéticas rotuladas, dados reais com fonte e datas, previsão nunca apresentada como decisão oficial e lacunas de execução explicitadas.

## Matriz de riscos

| Risco | Impacto | Mitigação / evidência |
|---|---|---|
| Dados Sabesp desatualizados | Alertas incorretos | Mostrar última observação; reprocessar apenas com testes; [dados-hidricos.md](dados-hidricos.md) |
| Vazamento temporal e incerteza | Modelo superestimado | Split temporal, baseline, cobertura empírica de intervalo e revisão humana |
| CNN fora do domínio brasileiro | Classificação não generalizável | Apontar EuroSAT europeu e limitações; não afirmar acurácia na RMSP |
| Demo no lugar de MongoDB | Requisito não provado | Apresentar [teste de persistência real](../web/evidence/mongo-smoke.json) |
| Hardware não validado | Segurança de trânsito | Não alegar implantação; teste físico e OTA como backlog futuro |
| Escopo e horário do portal | Entrega acadêmica incompleta | Conferir regra e prazo oficial antes do envio |
| Falta de prints reais do Trello | Perda de evidência da rubrica | Capturar o quadro e os cartões no Trello autenticado e incorporar ao PDF |

## Arquivos a apresentar

- [Quadro Scrum público](https://trello.com/b/oeQWcKWh/gs-20262-territ%C3%B3rio-vivo-software-engineering)
- [Requisitos](REQUISITOS.md) e [Engenharia de Software](ENGENHARIA.md)
- [Validação](VALIDACAO.md), [Pendências de entrega](ENTREGA.md) e [Equipe](EQUIPE.md)
- **PDF específico de Software Engineering:** link do Trello e capturas reais das três listas, backlog ordenado e planejamento das três sprints.

> Revisão final ainda necessária: confirmar restrições do portal, horários de envio e inserir screenshots reais do quadro. O planejamento do Trello está disponível e pode ser acompanhado pela equipe.
