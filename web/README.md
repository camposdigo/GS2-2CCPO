# Território Vivo — web e API

Node.js 22+ (recomendado 24 LTS), Express 5 e Mongoose. Interface em português, responsiva, com fluxo de cadastro/consulta, indicadores do módulo hídrico e envio de imagens ao classificador. Não usa serviços pagos nem publicação.

## Executar com MongoDB

No PowerShell, a partir desta pasta:

```powershell
npm.cmd ci
Copy-Item .env.example .env
# Inicie o MongoDB do compose na raiz ou configure MONGO_URI em .env.
npm.cmd start
```

Abra http://localhost:3000. `npm.cmd run dev` ativa reinício automático. O uso de `npm.cmd` evita o bloqueio de scripts PowerShell. `MONGO_URI` é lida somente pelo backend. O banco deve ficar em rede privada; não exponha sua porta na internet. O processo pode iniciar sem MongoDB, mas `/api/health` e APIs de dados retornam 503. Não há fallback silencioso; após corrigir a configuração, reinicie.

## Demonstração explícita

```powershell
$env:DEMO_MODE = 'true'
npm.cmd start
```

Nesse modo, `data/demo.json` contém quatro exemplos **sintéticos** e registros inseridos durante a demonstração. Os novos registros persistem no arquivo, inclusive após reiniciar. A interface identifica o modo. JSON de demonstração **não comprova integração com MongoDB**. Para retomar MongoDB, remova `DEMO_MODE` do ambiente ou defina-o como `false` em uma nova sessão. A seleção usa a variável efetiva do processo; ambiente existente tem precedência sobre `.env`.

## Contrato da API

| Método / rota | Entrada / resposta |
| --- | --- |
| `GET /api/health` | `{status,storage:{mode,available},classifier:{urlConfigured}}`; 503 se o armazenamento não está pronto. A configuração da URL não confirma a disponibilidade do modelo. |
| `GET /api/dashboard` | `{dataMode,occurrences:{total,open,resolved,byCategory},water}` |
| `GET /api/occurrences` | Filtros opcionais `category`, `region`, `status`, `page` (1+), `limit` (1–100). `{items,total,page,limit,dataMode}` |
| `POST /api/occurrences` | JSON `{category,region,description}`; 201 `{item,dataMode}` |
| `POST /api/classify` | Multipart, um campo `file`, PNG/JPEG, até 5 MB. Encaminha ao FastAPI `${CLASSIFIER_URL}/api/classify`. |

Categorias: `buraco`, `iluminacao`, `residuos`, `acessibilidade`. Regiões agregadas: `Centro`, `Zona Norte`, `Zona Sul`, `Zona Leste`, `Zona Oeste`. Status: `recebida`, `em_analise`, `resolvida`. O cadastro sempre cria status `recebida`; nenhuma rota pública modifica ou remove status. Os estados diferentes na demonstração são parte do conjunto sintético. Item: `{id,protocol,category,region,description,status,createdAt}`. Datas são ISO 8601.

Descrição: 12–600 caracteres. Campos desconhecidos, e-mails e padrões comuns de telefone são rejeitados; isso **não é detecção completa de dados pessoais**. Não inclua nomes, endereço exato ou identificadores nos textos. O protótipo é público e não envia registros para prefeituras.

Erros usam `{error:{code,message,fields?}}`, sem stack, URI de conexão ou conteúdo do arquivo. Exemplos: 400 validação, 413 tamanho, 415 formato, 429 limite, 503 armazenamento/modelo indisponível. Aplicativos móveis podem consumir a API diretamente. O frontend é da mesma origem; não há CORS aberto. O serviço não autentica usuários nem oferece funções administrativas; autenticação, moderação, política de retenção e gestão de direitos são pendências para produção.

Para Flutter web em uma origem local diferente, configure explicitamente `CORS_ORIGINS=http://localhost:5000,http://127.0.0.1:5000`. O padrão vazio permite somente a mesma origem (e clientes sem cabeçalho `Origin`, como apps nativos). A lista compara origens HTTP(S) exatas; preflight aceita somente GET/POST e Content-Type. Não há wildcard nem credenciais. Origens, métodos ou cabeçalhos cruzados fora da configuração recebem 403.

## Integrações

- Água: lê `../modules/water/artifacts/dashboard.json`. Valida o contrato e recalcula a atualidade com a data de São Paulo; mantém fonte, métricas, série, alertas e limites do estudo. Artefato ausente/inválido aparece como indisponível. Valor observado, previsão e intervalo nominal são apresentados separadamente.
- Imagens: `CLASSIFIER_URL`, padrão `http://127.0.0.1:8001`. Upload fica na memória; não é salvo pelo web. Há limite de 5 MB, verificação de assinatura e timeout de 15 segundos. O FastAPI precisa decodificar/validar integralmente a imagem. Sem serviço/modelo treinado, retorna 503 e não cria classe fictícia. `score` softmax não é probabilidade calibrada.
- Segurança básica: Helmet/CSP, limites de requisição, JSON 12 KB, validação estrita de filtros e payload, seleção explícita dos campos persistidos, renderização de texto com `textContent`, Mongo com buffering desabilitado e sem exposição de erros internos. Configure HTTPS, proxy confiável e controles de acesso antes de produção; o servidor local escuta em todas as interfaces para integração com emulador.

## Verificação

```powershell
npm.cmd test
```

Os testes usam `node:test` e Supertest: cadastro/consulta e reabertura de persistência demo, concorrência, filtros, contatos, alteração de status proibida, JSON/limites, CSP/XSS, falha real de conexão Mongo local, artefato hídrico/obsolescência e upload/proxy sem classificação inventada. Não acessam Mongo remoto, a API SABESP ou o modelo. A gravação real MongoDB deve ser validada com o banco iniciado; os testes locais não alegam verificar uma instância inexistente.

Teste opcional com MongoDB real e portátil, sem instalar serviço global (Windows; Python 3 necessário somente para o download):

```powershell
python scripts/fetch-mongodb-qa.py
npm.cmd run test:mongo
```

O download usa HTTPS do domínio oficial e intervalos do ZIP para obter somente `mongod.exe`, validando o CRC do membro. O executável do ZIP oficial pode não ter assinatura Authenticode. O teste inicia o MongoDB restrito a `127.0.0.1`, cadastra via HTTP, reinicia **a API e o banco**, consulta o mesmo documento e confirma sua existência diretamente na coleção. Remove o banco de teste e encerra os processos que criou. O resumo fica em `evidence/mongo-smoke.json`. O binário e os dados locais são ignorados no Git. Em outro sistema, configure `MONGOD_EXECUTABLE` com o caminho do binário compatível.

Com a web já iniciada e Chrome local disponível, `npm.cmd run test:browser` verifica desktop/mobile, ausência de rolagem horizontal, carregamento dos indicadores, abertura do formulário e navegação; grava screenshots e `evidence/browser-qa.json`. Configure `CHROME_EXECUTABLE` se necessário. Não instala navegador e não altera os registros.

Dependências exatas e lockfile versionados. Versões verificadas no registro npm na implementação; documentação de referência: [Express](https://expressjs.com/), [Mongoose](https://mongoosejs.com/), [Multer](https://github.com/expressjs/multer), [Zod](https://zod.dev/), [Helmet](https://helmetjs.github.io/), [express-rate-limit](https://express-rate-limit.mintlify.app/).
