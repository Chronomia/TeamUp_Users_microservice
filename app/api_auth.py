import os

from fastapi import HTTPException, Security
from fastapi.security import api_key

api_key_header = api_key.APIKeyHeader(name="api_key")
API_KEY = os.environ.get("API_KEY")


async def validate_api_key(key: str = Security(api_key_header)):
    if key != API_KEY:
        raise HTTPException(
            status_code=401, detail="Unauthorized"
        )
