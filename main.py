import logging
from contextlib import asynccontextmanager

import uvicorn
from bson import ObjectId
from fastapi import FastAPI, Body, HTTPException
from pymongo import MongoClient
from starlette import status

from src.User import UserModel

ATLAS_URI = "mongodb+srv://ll3598:mb3raWSgGgaeSg6T@teamup.zgtc4hf.mongodb.net/?retryWrites=true&w=majority"
logger = logging.getLogger(__name__)
mongodb_service = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    mongodb_service["client"] = MongoClient(ATLAS_URI)
    mongodb_service["db"] = mongodb_service["client"]["TeamUp"]
    mongodb_service["collection"] = mongodb_service["db"]["Users"]
    yield
    mongodb_service.clear()


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def index():
    return {"message": "Hello, World"}


@app.post(
    "/users/",
    response_description="Add a new user",
    response_model=UserModel,
    status_code=status.HTTP_201_CREATED,
    response_model_by_alias=False
)
async def create_user(user: UserModel = Body(...)):
    new_user = mongodb_service["collection"].insert_one(
        user.model_dump(by_alias=True, exclude={"id"})
    )

    created_user = mongodb_service["collection"].find_one(
        {"_id": new_user.inserted_id}
    )

    return created_user


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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
