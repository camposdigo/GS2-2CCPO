# Edge Computing — cruzamento da maquete

Este módulo fornece um simulador determinístico e uma proposta de firmware para **maquete didática**. O algoritmo, os dados e a placa do professor não foram fornecidos. O baseline defeituoso foi criado neste projeto; os resultados não são medições do cruzamento real nem evidência de uma atualização da maquete.

## Executar a simulação

Requer apenas Python 3.10+ e sua biblioteca padrão. A partir desta pasta:

```powershell
python -m unittest -v test_simulate.py
python simulate.py --duration 600 --seed 42 --output results/demo-seed42.json
python simulate.py --duration 60 --input input.example.csv
```

O CSV aceito tem exatamente `second,flow,count`, com `flow` igual a `ns`, `ew` ou `ped`; segundos inteiros no horizonte e contagens não negativas. Linhas repetidas são somadas. O arquivo de exemplo é sintético. Ao receber os dados do professor, adaptar o formato preservando sua proveniência e executar novamente. A mesma sequência de chegadas é usada nas duas políticas.

## Algoritmo e hipóteses

A máquina de estados usa vermelho geral de 2 s, abertura da cancela por 2 s ainda no vermelho, verde entre 8 e 18 s e amarelo de 3 s antes de retornar ao vermelho geral. As cancelas permanecem abertas no amarelo e fecham no vermelho geral. Nunca há permissivos simultâneos para eixos conflitantes; durante travessia, os dois eixos ficam vermelhos e as duas cancelas fechadas.

A fase de pedestres tem 4 s para iniciar entrada e 18 s adicionais para liberar a travessia. Os 18 s são o parâmetro didático `3 + ceil(12 / 0,8)`: 3 s de partida, faixa de 12 m e velocidade de 0,8 m/s. Isso não é um dimensionamento regulamentar e não garante atendimento a toda condição de mobilidade. Quem entra no último segundo permitido ainda recebe o tempo completo de passagem antes de qualquer verde veicular. Não entram novas pessoas na fase de limpeza. Distância, velocidade e condições reais devem ser validadas com o professor.

Uma seleção circular concede fases aos fluxos pendentes; o verde máximo impede que um eixo monopolize o cruzamento. Filas vazias podem encerrar seu verde após o mínimo e liberar outro fluxo. Oportunidades justas de fase não garantem espera limitada para cada pessoa em situações de saturação. Os testes de demanda contínua verificam oportunidades para todos os fluxos em intervalos de até 80 s com os parâmetros padrão.

Hipóteses: passos de 1 s, até um veículo atendido por segundo de verde por eixo e até três pedestres iniciando por segundo de entrada. O simulador não modela aceleração, comprimento de veículos, filas em vias adjacentes, falhas mecânicas, veículos ainda no cruzamento ou percepção humana dos sinais. Intertravamento lógico não substitui detecção física e avaliação do laboratório.

## Análise executada antes/depois

O relatório [results/demo-seed42.json](results/demo-seed42.json) foi gerado executando o comando acima por 600 s com seed 42. Chegadas: 129 NS, 105 EW e 36 pedestres. O legado sintético sobrepõe verdes NS/EW por 2 s em cada ciclo de 50 s e oferece só 5 s de passagem a pedestres; **esse código só existe no simulador e nunca deve ser enviado à placa**.

| Indicador observado | Legado sintético | Controlador corrigido |
| --- | ---: | ---: |
| Segundos com sinais conflitantes | 24 | 0 |
| Segundos de sinal veicular liberado com pedestre ainda atravessando | 150 | 0 |
| Espera média NS entre atendidos (s) | 1,419 | 33,256 |
| Espera média EW entre atendidos (s) | 40,620 | 22,571 |
| Espera média pedestres que iniciaram (s) | 19,611 | 27,629 |
| Veículos EW atendidos | 92 | 105 |
| Fila EW ao final | 13 | 0 |
| Pedestres na fila ao final | 0 | 1 |
| Pedestres em travessia ao final | 1 | 0 |

