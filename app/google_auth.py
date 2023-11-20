import datetime
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi_sso.sso.google import GoogleSSO
from jose import jwt
from starlette.middleware.cors import CORSMiddleware

SECRET_KEY = os.environ.get('SECRET_KEY')
CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
AWS_EC2_ADDRESS = os.environ.get('AWS_EC2_ADDRESS')

sso = GoogleSSO(client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                redirect_uri=AWS_EC2_ADDRESS+"/auth/callback")

google_auth_app = FastAPI()
google_auth_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@google_auth_app.get("/login")
async def login():
    with sso:
        return await sso.get_login_redirect()


@google_auth_app.get("/logout")
async def logout():
    response = RedirectResponse(url="/logout-page")
    response.delete_cookie(key="token")
    return response


@google_auth_app.get("/callback")
async def login_callback(request: Request):
    with sso:
        openid = await sso.verify_and_process(request)
        if not openid:
            raise HTTPException(status_code=401, detail="Authentication failed")

    # Create a JWT with the user's OpenID
    expiration = datetime.datetime.utcnow() + datetime.timedelta(minutes=60)
    token = jwt.encode({"pld": openid.model_dump(), "exp": expiration, "sub": openid.id},
                       key=SECRET_KEY, algorithm="HS256")
    response = RedirectResponse(url="/protected")
    response.set_cookie(
        key="token", value=token, expires=expiration
    )  # This cookie will make sure /protected knows the user
    # print(jwt.decode(token, key=SECRET_KEY, algorithms="HS256"))
    return response
