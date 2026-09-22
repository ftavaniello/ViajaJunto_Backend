from app.domain.entities.usuario import Usuario
from app.domain.ports.usuario_repository import UsuarioRepository


class UsuarioRepositoryMemory(UsuarioRepository):
    def __init__(self):
        self.usuarios: dict[int, Usuario] = {}
        self.proximo_id = 1

    def salvar(self, usuario: Usuario) -> Usuario:
        if usuario.id is None:
            usuario.id = self.proximo_id
            self.proximo_id += 1

        self.usuarios[usuario.id] = usuario

        return usuario

    def buscar_por_id(self, usuario_id: int) -> Usuario | None:
        return self.usuarios.get(usuario_id)

    def buscar_por_email(self, email: str) -> Usuario | None:
        for usuario in self.usuarios.values():
            if usuario.email == email:
                return usuario

        return None

    def deletar(self, usuario_id: int) -> None:
        self.usuarios.pop(usuario_id, None)