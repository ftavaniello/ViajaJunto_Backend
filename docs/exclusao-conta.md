# Exclusão de conta — issue #30

Política complementar aprovada para a funcionalidade existente. Os documentos
originais não especificam exclusão de contas nem transferência de titularidade.

`DELETE /usuarios/me` exige JWT e retorna `204` quando conclui.

- Se qualquer viagem criada pelo usuário tiver outro colaborador (Editor ou
  Visualizador), retorna `409` com uma explicação. Nenhum dado é alterado,
  inclusive viagens individuais; a conta e suas sessões continuam válidas.
- Sem esse impedimento, exclui a conta e suas viagens sem colaboradores, com
  roteiros, atividades, orçamentos e convites dessas viagens.
- Remove suas participações em viagens de outros usuários, preservando o
  planejamento e os demais participantes.
- Preserva avaliações públicas com autor nulo, incluindo nota e comentário;
  elas continuam contando nas médias. A referência à ocorrência fica nula
  quando o roteiro correspondente é excluído.
- Limpa a referência do responsável pela conclusão, preservando sua data.
- Remove tokens de recuperação, revogações e notificações destinadas à conta.
  Referências à conta como ator de notificações ou emissor de convites ficam
  nulas, conforme as chaves estrangeiras existentes. O texto histórico das
  notificações permanece como foi registrado.

Não há transferência automática de propriedade. O usuário deve resolver as
viagens compartilhadas antes de tentar novamente; a API não remove colaboradores
nem exclui viagens compartilhadas em nome dele ao excluir a conta.

A verificação e a exclusão acontecem na mesma transação. O adaptador bloqueia
primeiro o usuário e depois suas viagens, por id. Os locks conflitam com as
verificações de FK de novas viagens e participações, evitando que um novo vínculo
seja incluído entre a verificação e a exclusão. Falhas desfazem todas as alterações.
As cascatas existentes são usadas apenas após a aprovação explícita do caso de uso;
não houve alteração de schema ou necessidade de migration.

O cache de contagem de usuários é invalidado somente depois do commit. A
validação de autenticação consulta a existência da conta no banco: após a
exclusão, tokens antigos recebem `401`.

## Teste no Swagger com o seed

1. Autentique como `criador.demo@example.com`: excluir a conta retorna `409`
   enquanto sua viagem compartilhada tiver colaboradores.
2. Para testar a exclusão efetiva, use `descartavel.demo@example.com`, senha
   inicial `DemoViaja123!`: `DELETE /usuarios/me` retorna `204`. O roteiro próprio
   desaparece, mas suas avaliações permanecem anônimas.
3. Com o mesmo token, `GET /usuarios/me` retorna `401`.

Essas exclusões alteram os dados locais. Reiniciar a API não restaura contas
excluídas; a seed é idempotente.
