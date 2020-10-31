from pydantic import BaseModel, Field, constr
from spectree import SpecTree, Response
from spectree.plugins.starlette_plugin import StarlettePlugin, PAGES
from starlette.applications import Starlette
from starlette.authentication import requires
from sqlalchemy.orm import Session
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route
from .config import settings
from .orm.oauth2.token import oauth2_tokens
from .orm.db import db_session, session_scope


from dependency_injector.wiring import Closing
from dependency_injector.wiring import Provide
from .containers import Container

UI_ROUTES = {
  'redoc': 'api',
  'swagger': 'swagger'
}

class CustomPlugin(StarlettePlugin):

    def register_route(self, app):
        self.app = app
        try:
            self.app.add_route(
                self.config.spec_url,
                lambda request: JSONResponse(self.spectree.spec),
            )
        except: # some weirdness in the spectree library
            pass
        for ui in PAGES:
            self.app.add_route(
                f'/{self.config.PATH}/{UI_ROUTES[ui]}',
                lambda request, ui=ui: HTMLResponse(
                    PAGES[ui].format(self.config.spec_url)
                ),
            )

_app = SpecTree('starlette', path='docs', backend=CustomPlugin, MODE='strict')


class Message(BaseModel):
    text: str


class Profile(BaseModel):
    name: constr(min_length=2, max_length=40)  # Constrained Str
    age: int = Field(
        ...,
        gt=0,
        lt=150,
        description='user age(Human)'
    )


@_app.validate(json=Profile, resp=Response(HTTP_200=Message, HTTP_403=None), tags=['api'])
@requires('app_auth', status_code=403)
async def user_profile(request):
    """
    verify user profile (summary of this endpoint)

    user's name, user's age, ... (long description)
    """
    print(request.context.json)  # or await request.json()
    return JSONResponse({'text': 'it works'})



@requires(['api_auth'], status_code=403)
async def widget(request):
    return JSONResponse({ 'foo': 'bar' })



"""
Headers({'host': 'localhost:8000', 'user-agent': 'python-requests/2.24.0', 'accept-encoding': 'gzip, deflate', 'accept': '*/*', 'connection': 'keep-alive', 'authorization': 'OAuth oauth_nonce="o8UwM6s2yCqZKjt5lhDMKhg0Uqk8Kw", oauth_timestamp="1603486212", oauth_version="1.0", oauth_signature_method="HMAC-SHA1", oauth_consumer_key="YOUR-CLIENT-ID", oauth_token="oauth_token", oauth_signature="PRtLO8T8l2HyccoIeGGx40O1Tcs%3D"'})
"""

def authorize(request):
    print(request.headers)
    #grant = server.validate_consent_request(request, end_user=request.user)
    #context = dict(grant=grant, user=request.user)
    #return render(request, 'authorize.html', context)
    #if is_user_confirmed(request):
    #    # granted by resource owner
    #    return server.create_authorization_response(request, grant_user=request.user)
    ## denied by resource owner
    #return server.create_authorization_response(request, grant_user=None)


async def token_refresh(request):
    data = dict(await request.form())
    data['access_lifetime'] = settings.OAUTH2_ACCESS_TOKEN_TIMEOUT_SECONDS
    data['refresh_lifetime'] = settings.OAUTH2_REFRESH_TOKEN_TIMEOUT_SECONDS
    token = oauth2_tokens.refresh(**data)
    return JSONResponse(token.response_data())


async def token(request):
    data = dict(await request.form())
    data['access_lifetime'] = settings.OAUTH2_ACCESS_TOKEN_TIMEOUT_SECONDS
    data['refresh_lifetime'] = settings.OAUTH2_REFRESH_TOKEN_TIMEOUT_SECONDS
    token = oauth2_tokens.create(**data)
    return JSONResponse(token.response_data())


routes = [
    Route('/user', user_profile, methods=['POST']),
    Route('/auth', authorize, methods=['GET']),
    Route('/token', token, methods=['POST']),
    Route('/token-refresh', token_refresh, methods=['POST']),
    Route('/widget/', widget)
]


def get_app():
    app = Starlette(
        debug=True,
        routes=routes,
        on_startup=[])
    _app.register(app)
    return app
