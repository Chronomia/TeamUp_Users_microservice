from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import uvicorn

app = FastAPI()

# Sample data
users = [
    {'id': 1, 'name': 'Alice'},
    {'id': 2, 'name': 'Bob'}
]


class User(BaseModel):
    id: int
    name: str


@app.get("/")
def read_root():
    return {"message": "Hello, World"}


@app.get("/api/users", response_model=List[User])
def get_users():
    return users


@app.get("/api/users/{user_id}", response_model=User)
def get_user(user_id: int):
    user = next((u for u in users if u['id'] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.post("/api/users", response_model=User)
def create_user(user: User):
    users.append(user.model_dump())
    return user


@app.get("/api/users/{user_id}/events")
def get_user_events(user_id: int):
    # Sample data, you'd replace this with a query to your data source
    events = [{'id': 1, 'name': 'Event A'}, {'id': 2, 'name': 'Event B'}]
    return events


@app.get("/api/users/{user_id}/groups")
def get_user_groups(user_id: int):
    # Sample data, replace with a query to your data source
    groups = [{'id': 1, 'name': 'Group X'}, {'id': 2, 'name': 'Group Y'}]
    return groups


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
