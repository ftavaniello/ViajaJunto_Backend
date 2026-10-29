# Sessões, logout e troca de senha (RF02)

> **Status:** decisão adotada e implementada.
> **Requisito:** RF02 — permitir login e logout de usuários.

## Decisão

**Logout invalida o token no servidor.** Descartar o token só no cliente não
encerraria a sessão de verdade: qualquer cópia do JWT (outra aba, log, proxy,
ferramenta de teste) continuaria aceita até expirar. Com a revogação no servidor
é possível demonstrar que um token encerrado deixa de funcionar.

Não há refresh token: ele não é requisito do RF02. O access token continua
expirando em `JWT_EXPIRE_MINUTES` (60 min por padrão) e, depois disso, o
usuário faz login de novo.

## Como funciona

Cada token emitido no login é um JWT com estes claims:

| Claim | Uso |
|---|---|
| `sub` | Id do usuário |
| `iat` / `exp` | Emissão e expiração |
| `jti` | Identificador único da sessão; é o que o logout revoga |
| `ver` | Versão das sessões do usuário no momento da emissão |

Toda requisição protegida (`get_usuario_atual` → `ConsultarUsuarioAutenticado`)
só aceita o token se **todas** as condições valerem:

1. assinatura válida e `exp` no futuro;
2. o `jti` **não** está em `tokens_revogados`;
3. a conta ainda existe;
4. `ver` do token é igual a `usuarios.versao_sessao`.

Qualquer falha resulta em `401` com `WWW-Authenticate: Bearer`.

### Logout — `POST /auth/logout`

- Requer o token no header `Authorization: Bearer <token>`; responde `204`.
- Grava o `jti` e a expiração do token em `tokens_revogados` (o token em si
  nunca é armazenado).
- **Token copiado antes do logout:** é o mesmo `jti`, portanto também passa a
  receber `401` em todos os endpoints protegidos, mesmo antes de expirar.
- Encerra **apenas aquela sessão**. Outros logins do mesmo usuário (outro
  navegador ou dispositivo) continuam válidos.
- Logout repetido com o mesmo token, sem token, com token inválido ou expirado → `401`.
- A linha de revogação só precisa existir até `expira_em`: depois disso o
  próprio JWT já é recusado. Revogações vencidas são apagadas a cada novo logout,
  e todas as revogações de um usuário somem quando a conta é excluída (`ON DELETE CASCADE`).

### Troca de senha — `PATCH /usuarios/me/senha`

- Incrementa `usuarios.versao_sessao` na mesma transação que grava o novo hash.
- Com isso **todas** as sessões do usuário são encerradas, **inclusive a que
  fez a troca**: quem tinha a senha antiga (e talvez um token roubado) perde o
  acesso. O cliente deve levar o usuário para o login com a nova senha.
- Se a troca for recusada (senha atual errada, senha nova inválida), nada muda
  e as sessões continuam válidas.
- Alterar nome ou email não encerra sessões.

### Recuperação de senha (RF03)

Ainda não implementada. Quando for, a redefinição de senha pelo link de
recuperação **deve** seguir a mesma regra da troca: incrementar
`versao_sessao`, encerrando todas as sessões existentes.

## Armazenamento e falhas

- A lista de revogação fica no **PostgreSQL** (`tokens_revogados`), atrás da
  porta `TokenRevogadoRepository`. Ela é consultada a cada requisição
  autenticada, na mesma Session da requisição.
- **Não** usa o Redis/ElastiCache da contagem de usuários. Aquele cache tem
  fallback permissivo (se o Redis cai, a contagem vem do banco — `BYPASS`), o
  que é aceitável para um número exibido, mas não para autorização: um fallback
  "não sei, então deixa passar" aceitaria tokens revogados.
- Se o banco estiver indisponível a requisição falha (erro 5xx), **nunca** é
  autorizada. O comportamento é *fail-closed*.

## Compatibilidade

Tokens emitidos antes desta mudança não têm `jti` nem `ver` e são recusados
(`401`). Na implantação, os usuários logados precisam entrar de novo uma vez.

## Onde está no código

| Camada | Arquivo |
|---|---|
| Porta de revogação | `app/domain/ports/token_revogado_repository.py` |
| Dados do token | `app/domain/ports/token_service.py` (`DadosToken`) |
| Versão de sessão | `app/domain/entities/usuario.py` (`versao_sessao`) |
| Logout | `app/application/use_cases/encerrar_sessao.py` |
| Validação da sessão | `app/application/use_cases/consultar_usuario_autenticado.py` |
| Troca de senha | `app/application/use_cases/alterar_senha.py` |
| Persistência | `app/adapters/outbound/persistence/token_revogado_*.py` |
| JWT | `app/adapters/outbound/security/pyjwt_token_service.py` |
| Rota | `app/adapters/inbound/api/routes/auth.py` |
| Migração | `alembic/versions/b7e4d2a91c03_sessoes_e_logout.py` |
| Testes | `tests/application/test_sessao.py`, `tests/integration/test_logout_api.py`, `tests/integration/test_token_revogado_repository_sqlalchemy.py`, `tests/integration/test_pyjwt_token_service.py` |
