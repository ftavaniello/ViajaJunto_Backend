from app.domain.entities.usuario import Usuario
from app.domain.ports.usuario_repository import UsuarioRepository


class AtualizarUsuario:
    def __init__(self, repository: UsuarioRepository):
        self.repository = repository

    def execute(self, usuario_id: int, nome: str | None, email: str | None) -> Usuario:
        usuario = self.repository.buscar_por_id(usuario_id)

        if usuario is None:
            raise ValueError("Usuário não encontrado")

        if email and email != usuario.email:
            usuario_existente = self.repository.buscar_por_email(email)

            if usuario_existente:
                raise ValueError("Já existe um usuário com este email")

        usuario_atualizado = Usuario(
            id=usuario.id,
            nome=nome or usuario.nome,
            email=email or usuario.email,
            senha_hash=usuario.senha_hash,
        )

        return self.repository.salvar(usuario_atualizado)
