# POO — motor de alertas territorial em Java

Demonstração independente, sem dependências externas, com **dados sintéticos**. Requer JDK 17 ou superior. Os limiares de 40%/30% são didáticos e não representam política oficial de reservatórios.

No PowerShell, a partir desta pasta:

```powershell
.\run.ps1
.\run.ps1 -Test
```

Se a política local bloquear scripts, usar os comandos Java abaixo ou um terminal autorizado para scripts; não é necessário mudar a política permanente do sistema. `run.ps1` também aceita o JDK apontado por `JAVA_HOME` quando Java não está no PATH.

Alternativa em um terminal com JDK:

```text
javac -encoding UTF-8 -d build src/territorio/*.java
java -cp build territorio.Main
java -cp build territorio.Verificacoes
```

`ComponenteTerritorial` é a classe abstrata dos componentes; `Reservatorio` a especializa. `Sensor` é a interface de leitura; `SensorSimulado` implementa um adaptador determinístico. `EstrategiaPrevisao` fornece a validação compartilhada, e `Persistencia`/`TendenciaLinear` herdam o contrato e implementam previsões diferentes. A lista interna, os limiares e a referência operacional são privados; os consumidores recebem cópias imutáveis das leituras agregadas. O resumo público não mostra a referência restrita.

O método `avaliar` gera automaticamente o objeto de alerta e explica nível atual, projeção, tendência e limiares. A referência para severidade é o menor valor entre o nível atual e o projetado: uma previsão de melhora não apaga um risco já observado. Séries curtas, com lacunas, datas futuras, valores inválidos, dados não confiáveis ou desatualizados são rejeitadas/abstêm a previsão. Não há comando de racionamento nem integração com atuadores.

As verificações exercitam o resultado numérico da regressão, a diferença para o baseline, proteção da coleção, sigilo da referência no resumo, validação dos dados e abstenção. O exemplo projeta a série 52, 50, ..., 40 para 26% em sete dias pela tendência linear; o baseline permanece em 40%. Isso demonstra polimorfismo, **não mede acurácia com dados reais**.

Confiança é qualitativa e explicitamente não calibrada; nenhuma probabilidade foi estimada. A regressão simplificada ignora chuva, demanda e operação. A projeção é limitada ao intervalo físico, sem intervalo de previsão. Dados reais, avaliação temporal e calibração pertencem ao módulo analítico e precisam de execução própria. Encapsulamento Java evita alterações indevidas pelo contrato público, mas não substitui autenticação, autorização de API, criptografia ou uma política de privacidade.

A linguagem específica e os critérios adicionais de POO devem ser conferidos no portal do professor. Esta implementação escolhe Java por tornar visíveis abstração, interface, herança, encapsulamento e polimorfismo.

Validação realizada: compilação com OpenJDK 21.0.8, execução do exemplo e **18 verificações aprovadas**. O exemplo produziu ATENCAO para persistência e CRITICO para tendência linear, sem expor a referência operacional.
