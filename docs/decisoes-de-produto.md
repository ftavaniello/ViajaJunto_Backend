# Decisões de produto e regras adotadas

Este documento consolida o comportamento já implementado no backend. Não cria
funcionalidades nem comprova aprovação do professor. Os requisitos recebidos são
preservados em [requirements-ViajaJunto.md](requirements-ViajaJunto.md); divergências
estão identificadas abaixo. Alterações futuras devem alinhar código, testes e guias.

## D1 — Identificadores e convites

As chaves de usuários, viagens e recursos relacionados são inteiros. O ID da viagem
identifica o recurso e não concede acesso. O convite atual é individual por email,
com token aleatório, hash no banco, validade de sete dias e uso único. O aceite
exige autenticação com o email destinatário e cria um vínculo de Visualizador.
Somente o criador convida ou muda papéis. Reenviar substitui o link pendente.

**Adaptação:** RF18 originalmente descreve um código compartilhado da viagem.
O fluxo por email está em [convites e membros](convites-e-membros.md).

## D2 — Avaliações e ranking

Avalia-se a atividade pública do catálogo, não o destino diretamente. Cada usuário
mantém uma avaliação por atividade; novo envio atualiza a anterior. Notas são
inteiros de 1 a 5 e o comentário é opcional. Média e quantidade são calculadas das
avaliações persistidas, incluindo as de autores excluídos.

O ranking dos destinos agrega reviews de suas atividades e aplica média bayesiana,
com desempate por quantidade e ID. Assim, a RN05, que menciona destino, é interpretada
em conjunto com RF22 e o modelo original, que definem avaliação de atividade.
Guias: [avaliações](avaliacoes-atividades.md) e [ranking](ranking-destinos.md).

## D3 — Realização de atividade

Para publicar uma avaliação, o usuário precisa participar atualmente da viagem e
a ocorrência precisa estar `concluida`, com `realizada_em` preenchido. O responsável
pela marcação é `realizada_por_id`; ele não é o único participante autorizado a avaliar.
Visualizador pode publicar sua avaliação, mas não modificar o planejamento.

A conclusão é coletiva e declarada no sistema, sem comprovação individual externa.
Não há bloqueio por data futura. Esse é o critério complementar adotado para RF22.
Reabrir a ocorrência limpa sua comprovação atual e bloqueia novos envios até nova
conclusão; reviews já publicados são preservados.

## D4 — Permissões por viagem

| Operação | Criador | Editor | Visualizador |
| --- | --- | --- | --- |
| Consultar planejamento e mapa | Sim | Sim | Sim |
| Alterar nome, descrição, datas e status gerais | Sim | Sim | Não |
| Adicionar, editar, excluir e reordenar destinos/atividades | Sim | Sim | Não |
| Definir ou alterar orçamento | Sim | Sim | Não |
| Excluir viagem | Sim | Não | Não |
| Convidar, alterar papéis e remover membros | Sim | Não | Não |
| Avaliar atividade concluída conforme D3 | Sim | Sim | Sim |

O criador é identificado em `viagens.criador_id`, sem duplicação em membros.
Usuário externo ou removido recebe `404`; participante sem a permissão recebe `403`.
O vínculo atual é consultado a cada operação, inclusive para JWTs emitidos antes
da alteração de papel. Recursos filhos precisam pertencer à viagem/parada da URL.

RF19 detalha edição de destinos, atividades e orçamento. A edição dos dados gerais
pelo Editor é uma interpretação complementar já adotada, registrada nesta matriz.

## D5 — País visitado

Conta a parada de uma viagem própria/compartilhada, confirmada ou concluída, cuja
chegada é até hoje em UTC. Países são agrupados pelo código ISO alfa-2, sem duplicar
viagens. A remoção do vínculo retira esse acesso/histórico derivado. Não é verificação
de presença geográfica. Veja [mapa e países visitados](mapa-paises-visitados.md).

## D6 — Datas, horários e status

Datas de viagem/estadia são datas de calendário, sem conversão de fuso. Atividades
usam data e horário local separados; sem horário ficam ao fim do respectivo dia.
Timestamps operacionais, como criação, conclusão e validade de tokens, usam UTC.
A coluna opcional `fuso_horario` do catálogo armazena um nome IANA; não transforma
os horários do roteiro automaticamente.

