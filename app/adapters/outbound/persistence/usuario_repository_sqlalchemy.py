from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.usuario_model import UsuarioModel
from app.domain.entities.usuario import Usuario
from app.domain.ports.usuario_repository import UsuarioRepository


class SQLAlchemyUsuarioRepository(UsuarioRepository):
    def __init__(self, db: Session):
        self.db = db

    def salvar(self, usuario: Usuario) -> Usuario:
        if usuario.id is None:
            model = UsuarioModel(
                nome=usuario.nome,
                email=usuario.email,
                senha_hash=usuario.senha_hash,
            )
            self.db.add(model)
        else:
            model = self.db.get(UsuarioModel, usuario.id)
            model.nome = usuario.nome
            model.email = usuario.email
            model.senha_hash = usuario.senha_hash

        self.db.commit()
        self.db.refresh(model)

        return self._to_entity(model)

    def buscar_por_id(self, usuario_id: int) -> Usuario | None:
        model = self.db.get(UsuarioModel, usuario_id)

        return self._to_entity(model) if model else None

    def buscar_por_email(self, email: str) -> Usuario | None:
        model = (
            self.db.query(UsuarioModel)
            .filter(UsuarioModel.email == email)
            .first()
        )

        return self._to_entity(model) if model else None

    @staticmethod
    def _to_entity(model: UsuarioModel) -> Usuario:
        return Usuario(
            id=model.id,
            nome=model.nome,
            email=model.email,
            senha_hash=model.senha_hash,
        )
