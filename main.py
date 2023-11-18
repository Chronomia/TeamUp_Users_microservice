import json
import logging
from contextlib import asynccontextmanager

import certifi
import uvicorn
from bson import ObjectId
from fastapi import FastAPI, Body, HTTPException
from pymongo import MongoClient, ReturnDocument
from starlette import status
from typing import Optional

from src.User import UserModel, UserGroupModel, UserEventModel, UpdateUserModel, UserCollection

from pydantic import BaseModel

import boto3
from botocore.exceptions import ClientError

ATLAS_URI = "mongodb+srv://ll3598:mb3raWSgGgaeSg6T@teamup.zgtc4hf.mongodb.net/?retryWrites=true&w=majority"
logger = logging.getLogger(__name__)
mongodb_service = {}

topic_arn = "arn:aws:sns:us-east-1:083303715298:UserUpdatesTopic"
sns_client = boto3.client(
    'sns',
    aws_access_key_id='AKIARGZKJ2HRBHMCTSOW',
    aws_secret_access_key='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',
    region_name='us-east-1'
)

@asynccontextmanager
async def lifespan(service: FastAPI):
    mongodb_service["client"] = MongoClient(ATLAS_URI, tlsCAFile=certifi.where())
    mongodb_service["db"] = mongodb_service["client"]["TeamUp"]
    mongodb_service["collection"] = mongodb_service["db"]["Users"]
    yield
    mongodb_service.clear()


app = FastAPI(lifespan=lifespan)

def publish_to_sns(subject, message):
    message_json = json.dumps(message)
    try:
        if "_id" in message:
            message["_id"] = str(message["_id"])
        response = sns_client.publish(
            TopicArn=topic_arn,
            Subject = subject,
            Message=message_json
        )
        return response
    except ClientError as e:
        print(f"Error publishing to SNS: {e}")
        raise

@app.get("/")
async def index():
    return {"status": "online"}


@app.post(
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
    user_info = {
        "username":created_user['username'],
        "first_name":created_user['first_name'],
        "last_name":created_user['last_name'],
        "email":created_user['email'],
        "contact":created_user['contact'],
        "location":created_user['location'],
        "interests":created_user['interests'],
        "age":created_user['age'],
        "gender":created_user['gender'],
    }

    publish_to_sns(f"User {created_user['_id']} inserted successfully", user_info)
    return created_user


@app.get(
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

@app.get(
    "/users/{user_id}",
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


@app.put(
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


class SimpleResponseModel(BaseModel):
    message: str
    
@app.delete(
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
    user_info = {
        "username":user['username'],
        "first_name":user['first_name'],
        "last_name":user['last_name'],
        "email":user['email'],
        "contact":user['contact'],
        "location":user['location'],
        "interests":user['interests'],
        "age":user['age'],
        "gender":user['gender'],
    }

    publish_to_sns(f"User {user_id} has been deleted", user_info)
    return {"message": "User deleted successfully"}

@app.get(
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


@app.get(
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


@app.get(
    "/users/{user_id}/comments",
    response_description="Returns user's comment records by user id",
    response_model=UserModel,
    response_model_by_alias=False,
)
async def find_user_comment_by_id(user_id: str):
    user = mongodb_service["collection"].find_one(
        {"_id": ObjectId(user_id)}
    )

    if user is None:
        raise HTTPException(status_code=404, detail=f"User ID of {user_id} not found")

    return user

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
