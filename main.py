import logging
from contextlib import asynccontextmanager

import uvicorn
from bson import ObjectId
from fastapi import FastAPI, Body, HTTPException
from pymongo import MongoClient, ReturnDocument
from starlette import status

from src.User import UserModel, UserGroupModel, UserEventModel, UpdateUserModel, UserCollection

ATLAS_URI = "mongodb+srv://ll3598:mb3raWSgGgaeSg6T@teamup.zgtc4hf.mongodb.net/?retryWrites=true&w=majority"
logger = logging.getLogger(__name__)
mongodb_service = {}


@asynccontextmanager
async def lifespan(service: FastAPI):
    mongodb_service["client"] = MongoClient(ATLAS_URI)
    mongodb_service["db"] = mongodb_service["client"]["TeamUp"]
    mongodb_service["collection"] = mongodb_service["db"]["Users"]
    yield
    mongodb_service.clear()


app = FastAPI(lifespan=lifespan)


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

    return created_user


@app.get(
    "/users/",
    response_description="List all users with pagination",
    response_model=UserCollection,
    response_model_by_alias=False,
)
async def list_all_users(page: int = 1, limit: int = 5):
    items = mongodb_service["collection"].find().skip((page - 1) * limit).limit(limit)
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
    existing_username = list(mongodb_service["collection"].find({"username": user.username}).limit(1))
    if len(existing_username) == 1 and str(existing_username[0]["_id"]) != user_id:
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

        if update_result is not None:
            return update_result
        else:
            raise HTTPException(status_code=404, detail=f"User ID of {user_id} not found")

    if (existing_user := mongodb_service["collection"].find_one({"_id": ObjectId(user_id)})) is not None:
        return existing_user

    raise HTTPException(status_code=404, detail=f"User ID of {user_id} not found")


@app.get(
    "/users/{user_id}/events",
    response_description="Returns user's event records by user id",
    response_model=UserEventModel,
    response_model_by_alias=False,
)
async def find_use_event_by_id(user_id: str):
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
