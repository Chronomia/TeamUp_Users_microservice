import json
import logging
import os
import random
import string
from contextlib import asynccontextmanager
from datetime import timedelta, datetime
from typing import Optional, Union, Annotated

import boto3
import certifi
import uvicorn
from bson import ObjectId
from fastapi import FastAPI, Body, HTTPException, Security, Depends
from fastapi.security import APIKeyCookie, OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi_sso.sso.base import OpenID
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from pymongo import MongoClient, ReturnDocument
from random_username.generate import generate_username
from starlette import status
from starlette.middleware.cors import CORSMiddleware

from app.google_auth import google_auth_app
from app.user import UserModel, UserGroupModel, UserEventModel, UpdateUserModel, UserCollection, UserWithPwd, \
    UserFullModel, UpdateUsername, UserWithJWT

ATLAS_URI = os.environ.get('ATLAS_URI')
SECRET_KEY = os.environ.get('SECRET_KEY')
AWS_ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.environ.get('AWS_SECRET_KEY')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

logger = logging.getLogger(__name__)
mongodb_service = {}

TOPIC_ARN = os.environ.get('TOPIC_ARN')
lambda_client = boto3.client(
    'lambda',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name='us-east-1'
)


class SimpleResponseModel(BaseModel):
    message: str


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def authenticate_user_by_username(username: str, password: str):
    user = mongodb_service["collection"].find_one(
        {"username": username}
    )

    if user is None or not verify_password(password, user["password"]):
        raise HTTPException(status_code=401,
                            detail=f"Username or password is incorrect. "
                                   f"Use Google SSO login if you signed up the account "
                                   f"using Google SSO Sign On",
                            headers={"WWW-Authenticate": "Bearer"})

    return user


def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_logged_user(cookie: str = Security(APIKeyCookie(name="token"))) -> OpenID:
    try:
        claims = jwt.decode(cookie, key=SECRET_KEY, algorithms=["HS256"])
        return OpenID(**claims["pld"])
    except Exception as error:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials") from error


@asynccontextmanager
async def lifespan(app: FastAPI):
    mongodb_service["client"] = MongoClient(ATLAS_URI, tlsCAFile=certifi.where())
    mongodb_service["db"] = mongodb_service["client"]["TeamUp"]
    mongodb_service["collection"] = mongodb_service["db"]["Users"]
    yield
    mongodb_service.clear()


service = FastAPI(lifespan=lifespan)
service.mount("/auth", google_auth_app)
service.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def build_user_info(user):
    if isinstance(user, dict):
        user_info = {
            "username": user["username"],
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "email": user["email"],
            "contact": user["contact"],
            "location": user["location"],
            "interests": user["interests"],
            "age": user["age"],
            "gender": user["gender"],
        }
    else:
        user_info = {
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "contact": user.contact,
            "location": user.location,
            "interests": user.interests,
            "age": user.age,
            "gender": user.gender,
        }
    return user_info


@service.get('/')
async def root():
    return {'user_service_status': 'ONLINE'}


@service.post(
    "/users/",
    response_description="Add a new user",
    response_model=UserModel,
    status_code=status.HTTP_201_CREATED,
    response_model_by_alias=False
)
async def create_user(user: UserWithPwd = Body(...)):
    if len(list(mongodb_service["collection"].find({"username": user.username}).limit(1))) == 1:
        raise HTTPException(status_code=409, detail=f"Username {user.username} is already taken")

    if len(list(mongodb_service["collection"].find({"email": user.email}).limit(1))) == 1:
        raise HTTPException(status_code=409, detail=f"Email {user.email} is already registered")

    user.password = get_password_hash(user.password)

    new_user = mongodb_service["collection"].insert_one(
        user.model_dump(by_alias=True, exclude={"id"})
    )

    created_user = mongodb_service["collection"].find_one(
        {"_id": new_user.inserted_id}
    )

    lambda_payload = {
        "action": "create",
        "subject": f"User {created_user['_id']} created successfully",
        "user_info": await build_user_info(created_user)
    }

    lambda_client.invoke(
        FunctionName='userSNSnotifications',
        InvocationType='Event',
        Payload=json.dumps(lambda_payload),
    )

    return created_user


@service.get(
    "/users/",
    response_description="List all users with pagination and optional filtering by interest/location",
    response_model=UserCollection,
    response_model_by_alias=False,
)
async def list_all_users(interest: Optional[str] = None, location: Optional[str] = None, page: int = 1, limit: int = 5):
    query = {}
    if interest:
        query["interests"] = {"$in": [interest]}
    if location:
        query["location"] = location

    items = mongodb_service["collection"].find(query).skip((page - 1) * limit).limit(limit)
    return UserCollection(users=items)


@service.get(
    "/users/id/{user_id}",
    response_description="Find a user by id",
    response_model=UserFullModel,
    response_model_by_alias=False,
)
async def find_user_by_id(user_id: str):
    user = mongodb_service["collection"].find_one(
        {"_id": ObjectId(user_id)}
    )

    if user is None:
        raise HTTPException(status_code=404, detail=f"User ID of {user_id} not found")

    return user


@service.get(
    "/users/name/{username}",
    response_description="Find a user by username",
    response_model=UserFullModel,
    response_model_by_alias=False,
)
async def find_user_by_username(username: str):
    user = mongodb_service["collection"].find_one(
        {"username": username}
    )

    if user is None:
        raise HTTPException(status_code=404, detail=f"Username {username} not found")

    return user


