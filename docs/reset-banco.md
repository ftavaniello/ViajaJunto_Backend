# Reset explícito do banco local

Este comando apaga todos os dados da aplicação no banco local `viajajunto`, aplica
as migrações e carrega o seed atualizado. Use uma vez para substituir a carga antiga,
ou quando quiser voltar aos dados iniciais. Viagens, contas, avaliações e alterações
manuais atuais serão removidas.

## Executar

Com o PostgreSQL do Compose em execução, na raiz do repositório:

```powershell
docker compose stop api
docker compose run --rm --no-deps api python -m app.adapters.inbound.cli.reset_banco --confirmar
docker compose up -d --no-deps api
```

Pare a API antes do reset para evitar requisições durante a reconstrução. O container
temporário executa apenas o comando, sem iniciar outro servidor. Se o serviço `db`
estiver parado, inicie-o antes com:

```powershell
docker compose up -d --no-deps --wait db
```

Depois do sucesso, abra <http://localhost:8000/docs> e faça login novamente:
`criador.demo@example.com` / `DemoViaja123!`.
Os dados iniciais incluem seis usuários, quatro destinos, 24 atividades públicas,
27 viagens, 36 atividades do roteiro e 20 avaliações fictícias.

## Restrições

- A opção `--confirmar` é obrigatória. Sem ela o comando termina sem executar o reset.
- Exige exatamente `APP_ENV=development`; `test`, `staging` e `production` são recusados.
- Exige `postgresql+psycopg2`, host `db`, porta `5432` e banco `viajajunto`, sem parâmetros
  extras na URL. Outros destinos, incluindo `localhost` e o banco de testes, são recusados.
- Confere também o nome retornado pelo PostgreSQL antes de alterar o schema.
- Credenciais continuam vindo da configuração; não são exibidas na saída de erro.

A restrição corresponde ao banco padrão do Compose deste projeto. Configurações
com outro host, porta ou nome de banco são bloqueadas; não há opção de ignorar essa
verificação no comando.

## Transação e falhas

A limpeza do schema `public`, todas as migrações e o seed usam a mesma conexão e
transação do PostgreSQL. Se a migração ou o seed falhar, a transação é desfeita e o
schema e os dados anteriores são preservados. A contagem em cache é invalidada
somente depois da confirmação da transação.

O comando aguarda locks por até cinco segundos; pare a API e feche transações abertas
no DBClient antes de tentar novamente se houver bloqueio. Ele não remove volumes,
não limpa Redis inteiro e não altera o banco de testes.

O reset não faz parte do `docker compose up`. Nas inicializações normais, o seed
preserva edições e exclusões e não duplica registros. O reset só ocorre quando alguém
executa explicitamente o comando acima com `--confirmar`.

Veja [dados iniciais](seed-demonstracao.md) e [destinos reais](seed-demonstracao.md).
