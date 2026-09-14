class Usuario:
    def __init__(
        self,
        nome: str,
        email: str,
        senha_hash: str,
        id: int | None = None,
    ):
        if not nome.strip():
            raise ValueError("Nome não pode ser vazio")

        if not email.strip():
            raise ValueError("Email não pode ser vazio")

        if not senha_hash.strip():
            raise ValueError("Senha não pode ser vazia")

        self.id = id
        self.nome = nome
        self.email = email
        self.senha_hash = senha_hash