import bcrypt

from app.domain.ports.password_hasher import PasswordHasher


class BcryptPasswordHasher(PasswordHasher):

    def hash(self, senha: str) -> str:
        return bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()

    def verificar(self, senha: str, senha_hash: str) -> bool:
        return bcrypt.checkpw(senha.encode(), senha_hash.encode())
