from abc import ABC, abstractmethod


class PasswordHasher(ABC):
    @abstractmethod
    def hash(self, senha: str) -> str:
        pass

    @abstractmethod
    def verificar(self, senha: str, senha_hash: str) -> bool:
        pass
