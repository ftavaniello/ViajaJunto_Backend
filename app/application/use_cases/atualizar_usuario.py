from app.domain.entities.usuario import Usuario
from app.domain.errors import EmailDuplicado, UsuarioNaoEncontrado
from app.domain.ports.unit_of_work import UnitOfWork
from app.domain.ports.usuario_repository import UsuarioRepository


class AtualizarUsuario:
    def __init__(self, repository: UsuarioRepository, uow: UnitOfWork):
        self.repository = repository
        self.uow = uow

    def execute(self, usuario_id: int, nome: str | None, email: str | None) -> Usuario:
        usuario = self.repository.buscar_por_id(usuario_id)

        if usuario is None:
            raise UsuarioNaoEncontrado("Usuário não encontrado")

        if email and email != usuario.email:
            usuario_existente = self.repository.buscar_por_email(email)

            if usuario_existente:
                raise EmailDuplicado("Já existe um usuário com este email")

        usuario_atualizado = Usuario(
            id=usuario.id,
            nome=usuario.nome if nome is None else nome,
            email=usuario.email if email is None else email,
            senha_hash=usuario.senha_hash,
        )

        with self.uow:
            salvo = self.repository.salvar(usuario_atualizado)
            self.uow.commit()

        return salvo
