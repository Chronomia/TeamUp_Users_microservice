from typing import List, Optional, Annotated

from bson import ObjectId
from pydantic import BaseModel, Field, ConfigDict, EmailStr, BeforeValidator

PyObjectId = Annotated[str, BeforeValidator(str)]


class UserModel(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    username: str = Field(..., min_length=3, max_length=30)
    first_name: str = Field(...)
    last_name: str = Field(...)
    email: EmailStr = Field(...)
    contact: str = Field(...)
    location: str = Field(...)
    interests: List[str] = Field(...)
    age: int = Field(..., ge=13, le=150)
    gender: str = Field(...)
    friends: List[str] = Field([])
    group_member_list: List[str] = Field(...)
    group_organizer_list: List[str] = Field(...)
    event_organizer_list: List[str] = Field(...)
    event_participation_list: List[str] = Field(...)
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "username": "username@123",
                "first_name": "Your First Name",
                "last_name": "Your Last Name",
                "email": "name@example.com",
                "contact": "(123) 456-7890",
                "location": "New York, NY",
                "interests": ["Baseball", "Football", "Cycling"],
                "age": 25,
                "gender": "Male",

            }
        },
    )


class UserGroupModel(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    group_member_list: List[str] = Field(...)
    group_organizer_list: List[str] = Field(...)


class UserEventModel(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    event_organizer_list: List[str] = Field(...)
    event_participation_list: List[str] = Field(...)


class UpdateUserModel(BaseModel):
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    contact: Optional[str] = None
    location: Optional[str] = None
    interests: Optional[List[str]] = None
    age: Optional[int] = None
    group_member_list: Optional[List[str]] = None
    group_organizer_list: Optional[List[str]] = None
    event_organizer_list: Optional[List[str]] = None
    event_participation_list: Optional[List[str]] = None
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "username": "username@123",
                "first_name": "Your First Name",
                "last_name": "Your Last Name",
                "contact": "(123) 456-7890",
                "location": "New York, NY",
                "interests": ["Baseball", "Football", "Cycling"],
                "age": 25
            }
        },
    )


class UserCollection(BaseModel):
    users: List[UserModel]
