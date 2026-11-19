# Operating Systems and Computer Networks — estudo didático

Este documento resolve um **cenário criado para demonstração**. O PDF geral não contém a relação real de usuários, ACLs, tamanhos de disco ou questões do professor. Nenhuma conta, compartilhamento ou disco desta máquina foi alterado. Substitua este cenário pelo enunciado específico do portal antes da entrega da disciplina.

## 1. Inventário e política de acesso

O centro fictício Território Vivo possui um servidor Windows `SRV-TERRITORIO`, o compartilhamento `\\SRV-TERRITORIO\Centro$` e três pastas: `Atendimento`, `Analise` e `Coordenacao`. O sufixo `$` apenas oculta a listagem normal do compartilhamento; não concede segurança. Identidades, setores e arquivos abaixo são fictícios.

| Conta | Função | Grupo autorizado | Regra de negócio |
| --- | --- | --- | --- |
| Ana | Atendimento | `GG_Atendimento` | Modificar Atendimento; sem acesso a Analise e Coordenacao |
| Bruno | Análise hídrica | `GG_Analise` | Modificar Analise; sem acesso a Coordenacao |
| Carla | Coordenação | `GG_Coordenacao` | Ler Atendimento/Analise; modificar Coordenacao |
| Diana | Auditoria | `GG_Auditoria` | Ler relatórios agregados de Analise; sem escrita |

Contas entram em grupos de função (`GG_*`), que entram em grupos de recurso (`DL_*`). As ACLs referenciam os grupos de recurso. Exemplo: `Bruno → GG_Analise → DL_Analise_M`. A gestão de grupos evita permissões individuais difíceis de revisar. Administradores autorizados e `SYSTEM` mantêm controle total, com contas administrativas separadas das de uso diário.

| Pasta | NTFS pretendido para dados | SMB do compartilhamento |
| --- | --- | --- |
| Atendimento | `DL_Atendimento_M`: Modify; `DL_Coordenacao_R`: Read | grupos que escrevem: Change; grupos que só leem: Read |
| Analise | `DL_Analise_M`: Modify; `DL_Coordenacao_R` e `DL_Auditoria_R`: Read | mesma regra |
| Coordenacao | `DL_Coordenacao_M`: Modify | mesma regra |

`Modify` permite excluir conteúdo: não deve ser confundido com apenas gravar. O NTFS da raiz concede aos grupos apenas a travessia/listagem necessária, com escopo “somente esta pasta”; não propaga escrita para todos os setores. Na prática, validar também direitos de travessia, privilégios da conta e o escopo `this folder / subfolders / files`. A enumeração baseada em acesso pode melhorar a experiência de listagem, mas não substitui ACLs.

## 2. Incidentes e correções propostas

| Incidente fictício | Diagnóstico | Correção no laboratório | Resultado esperado via SMB |
| --- | --- | --- | --- |
| Ana altera arquivos de Analise | Ana pertence indevidamente a `GG_Analise`; o acesso é permitido em ambas as camadas | Retirar associação incorreta e manter `GG_Atendimento` | Ana não lê nem grava Analise; trabalha em Atendimento |
| Bruno lê, mas não salva | NTFS permite Modify, mas SMB concede apenas Read | Atribuir Change no SMB ao grupo de escrita; conferir NTFS | Bruno lê e grava Analise sem alterar ACLs |
| Carla perde acesso a Coordenacao | Existe Deny Read explícito para Carla, além do Allow do grupo | Remover a negação obsoleta após conferir a política; não ampliar `Everyone` | Carla modifica Coordenacao pelo grupo correto |
| Diana consegue editar relatórios | `Authenticated Users: Modify` foi herdado da raiz | Corrigir a ACE na origem; se a pasta precisa de isolamento, proteger a herança e revisar cada ACE convertida | Diana apenas lê; escritores continuam funcionando |

Após mudar grupos, renovar a sessão/autenticação para que o token reflita a associação nova; não concluir falha apenas por uma sessão antiga. Rever grupos aninhados e permissões diretas. Remover uma associação isolada não basta se outro grupo continuar concedendo o mesmo direito.

## 3. SMB, NTFS, herança e negação

