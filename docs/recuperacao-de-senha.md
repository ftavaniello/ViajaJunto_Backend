# Recuperação de senha por email (RF03)

> **Status:** implementada.
> **Requisito:** RF03 — oferecer recuperação de senha por email.
> **Depende de:** política de sessões em [`sessoes-e-logout.md`](sessoes-e-logout.md).

## Fluxo

1. O usuário informa o email em `POST /auth/recuperar-senha`.
2. Se existir conta com esse email, a API sorteia um token, grava **só o hash**
   dele e envia por email um link `RECUPERACAO_SENHA_URL?token=<token>`
   (o mesmo valor também aparece como código no corpo do email).
3. O frontend lê o `token` do link e envia `POST /auth/redefinir-senha` com
   `{"token": "...", "senha_nova": "..."}`.
4. A senha é trocada, o token é consumido e **todas as sessões** do usuário
   são encerradas. O usuário faz login com a nova senha.

## Contrato da API

| Rota | Corpo | Resposta |
|---|---|---|
| `POST /auth/recuperar-senha` | `{"email": "livia@example.com"}` | `202` com `{"detail": "Se o email estiver cadastrado, enviaremos um link para redefinir a senha."}` |
| `POST /auth/redefinir-senha` | `{"token": "...", "senha_nova": "novaSenha456"}` | `204`; `400` para token inválido, expirado ou já usado |

As duas rotas são públicas (sem `Authorization`). Erros de formato (email
mal formado, senha com menos de 8 caracteres) retornam `422`, como nas
demais rotas. Uma senha recusada **não** gasta o token.

## Regras

| Regra | Como é garantida |
|---|---|
| Token imprevisível | `secrets.token_urlsafe(32)`: 256 bits do gerador criptográfico do sistema |
| Persistência segura | A tabela `tokens_recuperacao_senha` guarda só o SHA-256 do token. Quem lê o banco não consegue montar um link válido |
| Expira | `expira_em` = emissão + 60 min (`RECUPERACAO_SENHA_VALIDADE_MINUTOS` em `app/domain/regras.py`) |
| Uso único | Ao redefinir, `usado_em` é preenchido. A linha é lida com `SELECT ... FOR UPDATE`, então duas redefinições simultâneas com o mesmo link não passam as duas |
| Só o link mais novo vale | Novo pedido e redefinição inutilizam os tokens pendentes do usuário |
| Encerra sessões | A redefinição incrementa `usuarios.versao_sessao`, como a troca de senha |
| Não revela contas | `POST /auth/recuperar-senha` responde sempre `202` com a mesma mensagem: email desconhecido, email cadastrado e falha no envio são indistinguíveis pela resposta |
| Mensagem única de erro | Token inexistente, expirado e reutilizado recebem o mesmo `400` |

### Falha no envio do email

Se o servidor de email recusar ou estiver fora do ar, a API **não** retorna
erro (isso revelaria que o email tem conta). A falha é registrada no log
(`Falha ao enviar email de recuperacao do usuario <id>`), sem o token. O token
gravado fica inutilizável, porque seu valor só existia no email que não saiu.
O usuário pode pedir um novo link.

### Limitações conhecidas

- **Tempo de resposta:** o envio é síncrono. Para um email cadastrado a
  resposta inclui o tempo da conversa SMTP, o que, medido com precisão,
  pode diferenciar contas existentes. Enviar em segundo plano (fila) resolve;
  fica para quando houver infraestrutura de filas.
- **Sem limite de tentativas:** não há rate limiting por IP ou por email.
  Cada pedido invalida o link anterior, então pedidos repetidos por terceiros
  atrapalham, mas não dão acesso à conta.
- Tokens usados ou vencidos não são apagados; somem com a conta (`ON DELETE CASCADE`).

## Envio de email: porta e adaptadores

O caso de uso depende só da porta `EmailSender`
(`app/domain/ports/email_sender.py`). O adaptador é escolhido por
`EMAIL_BACKEND` em `app/infrastructure/email.py`:

