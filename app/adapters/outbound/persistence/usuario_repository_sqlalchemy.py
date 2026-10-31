from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.adapters.outbound.persistence.usuario_model import USUARIOS_EMAIL_UNIQUE, UsuarioModel
from app.domain.entities.usuario import Usuario
from app.domain.errors import EmailDuplicado, UsuarioNaoEncontrado
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
            if model is None:
                raise UsuarioNaoEncontrado("Usuário não encontrado")
            model.nome = usuario.nome
            model.email = usuario.email
            model.senha_hash = usuario.senha_hash

        try:
            self.db.commit()
        except IntegrityError as error:
            # A unicidade do email e garantida pelo banco; a verificacao previa no
            # caso de uso nao elimina a condicao de corrida entre requisicoes.
            self.db.rollback()
            if _constraint_violada(error) == USUARIOS_EMAIL_UNIQUE:
                raise EmailDuplicado("Já existe um usuário com este email") from error
            raise
        self.db.refresh(model)

        return self._to_entity(model)

    def buscar_por_id(self, usuario_id: int) -> Usuario | None:
        model = self.db.get(UsuarioModel, usuario_id)

        return self._to_entity(model) if model else None

    def buscar_por_email(self, email: str) -> Usuario | None:
        model = self.db.query(UsuarioModel).filter(UsuarioModel.email == email).first()

        return self._to_entity(model) if model else None

    def contar(self) -> int:
        return self.db.scalar(select(func.count()).select_from(UsuarioModel))

    def deletar(self, usuario_id: int) -> None:
        model = self.db.get(UsuarioModel, usuario_id)

        if model is not None:
            self.db.delete(model)
            self.db.commit()

    @staticmethod
    def _to_entity(model: UsuarioModel) -> Usuario:
        return Usuario(
            id=model.id,
            nome=model.nome,
            email=model.email,
            senha_hash=model.senha_hash,
            criado_em=model.criado_em,
        )


def _constraint_violada(error: IntegrityError) -> str | None:
    # psycopg2 expoe o nome da constraint violada em diag.constraint_name.
    diag = getattr(error.orig, "diag", None)
    return getattr(diag, "constraint_name", None)