Viagem: `planejando`, `confirmada`, `concluida`. Atividade: `pendente`, `confirmada`,
`concluida`. `cancelada` permanece somente como estado legado de leitura.
As estadias respeitam o período da viagem e as atividades, o período da parada.

## D7 — Dinheiro e orçamento

Cada viagem usa uma moeda; a implementação atual utiliza BRL, inclusive no seed
internacional. Custos são decimais exatos com duas casas. O planejado soma custos
das ocorrências, exceto as canceladas legadas. Saldo = limite − planejado.
O percentual consumido por tipo usa o limite como denominador; a participação no
planejado usa a soma de custos. Denominador ausente/zero produz percentual nulo.
Os percentuais são arredondados em duas casas, meio para cima.

Não há DELETE do limite nem retirada por null; definir zero não equivale a limite
indefinido. Se a equipe exigir “remover orçamento” nesse sentido, falta decidir o
contrato correspondente. Veja [orçamento](orcamento-viagem.md).

## D8 — Catálogo, tipos e fotos

Os dados públicos de cidades/locais ficam no catálogo. Datas, estadias, custos e
status particulares ficam no roteiro; editá-los não altera o catálogo público.
Os tipos atuais são `passeio`, `refeicao`, `hospedagem`, `transporte` e `outro`,
alinhados ao documento original. [Tipos e migração](catalogo-atividades.md#tipos-de-atividades).

Cada registro suporta uma URL HTTP/HTTPS de foto. Não há upload/armazenamento de
arquivos, e as imagens do seed estão pendentes. O abastecimento é operacional por
JSON/seed ou Geoapify. O fornecedor substitui o Google Places previsto inicialmente;
a atualização externa preserva IDs, avaliações e curadoria. Ver [integração](integracao-locais.md).

## D9 — Email e notificacoes

Recuperação de senha usa token de uso único com validade de 60 minutos, apenas hash
persistido e invalidação dos pendentes. A redefinição encerra todas as sessões.
O Compose envia para Mailpit; SMTP externo precisa ser configurado. O modo console
apenas imprime mensagens para testes locais. [Recuperação](recuperacao-de-senha.md).

Notificações são persistidas na mesma transação da mudança e consultadas por polling.
O autor da mudança não recebe seu próprio aviso. Os eventos atuais são:

- Entrada de membro: demais participantes.
- Alteração de papel/remoção: membro afetado, exceto quando é o autor da ação.
- Exclusão de viagem: demais participantes; o histórico permanece com viagem nula.
- Mudança de nome/datas/status gerais, inclusão/remoção de destinos e alteração das
  datas de estadia: demais participantes.
- Inclusão/remoção de atividade e mudança de data, horário ou status: demais participantes.

O escopo atual não avisa por reordenação, limite/custo de orçamento, duração,
descrição ou hospedagem. Isso registra a seleção implementada de “relevante” no RF21;
qualquer ampliação precisa ser acordada e implementada. Cada usuário lista, conta
e marca como lidas somente suas próprias notificações.

## D10 — Exclusões e sessões

Excluir explicitamente uma viagem remove membros, orçamento, convites e roteiro.
Catálogo e reviews sobrevivem; a referência da review à ocorrência excluída fica nula.
Ao excluir a conta, se o usuário criou qualquer viagem com colaboradores, retorna
`409` e preserva tudo. Nos demais casos, remove conta, viagens próprias individuais,
participações e tokens; reviews ficam com autor nulo. Não há transferência automática.
[Política de exclusão](exclusao-conta.md).

A autenticação consulta a existência da conta, a versão de sessão e a revogação do
JWT. Logout revoga somente o token usado; troca/redefinição de senha invalida todas
as sessões. Cadastro/exclusão invalidam o cache da contagem após o commit.
[Política de sessões](sessoes-e-logout.md).

## Validações restantes da entrega

Consolidar com a equipe/professor as adaptações de convite, fornecedor, realização
coletiva, critério de visita e permissões complementares; validar frontend, fotos,
SMTP, CORS/proxy, tempo completo das páginas e exigência de hospedagem pública.
A [auditoria histórica](historico/auditoria-final-requisitos.md) registra a revisão
original; o [guia de validação](validacao-e-desempenho.md) contém método e evidências.
