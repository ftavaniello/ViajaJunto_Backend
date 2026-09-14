from abc import ABC, abstractmethod

from app.domain.entities.usuario import Usuario


class UsuarioRepository(ABC):

    @abstractmethod
    def salvar(self, usuario: Usuario) -> Usuario:
        pass

    @abstractmethod
    def buscar_por_id(self, usuario_id: int) -> Usuario | None:
        pass

    @abstractmethod
    def buscar_por_email(self, email: str) -> Usuario | None:
        pass