No acesso remoto, uma operação precisa ser autorizada **tanto no compartilhamento quanto no NTFS**. Assim, NTFS Modify com SMB Read resulta em leitura via SMB; SMB Change com NTFS Read também. Acesso local ao caminho físico não passa pela ACL do compartilhamento. As duas camadas devem ser configuradas segundo a política de recurso. A [orientação Microsoft para compartilhamento e NTFS](https://learn.microsoft.com/en-us/iis/web-hosting/configuring-servers-in-the-windows-web-platform/configuring-share-and-ntfs-permissions) documenta a configuração separada dessas camadas.

Permissões Allow de grupos aplicáveis podem somar direitos em uma mesma camada. A verificação considera os SIDs do token, os direitos solicitados e a sequência das ACEs; uma negação de escrita não necessariamente nega leitura. A [explicação oficial de AccessCheck](https://learn.microsoft.com/en-us/windows/win32/secauthz/how-dacls-control-access-to-an-object) descreve a autorização ou negação dos direitos restantes e a negação implícita quando faltam concessões.

A ordem canônica é: ACEs explícitas antes das herdadas; dentro das explícitas, Deny antes de Allow; as herdadas seguem do ancestral mais próximo ao mais distante, com Deny antes de Allow em cada nível. Portanto, a frase “Deny sempre vence” é imprecisa: um Allow explícito pode conceder um direito antes de um Deny herdado. Esta é a [ordem oficial das ACEs](https://learn.microsoft.com/en-us/windows/win32/secauthz/order-of-aces-in-a-dacl).

Exemplo controlado: a pasta pai nega Write a `GG_Auditoria` de forma herdável; na subpasta, Diana recebe Allow Write **explícito**. Em uma DACL canônica simples, o Allow explícito vem antes do Deny herdado e pode permitir Write. Isso não é uma boa solução de manutenção: remover a negação inadequada na origem e conceder acesso pelo grupo certo produz uma política mais clara. Já um Deny Write explícito para Diana, antes de um Allow Write explícito do grupo, bloqueia a escrita. Sempre inspecionar a ACL real, inclusive entradas de objeto e escopos de propagação.

Desabilitar herança não apaga automaticamente permissões copiadas: ao converter herdadas em explícitas, elas permanecem. Se escolher remover herdadas, restaurar previamente os acessos administrativos e necessários para não bloquear o recurso. Preferir corrigir a origem quando a regra vale para a árvore inteira. A Microsoft descreve a [propagação e a precedência de entradas diretamente aplicadas](https://learn.microsoft.com/en-us/windows/win32/secauthz/automatic-propagation-of-inheritable-aces).

## 4. Verificação no laboratório Windows

Registrar o estado inicial com `Get-SmbShareAccess -Name 'Centro$'`, `Get-Acl -LiteralPath 'D:\Centro\Analise' | Format-List` e `whoami /groups` na sessão do usuário de teste. Esses caminhos e nomes são exemplos; não executar alterações no computador pessoal. Se houver domínio, conferir associações com as ferramentas de administração autorizadas pelo professor.

Depois das correções, testar com cada conta comum por `\\SRV-TERRITORIO\Centro$`, sem reutilizar credenciais administrativas. Registrar: listar, abrir, criar, editar, excluir e tentar acessar outro setor. Testar também uma conta sem grupo autorizado. Esperado: Bruno grava Analise e não acessa Coordenacao; Ana só opera Atendimento; Diana abre relatórios e não cria nem exclui; Carla mantém os acessos da matriz. O teste local de Bruno e o remoto devem evidenciar a diferença entre as camadas. Usar a aba “Acesso efetivo” para apoiar o diagnóstico NTFS e conferir separadamente o SMB. Guardar capturas e saída dos comandos no ambiente do professor; este documento não contém evidência de execução desses testes.

## 5. RAID e capacidade útil

Inventário didático: **quatro discos de 2 TB decimais**, sem reserva de sistema de arquivos ou metadados. Considerar capacidade do menor disco em arrays com discos diferentes. Os resultados são cálculos nominais, não medições.

| Arranjo | Discos utilizados | Cálculo | Capacidade nominal | Tolerância |
| --- | --- | --- | --- | --- |
| RAID 0 | 4 | `4 × 2` | 8 TB | Nenhuma; a falha de qualquer membro compromete o volume |
| RAID 1 tradicional | 2, os outros 2 ficam fora do volume | `1 × 2` | 2 TB | Falha de 1 dos 2 membros do espelho |
| RAID 5 | 4 | `(4 − 1) × 2` | 6 TB | Falha de 1 membro; uma segunda antes da reconstrução excede a proteção |

RAID 0 distribui dados sem redundância. RAID 1 replica os dados do espelho. RAID 5 usa paridade distribuída e requer pelo menos três discos. A descrição dos níveis e suas propriedades está no [guia técnico oficial Dell PERC](https://i.dell.com/sites/csdocuments/Shared-Content_data-Sheets_Documents/en/perc-technical-guidebook.pdf).

A comparação explicita que o RAID 1 tradicional usa apenas dois discos. Se os quatro forem organizados em **dois espelhos independentes**, a soma será 4 TB em dois volumes; tolera uma falha em cada par, mas não duas no mesmo par. Isso não é um único RAID 1 de 4 TB. Espelhos com mais de dois membros dependem do controlador e não são presumidos aqui. Discos de reserva não aumentam a capacidade útil. A reconstrução consome recursos e deixa o array vulnerável a falhas adicionais; redundância não garante ausência de interrupções.

Para um pequeno centro que prioriza simplicidade, propor RAID 1 de dois discos e reposição preparada. RAID 5 atende melhor à capacidade deste exemplo, mas exige avaliar carga, tempo de reconstrução, controlador e risco. A escolha final depende das necessidades e equipamentos reais.

## 6. RAID não substitui backup

Exclusão acidental, ransomware, corrupção lógica, roubo e desastre podem atingir simultaneamente todas as cópias de um array. RAID ajuda na continuidade diante das falhas de disco previstas pelo nível; backup preserva cópias recuperáveis de outros momentos. A [documentação oficial Dell distingue RAID de backup](https://www.dell.com/support/kbdoc/en-us/000148741/how-to-create-a-raid-with-intel-perc-and-lsi-controllers).

Plano proposto: cópia diária, cópia externa separada e uma cópia isolada/imutável; criptografia, acesso restrito, retenção definida e testes periódicos de restauração. Objetivos iniciais **a validar**: RPO de 24 h e RTO de 4 h. Somente ensaios de restauração e medição do ambiente podem comprovar esses objetivos. Recuperar periodicamente um arquivo e um conjunto completo em ambiente isolado, verificando integridade e registrando duração.

## Pendências para a entrega definitiva

Obter a matriz de usuários e os casos de permissão do professor, confirmar quantidade/capacidade dos discos e restrições do controlador, executar no laboratório autorizado e anexar evidências antes/depois. Este estudo não afirma ter corrigido a infraestrutura real nem realizado uma reconstrução RAID.