O ganho observado é a eliminação dos conflitos modelados e uma distribuição mais equilibrada do atendimento veicular. A segurança tem custo: a espera de NS e dos pedestres aumenta neste cenário. Não houve melhora universal de espera. O legado também descumpre os intervalos de segurança, portanto a sua rapidez não constitui uma alternativa aceitável de operação. Comparações futuras de eficiência devem incluir outro baseline que já seja seguro.

A média de espera inclui apenas quem começou atendimento, por isso o JSON mostra também filas finais, pessoas em travessia, maior espera observada e fila média no tempo. Para quem ainda está aguardando, a maior espera observada é uma duração parcial; não é o tempo final de espera. Os testes conferem conservação de pessoas/veículos, conflitos em múltiplas seeds, transições, travessias e fairness. Foram executados **9 testes Python com sucesso** nesta implementação.

## Firmware ESP32

`firmware/territorio_crossing/` contém o sketch Arduino e o núcleo C++ independente. O alvo proposto é **ESP32 DevKit com módulo WROOM-32, sem PSRAM**, usando Arduino-ESP32 **3.x**. O código usa WiFi, WebServer, Update e LEDC do próprio core. A API de PWM emprega `ledcAttach` e `ledcWrite`, conforme a [documentação oficial LEDC da Espressif](https://docs.espressif.com/projects/arduino-esp32/en/latest/api/ledc.html).

| Função | GPIO | Conexão proposta |
| --- | --- | --- |
| NS vermelho/amarelo/verde | 25/26/27 | LEDs com resistores |
| EW vermelho/amarelo/verde | 32/33/14 | LEDs com resistores |
| Pedestre vermelho/verde | 16/17 | LEDs com resistores |
| Cancelas NS/EW | 18/19 | PWM para microservos; fonte externa adequada e GND comum |
| Buzzer ativo / sinalização de espera | 13/21 | Buzzer com driver se necessário / LED com resistor |
| Detectores NS/EW | 34/35 | Nível HIGH enquanto houver demanda; **pulldown externo**, tensão compatível de 3,3 V |
| Botão pedestre / chave física de manutenção | 22/23 | Botão/chave para GND, `INPUT_PULLUP` |

Confirmar a pinagem e a alimentação da placa efetivamente entregue. GPIO 16/17 podem ter outros usos em módulos com PSRAM. Os pulsos 1000/2000 µs e os 2 s de abertura são apenas parâmetros iniciais; calibrar sem carga e verificar os limites do servo. Não alimentar motores diretamente dos GPIOs. O protótipo não tem fim de curso, detector de obstáculo, confirmação de posição ou sensor de ocupação da travessia: ele comanda posições, mas não comprova que a cancela obedeceu. Sinais luminosos e sonoros são didáticos e não possuem certificação viária.

No início e em falha lógica, os sinais ficam vermelhos. O pedido de manutenção preserva o amarelo e o tempo integral de pedestres antes de imobilizar as fases. A lógica usa subtração de inteiros sem sinal para tratar o retorno de `millis()`. O pedido de pedestre permanece registrado até ser oferecida sua janela de entrada. A ausência de Wi-Fi não impede a lógica local.

## Preparar e compilar a placa

Copiar `secrets.example.h` para `secrets.h` **localmente**, preencher Wi-Fi e uma chave aleatória de ao menos 32 caracteres. O `.gitignore` exclui `secrets.h`. O valor de exemplo mantém OTA desabilitado. Não colocar a chave em arquivos de entrega ou capturas.

Instalar o core ESP32 3.x no ambiente Arduino e selecionar uma tabela de partições com duas partições OTA de aplicação e dados OTA. A primeira gravação é por USB. A [documentação Espressif sobre atualização web](https://docs.espressif.com/projects/arduino-esp32/en/latest/ota_web_update.html) explica o fluxo de primeira gravação e envio de um `.bin`; os [requisitos de partições OTA](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/system/ota.html) são documentados no ESP-IDF.

Se `arduino-cli` e o core estiverem disponíveis, a partir desta pasta:

```text
arduino-cli compile --fqbn esp32:esp32:esp32 --build-path firmware/build/esp32 firmware/territorio_crossing
```

Selecionar a placa e o esquema OTA corretos conforme o laboratório; `esp32:esp32:esp32` é o alvo proposto, não a identificação de uma placa conectada. O binário depende da configuração real e pode não caber em uma partição pequena.

## Atualização remota proposta

1. Gravar inicialmente por USB e anotar o IP mostrado na serial.
2. Armar a chave física de manutenção e aguardar a conclusão da fase atual e o vermelho geral. Somente no estado de manutenção o firmware atende HTTP.
3. Consultar `http://IP-DA-MAQUETE/status` e confirmar `MAINTENANCE`.
4. Enviar o `.bin` compilado para o hardware correto por HTTP multipart, com a chave no cabeçalho `X-OTA-Key`.
5. Após resposta de sucesso, conferir reinício, versão e funcionamento mantendo a manutenção armada. Desarmar para retomar as fases depois da inspeção.

Exemplo de formato com placeholders, para executar **somente no laboratório**:

```text
curl --fail --header "X-OTA-Key: SUA-CHAVE-LOCAL" --form "firmware=@firmware.bin" http://IP-DA-MAQUETE/update
```

O envio usa `Update.begin`, `Update.write` e `Update.end`, seguindo a API [Update oficial do core Espressif](https://github.com/espressif/arduino-esp32/blob/master/libraries/Update/src/Update.h). O sketch checa a chave antes de começar a gravação, exige manutenção física, rejeita origem web diferente quando presente, aborta uploads interrompidos e retorna erro sem reiniciar em falha. Não habilita CORS. Um cliente HTTP lento só pode bloquear a execução quando as fases já estão paradas em vermelho.

HTTP transmite a chave sem criptografia. Este mecanismo é restrito à rede isolada do laboratório; não expor à Internet. Não há TLS, assinatura obrigatória, secure boot nem política de rollback verificada. O sucesso de `Update.end` não comprova que a imagem faz o comportamento correto. O teste de partida, recuperação e eventual rollback precisa de um procedimento próprio; a Espressif documenta essas possibilidades no guia de OTA, mas elas não são alegadas implementadas aqui.

## Validação C++ realizada e limites

O núcleo `TrafficController.h` foi compilado com **MSVC 14.51 / C++17**, e `firmware/tests/controller_test.cpp` foi executado com sucesso. Ele cobre intertravamento, oportunidades para todos os fluxos, manutenção sem cortar a travessia, parada travada em falha e retorno de `millis()`. Este é um teste de código nativo, não uma compilação de Arduino nem teste de GPIO/OTA.

Em um terminal de desenvolvimento do Visual Studio, a partir desta pasta:

```text
cl /nologo /std:c++17 /EHsc /W4 /utf-8 /Fe:firmware/build/controller_test.exe /Fo:firmware/build/controller_test.obj firmware/tests/controller_test.cpp
firmware/build/controller_test.exe
```

Criar `firmware/build` antes, se necessário. Alternativa com GCC/Clang:

```text
g++ -std=c++17 -Wall -Wextra -pedantic firmware/tests/controller_test.cpp -o firmware/build/controller_test
firmware/build/controller_test
```

**Arduino CLI/core e hardware não estavam disponíveis para validação nesta execução.** O sketch completo, os tempos físicos, o PWM, Wi-Fi e os retornos HTTP/OTA ainda precisam de compilação e ensaio na placa. Não foi produzido nem enviado um binário ESP32.

Antes de entregar Edge, obter os dados e o algoritmo original do professor, adaptar à sua maquete, registrar diagnóstico original e corrigido, compilar, gravar, testar chave inválida, upload interrompido, reinício e manutenção, e gravar evidências da atualização remota e das travessias. Este módulo prepara o trabalho, mas não substitui essas evidências.