| `EMAIL_BACKEND` | Adaptador | Uso |
|---|---|---|
| `smtp` | `SmtpEmailSender` | Docker Compose (Mailpit) e produção (qualquer SMTP) |
| `console` (padrão) | `ConsoleEmailSender` | API rodando fora do Docker sem SMTP: o email vai para o log. **Nunca em produção**, o log passaria a conter links válidos |
| — | `EmailSenderMemory` | Só nos testes automatizados (injetado com `dependency_overrides`) |

Variáveis (ver `.env.example`):

| Variável | Padrão | Descrição |
|---|---|---|
| `EMAIL_BACKEND` | `console` | `smtp` ou `console` |
| `EMAIL_REMETENTE` | `ViajaJunto <nao-responda@viajajunto.local>` | Cabeçalho `From` |
| `SMTP_HOST` / `SMTP_PORT` | `localhost` / `1025` | Servidor SMTP |
| `SMTP_USUARIO` / `SMTP_SENHA` | vazio | Autenticação, se o servidor exigir |
| `SMTP_STARTTLS` | `false` | `true` para servidores reais na porta 587 |
| `RECUPERACAO_SENHA_URL` | `http://localhost:3000/redefinir-senha` | Página do frontend que recebe `?token=` |

## Como ver os emails no ambiente de teste

O Docker Compose inclui o **Mailpit**, um servidor SMTP falso que captura
todos os emails enviados pela API (nada sai para a internet). A API do
Compose já está configurada com `EMAIL_BACKEND=smtp` e `SMTP_HOST=mailpit`.

1. Suba o ambiente: `docker compose up -d --build`.
2. Peça a recuperação, pelo Swagger (<http://localhost:8000/docs>) ou:

   ```sh
   curl -X POST http://localhost:8000/auth/recuperar-senha \
     -H "Content-Type: application/json" \
     -d '{"email": "usuario@viajajunto.com"}'
   ```

   (`usuario@viajajunto.com` é o usuário criado pelas migrações.)
3. Abra a caixa de entrada do Mailpit em **<http://localhost:8025>**. O email
   aparece em segundos, com o link e o código.
4. Copie o código e chame `POST /auth/redefinir-senha` no Swagger:

   ```json
   {"token": "<código do email>", "senha_nova": "novaSenha456"}
   ```

   Ainda não há frontend, então o link para `localhost:3000` não abre nada;
   o que importa é o valor de `token`.

Para quem prefere linha de comando, o Mailpit tem API HTTP:
`curl http://localhost:8025/api/v1/messages` lista os emails e
`curl -X DELETE http://localhost:8025/api/v1/messages` limpa a caixa.

**API fora do Docker:** suba só o Mailpit (`docker compose up -d mailpit`) e
use `EMAIL_BACKEND=smtp` e `SMTP_HOST=localhost` no `.env`. Sem nenhum SMTP,
deixe `EMAIL_BACKEND=console` e procure o email no log do Uvicorn.

**Testes automatizados** não usam SMTP: trocam a porta por
`EmailSenderMemory` e leem o token da lista `enviados`. A falha de envio é
simulada com `EmailSenderMemory(falhar=True)`.

## Onde está no código

| Camada | Arquivo |
|---|---|
| Entidade e regras do token | `app/domain/entities/token_recuperacao_senha.py` |
| Portas | `app/domain/ports/token_recuperacao_senha_repository.py`, `app/domain/ports/email_sender.py` |
| Casos de uso | `app/application/use_cases/solicitar_recuperacao_senha.py`, `app/application/use_cases/redefinir_senha.py` |
| Persistência | `app/adapters/outbound/persistence/token_recuperacao_senha_repository_*.py` (tabela criada em `alembic/versions/a3f1c9d27b45_modelo_de_dados_v1.py`) |
| Email | `app/adapters/outbound/email/`, `app/infrastructure/email.py` |
| Rotas | `app/adapters/inbound/api/routes/auth.py` |
| Testes | `tests/application/test_recuperar_senha.py`, `tests/application/test_email_sender.py`, `tests/integration/test_recuperacao_senha_api.py`, `tests/integration/test_token_recuperacao_senha_repository_sqlalchemy.py` |
