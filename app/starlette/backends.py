import datetime
from starlette.authentication import AuthenticationBackend, AuthCredentials, SimpleUser
from .. import orm
from ..orm.oauth2.token import OAuth2Token
from ..orm.db import session_scope
from ..orm.user import User
from .. import containers

from dataclasses import dataclass
import dataclasses

class SessionAuthBackend(AuthenticationBackend):

    async def authenticate(self, request):
        if 'user_id' in request.session:
            user_id = request.session['user_id']
            with session_scope() as db:
                user = User.objects.get(user_id, db=db)
            return AuthCredentials(['app_auth']), user
        if request.headers.get('authorization'):
            bearer = request.headers['authorization'].split()
            if bearer[0] != 'Bearer':
                return
            bearer = bearer[1]
            token = OAuth2Token.objects.get_by_access_token(bearer)
            if token.revoked:
                raise Exception
            if datetime.datetime.utcnow() > token.access_token_expires_at:
                raise Exception
            request.scope['token'] = token
            return AuthCredentials(['api_auth']), None