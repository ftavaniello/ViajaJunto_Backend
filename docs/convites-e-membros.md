# Convites por email, membros e papéis por viagem — issue #16

Implementa RF18–RF20 e RN02–RN04/RN06. O criador convida alguém pelo email; a
pessoa recebe um link e, ao aceitá-lo com a conta daquele email, entra direto na
viagem como **Visualizador**. Só o criador promove, rebaixa ou remove
colaboradores. O criador não é membro: ele é `viagens.criador_id` e não tem linha
em `membros_viagem`.

> **Mudança em relação ao requisito original:** o RF18 previa convite "pelo código
> da viagem". A equipe optou por convites individuais por email: um código único
> por viagem dava acesso a qualquer pessoa que o recebesse repassado. A migração
> `d8a2f5c3e174` removeu `viagens.codigo_convite` e criou `convites_viagem`.

## Fluxo

1. O criador chama `POST /viagens/{viagem_id}/convites` com `{"email": "ana@example.com"}`.
2. O backend sorteia um token, guarda só o hash SHA-256 dele e envia ao email
   o link `CONVITE_URL?token=<token>`.
3. Ana abre o link no frontend. Se não tiver conta, cadastra-se **com o mesmo email**;
   depois faz login.
4. O frontend chama `POST /viagens/convites/aceitar` com `{"token": "<token>"}`.
5. Ana entra na viagem do convite como `visualizador`. A viagem passa a aparecer
   em `GET /viagens`.

Em nenhum momento o convidado informa o id da viagem: ela é descoberta pelo token.

## Operações e permissões

Todas exigem `Authorization: Bearer <token>` e identificam o usuário pelo token.

| Método e rota | Operação | Quem pode |
|---|---|---|
| `POST /viagens/{viagem_id}/convites` | Envia convite por email | Criador |
| `GET /viagens/{viagem_id}/convites` | Lista convites pendentes | Criador |
| `DELETE /viagens/{viagem_id}/convites/{convite_id}` | Cancela convite pendente | Criador |
| `POST /viagens/convites/aceitar` | Aceita o convite do link | Dono do email convidado |
| `GET /viagens/{viagem_id}/membros` | Lista criador e colaboradores | Criador, Editor e Visualizador |
| `PATCH /viagens/{viagem_id}/membros/{usuario_id}` | Altera papel (`editor` ou `visualizador`) | Criador |
| `DELETE /viagens/{viagem_id}/membros/{usuario_id}` | Remove colaborador | Criador |

## Regras

- **Qualquer email pode ser convidado**, com ou sem conta. O email é guardado em
  minúsculas e comparado sem diferenciar maiúsculas.
- **Convite ligado ao email.** Só a conta com o email convidado aceita; outra conta
  que receba o link repassado recebe 403 e o convite continua valendo para o dono.
- **Papel inicial fixo.** Todo convidado entra como `visualizador`
  (`PAPEL_INICIAL_CONVIDADO`). O corpo do aceite só aceita `token`; enviar `papel`
  ou `viagem_id` retorna 422.
- **Uso único, sem aceite repetido.** Um link já usado retorna 409, inclusive depois
  de o membro ser removido: para voltar, ele precisa de um convite novo. Quem já
  participa da viagem também recebe 409 (o papel atual não muda). Duas aceitações
  simultâneas são barradas pela constraint `uq_membros_viagem_viagem_usuario`.
- **Validade de 7 dias** (`CONVITE_VALIDADE_DIAS`). Token inexistente e expirado
  recebem a mesma resposta: 404 `"Convite inválido ou expirado"`.
- **Reenvio.** Convidar de novo o mesmo email invalida o link anterior; há no máximo
  um convite pendente por email em cada viagem (índice `uq_convites_viagem_pendente`).
- **Não convida quem já participa** (criador ou colaborador): 409, sem enviar email.
- **Falha no envio do email** retorna 503 e nada é gravado; o criador tenta de novo.
- **Gestão exclusiva do criador (RN04).** Editor e Visualizador recebem 403 ao
  convidar, listar ou cancelar convites, alterar papéis ou remover alguém, inclusive
  a si mesmos. Quem não participa da viagem recebe 404, como se ela não existisse.
- **O criador não é alterado nem removido** (400).
- **Efeito imediato.** `PoliticaAcessoViagem` lê o papel do banco a cada requisição
  e o JWT não carrega papel; promoção, rebaixamento e remoção valem na próxima
  chamada do colaborador.

## Respostas

| Situação | Status |
|---|---|
| Convite enviado | 201 |
| Aceite bem-sucedido (retorna a viagem com `papel_usuario`) | 201 |
| Link inexistente ou expirado | 404 |
| Link aberto com conta de outro email | 403 |
| Link já usado, ou usuário já participa da viagem | 409 |
| Convidar quem já participa | 409 |
| Falha ao enviar o email | 503 |
| Colaborador tentando gerenciar convites/membros | 403 |
| Viagem de que o usuário não participa | 404 |
| Convite pendente ou colaborador inexistente nesta viagem | 404 |
| Alterar ou remover o criador | 400 |
| Email malformado, papel fora de `editor`/`visualizador`, campos extras | 422 |

## Configuração

| Variável | Padrão | Uso |
|---|---|---|
| `CONVITE_URL` | `http://localhost:3000/convite` | Página do frontend que recebe `?token=` e chama o aceite |

O envio usa o mesmo `EmailSender` da recuperação de senha (`EMAIL_BACKEND`, SMTP).
No Docker Compose os emails ficam no Mailpit, em <http://localhost:8025>.

As notificações `membro_entrou`, `papel_alterado` e `membro_removido` (RF21) já são
persistidas na mesma transação da alteração. A API permite listar e marcar como
lidas somente as notificações do próprio usuário. Veja o
[escopo dos avisos](decisoes-de-produto.md#d9--email-e-notificacoes).

## Teste pelo Swagger

1. Crie dois usuários (criador e convidado), faça login com cada um e guarde os tokens.
2. Como criador, crie uma viagem e chame `POST /viagens/{id}/convites` com o email
   do convidado.
3. Abra o Mailpit (<http://localhost:8025>) e copie o valor de `token` do link.
4. Como convidado, chame `POST /viagens/convites/aceitar` com `{"token": "..."}`:
   a resposta traz `papel_usuario: "visualizador"`. Repetir retorna 409.
5. Como convidado, `PATCH /viagens/{id}` retorna 403.
6. Como criador, `PATCH /viagens/{id}/membros/{id_convidado}` com
   `{"papel": "editor"}`; repita o passo 5, que agora retorna 200.
7. Como criador, `DELETE /viagens/{id}/membros/{id_convidado}`; como convidado,
   `GET /viagens/{id}` passa a retornar 404.
