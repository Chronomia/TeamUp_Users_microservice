import datetime
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi_sso.sso.google import GoogleSSO
from jose import jwt

SECRET_KEY = os.environ.get('SECRET_KEY')
CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')

sso = GoogleSSO(client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                redirect_uri="http://127.0.0.1:8000/auth/callback")
auth_app = FastAPI()


@auth_app.get("/login")
async def login():
    with sso:
        return await sso.get_login_redirect()


@auth_app.get("/logout")
async def logout():
    response = RedirectResponse(url="/prot")
    response.delete_cookie(key="token")
    return response


@auth_app.get("/callback")
async def login_callback(request: Request):
    with sso:
        openid = await sso.verify_and_process(request)
        if not openid:
            raise HTTPException(status_code=401, detail="Authentication failed")

    # Create a JWT with the user's OpenID
    expiration = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(days=1)
    token = jwt.encode({"pld": openid.model_dump(), "exp": expiration, "sub": openid.id},
                       key=SECRET_KEY, algorithm="HS256")
    response = RedirectResponse(url="/protected")
    response.set_cookie(
        key="token", value=token, expires=expiration
    )  # This cookie will make sure /protected knows the user
    decoded = jwt.decode(token, key=SECRET_KEY, algorithms="HS256")
    print(decoded)
    return response