@service.get(
    "/users/email/{email}",
    response_description="Find a user by email",
    response_model=UserFullModel,
    response_model_by_alias=False,
)
async def find_user_by_email(email: str):
    user = mongodb_service["collection"].find_one(
        {"email": email}
    )

    if user is None:
        raise HTTPException(status_code=404, detail=f"Email {email} is not associated with a user account")

    return user


@service.put(
    "/users/{user_id}/profile",
    response_description="Update a user's profile by id",
    response_model=UserFullModel,
    response_model_by_alias=False,
)
async def update_user_profile(user_id: str, user: UpdateUserModel = Body(...)):
    current_user = mongodb_service["collection"].find_one({"_id": ObjectId(user_id)})

    user = {
        k: v for k, v in user.model_dump(by_alias=True).items() if v is not None
    }

    if len(user) >= 1:
        update_result = mongodb_service["collection"].find_one_and_update(
            {"_id": ObjectId(user_id)},
            {"$set": user},
            return_document=ReturnDocument.AFTER,
        )

        changes = {k: {"old": current_user.get(k), 'new': user[k]} for k in user}
        if update_result is not None:
            message = {'details': changes}
            lambda_payload = {
                "action": "update",
                "subject": f"User profile updated for user_id {user_id}",
                "change": message
            }

            lambda_client.invoke(
                FunctionName='userSNSnotifications',
                InvocationType='Event',
                Payload=json.dumps(lambda_payload),
            )
            return update_result
        else:
            raise HTTPException(status_code=404, detail=f"User ID of {user_id} not found")

    if (existing_user := mongodb_service["collection"].find_one({"_id": ObjectId(user_id)})) is not None:
        return existing_user

    raise HTTPException(status_code=404, detail=f"User ID of {user_id} not found")


@service.delete(
    "/users/{user_id}",
    response_description="Delete a user",
    response_model=SimpleResponseModel,
    response_model_by_alias=False
)
async def delete_user(user_id: str):
    user = mongodb_service["collection"].find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found")

    delete_result = mongodb_service["collection"].delete_one({"_id": ObjectId(user_id)})

    if delete_result.deleted_count == 0:
        raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found")

    lambda_payload = {
        "action": "delete",
        "subject": f"User {user_id} has been deleted",
        "user_info": await build_user_info(user)
    }

    lambda_client.invoke(
        FunctionName='userSNSnotifications',
        InvocationType='Event',
        Payload=json.dumps(lambda_payload),
    )
    return {"message": "User deleted successfully"}


@service.get(
    "/users/{user_id}/events",
    response_description="Returns user's event records by user id",
    response_model=UserEventModel,
    response_model_by_alias=False
)
async def find_user_event_by_id(user_id: str):
    user = mongodb_service["collection"].find_one(
        {"_id": ObjectId(user_id)},
        {"event_organizer_list": 1, "event_participation_list": 1}
    )

    if user is None:
        raise HTTPException(status_code=404, detail=f"User ID of {user_id} not found")

    return user


@service.get(
    "/users/{user_id}/groups",
    response_description="Returns user's group records by user id",
    response_model=UserGroupModel,
    response_model_by_alias=False,
)
async def find_user_group_by_id(user_id: str):
    user = mongodb_service["collection"].find_one(
        {"_id": ObjectId(user_id)},
        {"group_organizer_list": 1, "group_member_list": 1}
    )

    if user is None:
        raise HTTPException(status_code=404, detail=f"User ID of {user_id} not found")

    return user


@service.get(
    "/users/{user_id}/friends",
    response_description="Returns user's friends by user id",
    response_model=UserGroupModel,
    response_model_by_alias=False,
)
async def find_user_friends_by_id(user_id: str):
    user = mongodb_service["collection"].find_one(
        {"_id": ObjectId(user_id)},
        {"friends": 1}
    )

    if user is None:
        raise HTTPException(status_code=404, detail=f"User ID of {user_id} not found")

    return user


@service.get(
    "/users/{user_id}/comments",
    response_description="Returns user's comment records by user id",
    response_model=None,
    response_model_by_alias=False,
)
async def find_user_comment_by_id(user_id: str):
    # TODO: To be integrated with the group and event microservice
    pass


@service.post("/token")
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user = authenticate_user_by_username(form_data.username, form_data.password)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    data_for_token = {"username": user["username"],
                      "email": user["email"]}
    access_token = create_access_token(
        data=data_for_token, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@service.get(
    "/google-sso-token",
    response_description="SSO login user",
    response_model_by_alias=False
)
async def google_sso_access_token(user: OpenID = Depends(get_logged_user)):
    try:
        # Return the user profile if the user already exists
        user_result = await find_user_by_email(user.email)

    except HTTPException:
        # Create a new user based on the Google SSO user profile
        new_username = generate_username(1)[0]
        while len(list(mongodb_service["collection"].find({"username": new_username}).limit(1))) == 1:
            new_username = generate_username(1)[0]

        new_user = {
            "username": new_username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "contact": "",
            "location": "",
            "interests": [],
            "age": None,
            "gender": "",
            "friends": [],
            "group_member_list": [],
            "group_organizer_list": [],
            "event_organizer_list": [],
            "event_participation_list": [],
            "password": ''.join(random.choices(string.ascii_letters + string.digits, k=20))
        }

        user_result = await create_user(UserWithPwd(**new_user))

    # Create a JWT token for normal TeamUP login
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    data_for_token = {"username": user_result["username"],
                      "email": user_result["email"]}
    access_token = create_access_token(
        data=data_for_token, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@service.get(
    "/logout-page",
    response_description="Logout screen",
)
async def logout_success():
    return {"Status": "Logout success"}


if __name__ == '__main__':
    uvicorn.run(service, host="0.0.0.0", port=8000)
