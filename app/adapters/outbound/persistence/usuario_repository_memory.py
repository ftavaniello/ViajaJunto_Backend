from datetime import datetime, timezone

from app.domain.entities.usuario import Usuario
from app.domain.errors import EmailDuplicado, UsuarioNaoEncontrado
from app.domain.ports.usuario_repository import UsuarioRepository


class UsuarioRepositoryMemory(UsuarioRepository):
    def __init__(self):
        self.usuarios: dict[int, Usuario] = {}
        self.proximo_id = 1

    def salvar(self, usuario: Usuario) -> Usuario:
        # Espelha a constraint unique(email) do banco, inclusive quando o caso de
        # uso nao percebe o conflito antes de salvar.
        existente = self.buscar_por_email(usuario.email)
        if existente is not None and existente.id != usuario.id:
            raise EmailDuplicado("Já existe um usuário com este email")

        if usuario.id is None:
            usuario.id = self.proximo_id
            usuario.criado_em = datetime.now(timezone.utc)
            self.proximo_id += 1
        else:
            anterior = self.usuarios.get(usuario.id)
            if anterior is None:
                raise UsuarioNaoEncontrado("Usuário não encontrado")
            # Assim como no banco, a data de cadastro nao muda numa atualizacao.
            usuario.criado_em = anterior.criado_em

        self.usuarios[usuario.id] = usuario

        return usuario

    def buscar_por_id(self, usuario_id: int) -> Usuario | None:
        return self.usuarios.get(usuario_id)

    def buscar_por_email(self, email: str) -> Usuario | None:
        for usuario in self.usuarios.values():
            if usuario.email == email:
                return usuario

        return None

    def contar(self) -> int:
        return len(self.usuarios)

    def deletar(self, usuario_id: int) -> None:
        self.usuarios.pop(usuario_id, None)
