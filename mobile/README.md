# Território Vivo — Flutter

App com painel hídrico, gráfico com descrição textual, alertas explicados, consulta/cadastro de ocorrências e preferências locais. A API é a mesma do portal Node.js; dados reais e demonstração têm identificação separada. Não há geolocalização nem cadastro de cidadãos.

## Executar

Use Flutter estável (validado com Flutter 3.47.9 / Dart 3.13.7). Neste computador, o SDK isolado está em `../.tools/flutter/bin/flutter.bat`, a partir desta pasta. Em outro computador, siga a [instalação oficial](https://docs.flutter.dev/install).

```powershell
cd mobile
flutter pub get

# Navegador: a porta 5000 deve constar da allowlist do backend.
flutter run -d chrome --web-port 5000 --dart-define=API_BASE_URL=http://localhost:3000

# Emulador Android: 10.0.2.2 alcança o host.
flutter run -d <id-do-emulador> --dart-define=API_BASE_URL=http://10.0.2.2:3000

# Aparelho Android: trocar pelo IP LAN do computador, ambos na mesma rede.
flutter run -d <id-do-aparelho> --dart-define=API_BASE_URL=http://192.168.0.10:3000
```

Inicie a API antes. Para Flutter Web em outra origem, configure o backend:

```powershell
# Na raiz, antes de scripts/iniciar.ps1:
$env:CORS_ORIGINS = 'http://localhost:5000,http://127.0.0.1:5000'
powershell -ExecutionPolicy Bypass -File scripts/iniciar.ps1 -Demo
```

O CORS aceita somente as origens listadas, sem wildcard ou cookies. Navegador e API no mesmo host e em portas diferentes continuam sendo origens diferentes. A allowlist precisa corresponder exatamente à URL aberta.

O Android debug permite HTTP local. **Profile/release usam HTTPS**, sem liberar tráfego claro: configure `API_BASE_URL=https://seu-servidor` para essas variantes. Não use localhost para alcançar o computador a partir de um aparelho/emulador. A permissão INTERNET está no manifesto principal.

## Estado e persistência

- `TerritoryState` é um `ChangeNotifier` observado pela interface.
- `TerritoryApi` recebe `http.Client`, valida respostas e interpreta o envelope real de erro da API.
- `SharedPreferencesAsync` armazena região favorita e último painel agregado. O cache não armazena descrições das ocorrências.
- Falha de rede mostra offline/cache com datas. Alertas e projeções vencidos recebem aviso; nenhum resultado aciona restrição de água.
- Ao trocar o filtro, respostas de requisições antigas são descartadas. Limpar cache invalida uma escrita de atualização pendente.
- Formulário valida categoria, região e descrição; a API reaplica os mesmos limites e recusa possíveis contatos pessoais.

Regiões: Centro, Zona Norte, Zona Sul, Zona Leste e Zona Oeste de São Paulo. São regiões agregadas para o protótipo CitizenTech; não se deve interpretar a preferência como medição hídrica por região. Os dados do Cantareira não são desagregados por bairro.

## Testes e compilação

```powershell
flutter analyze
flutter test
flutter build web --dart-define=API_BASE_URL=http://localhost:3000

# Servir o build, com a API/CORS já configurados:
python -m http.server 5000 --bind 127.0.0.1 --directory build/web
```

Os testes cobrem API/erros UTF-8, persistência, offline, corrida entre filtros, limpeza de cache, formulário inválido, falha de servidor e layout de 320 px com escala de texto 2×. A compilação web não comprova instalação num aparelho Android. O projeto Android está incluído, mas o teste físico e a geração de APK dependem do Android SDK/dispositivo e constam como pendências quando não executados.

## Acessibilidade e limites

Material 3, rótulos, ações com tooltip, texto ampliável, rolagem e descrição textual do gráfico. Alertas usam texto além de cor. O teste de layout não substitui avaliação com leitor de tela e usuários. A listagem móvel consulta até 50 ocorrências por vez; a API e o portal oferecem paginação completa.

Fontes: [HTTP no Flutter](https://docs.flutter.dev/cookbook/networking/fetch-data), [pacote http](https://pub.dev/packages/http), [shared_preferences](https://pub.dev/packages/shared_preferences) e [política Android de segurança de rede](https://developer.android.com/privacy-and-security/security-config#CleartextTrafficPermitted). Preferências são armazenamento de conveniência, não um cofre para dados críticos.
