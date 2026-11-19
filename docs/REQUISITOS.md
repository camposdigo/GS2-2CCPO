# Global Solution 2026.2 — matriz de requisitos

Fonte: `GS2026.2 - FEV.pdf`, apresentação do 2º ano de Ciência da Computação. Os requisitos abaixo vêm do PDF; decisões de implementação estão identificadas como escolhas do projeto. Os enunciados complementares do portal precisam ser conferidos antes da entrega.

## Proposta: Território Vivo

Plataforma de inteligência territorial que combina ocorrências de infraestrutura, observação de recursos hídricos da RMSP e classificação experimental de paisagens. Os alertas apresentam evidências, qualidade dos dados e limitações. Medidas de alto impacto exigem avaliação humana. Os laboratórios de redes e de cruzamento inteligente complementam a solução.

| Disciplina | Exigência do PDF | Implementação prevista | Evidência necessária |
|---|---|---|---|
| Operating Systems and Computer Networks | Grupos de usuários; permissões SMB/NTFS; herança e negações; RAID 0/1/5; backup | Relatório técnico e cenário didático de permissões e capacidade | Resolver também o cenário específico entregue pelo professor |
| Software Engineering | Plataforma de análise territorial para apoiar planejamento | Requisitos, histórias, critérios de aceite, arquitetura, riscos e rastreabilidade | Confirmar os documentos e formato cobrados pelo professor |
| Data Science and Analytics | Recursos hídricos da RMSP; dados reais históricos e atuais; ML; risco de escassez; revisão humana | Pipeline de dados oficiais, tratamento, previsão temporal e painel | Série coletada, fonte, datas, métricas observadas e comparação com baseline |
| Application Development | Cadastro/consulta de ocorrências; Node.js, Express e MongoDB; formulário, rotas e validação | Portal CitizenTech e API compartilhada | Executar com MongoDB; modo de demonstração não substitui essa validação |
| Object-Oriented Programming | Classes abstratas, interface de sensores, leitura/previsão, encapsulamento e herança de estratégias | Módulo Java com sensores e alertas explicados | Compilação, execução, testes e explicação dos conceitos; linguagem é escolha do projeto |
| Cross-Platform Application Development | Flutter, navegação, estado, API, persistência, formulários, gráficos, alertas explicados/confiança/limitações, acessibilidade e privacidade | Aplicativo com painel, alertas, ocorrências e preferências | Análise estática, testes e execução em plataforma suportada |
| Edge Computing | Corrigir controle do cruzamento da maquete, analisar fluxos e atualizar firmware remotamente | Simulação e firmware de referência com intertravamento e atualização remota | Adaptar aos dados, pinos e firmware fornecidos; demonstrar na maquete |
| CNN | CNN própria para paisagens de satélite; comparar camadas/filtros/hiperparâmetros; integração web | Treinamento EuroSAT RGB, experimentos, métricas e API de inferência | Treinamento efetivo, conjuntos separados, matriz de confusão e teste via portal |

## Requisitos transversais

- Informar procedência, data de observação e atualização dos dados; não apresentar simulação como medição real.
- Separar treino, validação e teste; nas séries temporais, respeitar a ordem temporal e o horizonte de previsão.
- Exibir métricas, limitações, vieses e condições em que previsões devem ser suspensas.
- Não automatizar racionamento, distribuição de serviços ou outras medidas de alto impacto.
- Minimizar dados pessoais: ocorrências usam região/bairro, sem cadastro de cidadãos, coordenadas residenciais, nomes ou contatos.
- Relacionar métricas técnicas a indicadores sociais mensuráveis, sem alegar benefícios ainda não observados.
- Disponibilizar instruções de execução e evidências verificáveis.

## Agenda informada pelo PDF

- Desenvolvimento: **4 a 19 de novembro de 2026**.
- Prazo máximo das avaliações: **19 de novembro de 2026**, no portal, para cada professor.
- Resultado/vista: **23 a 27 de novembro de 2026**.
- Trabalho individual, em dupla ou em trio.
- Para concorrer ao prêmio: vídeo pitch de até **3 minutos**, enviado ao Scrum Master junto com a GS.

O PDF não informa horário limite, rubricas completas, linguagem da disciplina de POO, modelos específicos de ML, dataset obrigatório de CNN nem configuração da maquete. Esses itens não devem ser inventados.
