# Preparação para entrega — GS 2026.2

O projeto foi implementado a partir da apresentação geral. Este checklist distingue o que pode ser demonstrado no computador do que exige a atividade específica, laboratório ou identificação da equipe. Não substitui a rubrica dos professores.

## Antes do envio

- [x] Preencher integrantes, RMs e turma em `EQUIPE.md`: três integrantes da turma **2CCPO**.
- [ ] Conferir os oito enunciados detalhados no portal; adequar nomes, formatos e exigências de cada disciplina.
- [ ] Executar os módulos usando os guias e ler `VALIDACAO.md`.
- [ ] Verificar a data das observações hídricas e atualizar coleta/treino se a apresentação exigir dados mais recentes.
- [ ] Gravar demonstrações ou capturas adicionais exigidas pelo professor.
- [ ] Gerar/regerar ZIP com `python scripts/empacotar.py` depois de preencher os dados da equipe.
- [ ] Enviar cada avaliação ao professor da disciplina no portal, até **19/11/2026**; confirmar o horário limite no portal.
- [ ] Se concorrer ao prêmio, gravar e enviar pitch de **até três minutos** ao Scrum Master; roteiro em `PITCH.md`.

## O que mostrar por disciplina

| Disciplina | Código/relatório e evidência | Dependência ainda externa |
|---|---|---|
| SO e Redes | `redes.md`: grupos, SMB/NTFS, herança/negação, RAID e backup | Substituir/adaptar o cenário didático pelo caso real de usuários, permissões e discos do professor; executar no ambiente do laboratório se exigido |
| Software Engineering | `REQUISITOS.md`, `ENGENHARIA.md`, arquitetura Mermaid, critérios de aceite e riscos | Confirmar documentos, diagramas, metodologia e formato cobrados |
| Data Science | `modules/water/`: CSV/cache oficial, notebook executado, figuras, métricas e alertas | Validar escopo específico e atualizar dados na data da apresentação; nenhum sistema foi conectado a decisões reais de abastecimento |
| Application Development | Portal/API em Node+Express+MongoDB; testes e persistência real em `web/evidence/mongo-smoke.json` | Iniciar sua instância MongoDB na apresentação; dados demo não substituem banco real |
| POO | Fontes Java, exemplo e 18 verificações | Confirmar linguagem/formato se o enunciado específico exigir outra linguagem |
| Flutter | App, análise estática, testes, build web e evidências de navegador | Compilar/instalar e demonstrar em aparelho/emulador Android se exigido; testes físicos e leitor de tela não foram presumidos |
| Edge | Simulador, comparação e firmware de referência com OTA/intertravamento | Dados de fluxo, pinos, componentes e firmware do professor; compilar o sketch completo e validar atualização na maquete compatível |
| CNN | CNN própria treinada, quatro experimentos, teste final, matriz de confusão e integração web real | Conferir dataset/protocolo exigido; não alegar validação brasileira ou ganho ambiental observado |

## Como apresentar as limitações

- Dados hídricos são reais e atribuídos à Sabesp, com datas e hashes. O modelo é acadêmico, estima apenas Cantareira e não decide racionamento.
- A cobertura efetiva dos intervalos é inferior à nominal; informe ambas e não transforme softmax/cobertura em certeza individual.
- A CNN foi treinada em subconjunto balanceado de EuroSAT europeu. A divisão é por arquivo; proximidade geográfica pode inflar o resultado.
- Os exemplos de ocorrências e os fluxos do simulador são sintéticos e identificados. Nenhum envio é feito a órgãos públicos.
- Simulação e testes C++ não comprovam segurança do firmware no hardware. A atualização remota precisa da maquete e de manutenção local autorizada.
- Benefícios sociais propostos não foram medidos em implantação. Não alegar redução real de consumo, acidentes ou tempo de atendimento.

## Conteúdo do ZIP

Código, READMEs, documentação, PDF original, amostras oficiais hídricas com procedência, notebook, resultados e pesos de CNN, scripts e evidências. O pacote não inclui SDKs, ambientes virtuais, dependências npm, credenciais, banco de teste ou o dataset EuroSAT completo. Os guias explicam como instalar dependências e baixar os dados de treino.

O arquivo `ARQUIVOS.json` dentro do ZIP registra tamanho e SHA-256 dos arquivos incluídos. Antes de enviar, abrir o ZIP e confirmar que nomes/RMs e documentos específicos estão preenchidos.
