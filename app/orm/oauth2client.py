"""
https://docs.authlib.org/en/latest/flask/2/authorization-server.html
"""
import datetime
import secrets
from dataclasses import dataclass
from typing import List, Optional
from dependency_injector.wiring import Provide, Closing
from sqlalchemy import Column, Integer, ForeignKey, String, DateTime
from sqlalchemy.orm import relationship, Session
from sqlalchemy import UniqueConstraint
from . import base
from . import user
from . import OAUTH2_CLIENT_ID_MAX_CHARS, OAUTH2_CLIENT_SECRET_MAX_CHARS
from . import OAUTH2_CLIENT_ID_BYTES, OAUTH2_CLIENT_SECRET_BYTES
from ..auth import create_random_key
from ..containers import Container


class InvalidOAuth2Client(Exception):
    """Invalid OAuth2 client."""


@dataclass
class OAuth2Client(base.ModelBase, base.DataModel):
    """OAuth2 API Client model."""

    __tablename__ = 'oauth2_clients'
    __table_args__ = (
        UniqueConstraint('name', 'user_id', name='name_user_id_unique_1'),
    )

    id:int = Column(Integer, primary_key=True)
    name:str = Column(String(100), nullable=False, default='Primary')
    client_id:str = Column(String(OAUTH2_CLIENT_ID_MAX_CHARS), unique=True,
        index=True, nullable=False)
    client_secret:str = Column(String(OAUTH2_CLIENT_SECRET_MAX_CHARS), unique=True,
        index=True, nullable=False)
    created_at:datetime.datetime = Column(DateTime, nullable=False,
        default=datetime.datetime.utcnow)
    secret_expires_at:datetime.datetime = Column(Integer, nullable=True)
    user_id:int = Column(
        Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    user = relationship('User') # type: ignore

    InvalidOAuth2Client = InvalidOAuth2Client # pylint:disable=invalid-name

    def compare_secret(self, secret):
        """Compare a given secret with the secret for this instance.

        Returns True if they are the same.
        """
        return secrets.compare_digest(secret, self.client_secret)


class OAuth2ClientManager(base.CRUDManager[OAuth2Client]):
    """OAuth2 API object manager."""

    def create(self, properties,
            db:Session=Closing[Provide[Container.closed_db]]) -> base.ModelType:
        if 'client_id' not in properties:
            properties['client_id'] = create_random_key(OAUTH2_CLIENT_ID_BYTES)
        if 'client_secret' not in properties:
            properties['client_secret'] = create_random_key(OAUTH2_CLIENT_SECRET_BYTES)
        return super(OAuth2ClientManager, self).create(properties, db=db)

    @classmethod
    def get_by_client_id(cls, client_id: str, *,
            db:Session=Closing[Provide[Container.closed_db]]
        ) -> Optional[OAuth2Client]:
        """Get an API client by client ID."""
        return db.query(OAuth2Client).filter(
            OAuth2Client.client_id == client_id).one_or_none()

    @classmethod
    def get_for_user(cls, user:user.User, client_id: str, *,
            db:Session=Closing[Provide[Container.closed_db]]
        ) -> Optional[OAuth2Client]:
        """Get an API client by client ID."""
        return db.query(OAuth2Client).filter(
            OAuth2Client.client_id == client_id,
            OAuth2Client.user == user).one_or_none()

    @classmethod
    def fetch_for_user(cls, user:user.User, *,
            db:Session=Closing[Provide[Container.closed_db]]
        ) -> List[OAuth2Client]:
        """Get the API clients for the user."""
        return db.query(OAuth2Client).filter(OAuth2Client.user==user).all()

    @classmethod
    def delete_for_user(cls, user:user.User, client_id:str, *,
            db:Session=Closing[Provide[Container.closed_db]]
        ) -> bool:
        """Delete the specified API client."""
        obj = db.query(OAuth2Client).filter(
            OAuth2Client.client_id == client_id,
            OAuth2Client.user==user).one_or_none()
        if obj:
            db.delete(obj)
            return True
        else:
            return False

    @classmethod
    def exists(cls, user:user.User, name:str, *,
            db:Session=Closing[Provide[Container.closed_db]]
        ) -> bool:
        """Return True if a client with this name exists for the given user."""
        q = db.query(OAuth2Client).filter(
            OAuth2Client.name == name,
            OAuth2Client.user == user)
        return db.query(q.exists()).scalar()


oauth2_clients = OAuth2ClientManager(OAuth2Client)
OAuth2Client.objects = oauth2_clients
