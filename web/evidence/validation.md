# Evidências de verificação

Executado no Windows, Node.js 24.22.1, em 09/11/2026 (São Paulo).

- `npm.cmd test`: 13 testes aprovados, zero falhas; inclui persistência demo após reabrir arquivo, concorrência, validação estrita, privacidade básica, status público imutável, limites, CSP/XSS, falha Mongo real e sem fallback, artefato hídrico obsoleto, expiração de previsão, proxy sem classificação inventada e CORS com origem/preflight autorizado e negado.
- Instalação com versões exatas e `package-lock.json`; auditoria npm: zero vulnerabilidades reportadas no momento da instalação.
- `npm.cmd run test:mongo`: MongoDB Community **8.2.12 real**, sem serviço global, restrito a `127.0.0.1`. Registro criado por HTTP201; API e banco reiniciados; mesma ID recuperada; confirmação direta na coleção. Banco de QA removido. Resumo em `mongo-smoke.json`.
- `npm.cmd run test:browser`: Chrome já instalado, headless/CDP. Viewports desktop1440 e mobile390. Sem rolagem horizontal da página, sem exceções JS; indicadores carregados, gráfico SVG presente, formulário aberto e navegação/consulta verificados. Resumo em `browser-qa.json`.
- `painel-desktop.png` e `painel-mobile.png`: capturas reais do app, inspecionadas. O modo de ocorrências está explicitamente identificado como demonstração JSON; o indicador de água vem do artefato oficial SABESP, fonte independente.

O teste de browser não envia ocorrência para não alterar a demonstração. Cadastro e persistência estão cobertos tanto por testes HTTP quanto pelo teste com MongoDB real. O classificador foi verificado com resposta simulada no teste de contrato; o treino e a integração final com o serviço CNN são de responsabilidade do módulo de visão computacional. Nenhuma classificação é gerada pelo web quando o serviço não está disponível.

Binário Mongo local, banco de QA, perfil temporário Chrome e `node_modules` não devem entrar no pacote de entrega. O download do binário usa o domínio oficial `fastdl.mongodb.org`, HTTPS e CRC do membro ZIP; o executável distribuído no ZIP não apresentou assinatura Authenticode. Não foi instalado serviço do Windows nem modificado navegador/perfil pessoal.
