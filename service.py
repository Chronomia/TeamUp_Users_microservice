import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

import boto3
import certifi
import uvicorn
from botocore.exceptions import ClientError
from bson import ObjectId
from fastapi import FastAPI, Body, HTTPException, Security, Depends
from fastapi.security import APIKeyCookie
from fastapi_sso.sso.base import OpenID
from jose import jwt
from pydantic import BaseModel
from pymongo import MongoClient, ReturnDocument
from random_username.generate import generate_username
from starlette import status

from google_auth import auth_app
from app.user import UserModel, UserGroupModel, UserEventModel, UpdateUserModel, UserCollection

ATLAS_URI = os.environ.get('ATLAS_URI')
SECRET_KEY = os.environ.get('SECRET_KEY')
AWS_ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.environ.get('AWS_SECRET_KEY')

logger = logging.getLogger(__name__)
mongodb_service = {}

TOPIC_ARN = os.environ.get('TOPIC_ARN')
sns_client = boto3.client(
    'sns',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name='us-east-1'
)


class SimpleResponseModel(BaseModel):
    message: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    mongodb_service["client"] = MongoClient(ATLAS_URI, tlsCAFile=certifi.where())
    mongodb_service["db"] = mongodb_service["client"]["TeamUp"]
    mongodb_service["collection"] = mongodb_service["db"]["Users"]
    yield
    mongodb_service.clear()


async def get_logged_user(cookie: str = Security(APIKeyCookie(name="token"))) -> OpenID:
    try:
        claims = jwt.decode(cookie, key=SECRET_KEY, algorithms=["HS256"])
        return OpenID(**claims["pld"])
    except Exception as error:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials") from error


service = FastAPI(lifespan=lifespan)
service.mount("/auth", auth_app)


def publish_to_sns(subject, message):
    message_json = json.dumps(message)
    try:
        if "_id" in message:
            message["_id"] = str(message["_id"])
        response = sns_client.publish(
            TopicArn=TOPIC_ARN,
            Subject=subject,
            Message=message_json
        )
        return response
    except ClientError as e:
        print(f"Error publishing to SNS: {e}")
        raise


async def build_user_info(user):
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
async def create_user(user: UserModel = Body(...)):
    if len(list(mongodb_service["collection"].find({"username": user.username}).limit(1))) == 1:
        raise HTTPException(status_code=409, detail=f"Username {user.username} is already taken")

    if len(list(mongodb_service["collection"].find({"email": user.email}).limit(1))) == 1:
        raise HTTPException(status_code=409, detail=f"Email {user.email} is already registered")

    new_user = mongodb_service["collection"].insert_one(
        user.model_dump(by_alias=True, exclude={"id"})
    )

    created_user = mongodb_service["collection"].find_one(
        {"_id": new_user.inserted_id}
    )

    user_info = await build_user_info(user)

    publish_to_sns(f"User {created_user['_id']} inserted successfully", user_info)
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
    response_model=UserModel,
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
    response_model=UserModel,
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
    response_model=UserModel,
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
    "/users/{user_id}/update",
    response_description="Update a user's profile by id",
    response_model=UserModel,
    response_model_by_alias=False,
)
async def update_user_profile(user_id: str, user: UpdateUserModel = Body(...)):
    current_user = mongodb_service["collection"].find_one({"_id": ObjectId(user_id)})
    if len(current_user) == 1 and str(current_user[0]["_id"]) != user_id:
        print(list(mongodb_service["collection"].find({"username": user.username}).limit(1)))
        raise HTTPException(status_code=409, detail=f"Username {user.username} is already taken")

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
            message = {
                'details': changes
            }

            publish_to_sns(f"User data updated for user_id {user_id}", message)
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

    user_info = await build_user_info(user)

    publish_to_sns(f"User {user_id} has been deleted", user_info)
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
    "/users/{user_id}/comments",
    response_description="Returns user's comment records by user id",
    response_model=UserModel,
    response_model_by_alias=False,
)
async def find_user_comment_by_id(user_id: str):
    # TODO: To be integrated with the group and event microservice
    user = mongodb_service["collection"].find_one(
        {"_id": ObjectId(user_id)}
    )

    if user is None:
        raise HTTPException(status_code=404, detail=f"User ID of {user_id} not found")

    return user


@service.get(
    "/protected",
    response_description="SSO login user",
    response_model=UserModel,
    response_model_by_alias=False
)
async def protected_endpoint(user: OpenID = Depends(get_logged_user)):
    try:
        user_result = await find_user_by_email(user.email)
        return user_result
    except HTTPException:
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
            "event_participation_list": []
        }

        user_result = await create_user(UserModel(**new_user))
        return user_result


@service.get(
    "/logout-page",
    response_description="Logout screen",
)
async def logout_success():
    return {"Status": "Logout success"}


if __name__ == '__main__':
    uvicorn.run(service, host="0.0.0.0", port=8000)
