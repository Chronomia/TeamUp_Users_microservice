import logging
import os

import certifi as certifi
from pymongo import MongoClient

ATLAS_URI = os.environ.get('ATLAS_URI')
logger = logging.getLogger(__name__)

mongodb_service = {"client": MongoClient(ATLAS_URI, tlsCAFile=certifi.where())}
mongodb_service["db"] = mongodb_service["client"]["TeamUp"]
mongodb_service["collection"] = mongodb_service["db"]["Users"]


for user in mongodb_service["collection"].find():
    if 'interests' in user and isinstance(user['interests'], str):
        interests_list = user['interests'].split(', ')
        mongodb_service["collection"].update_one({'_id': user['_id']}, {'$set': {'interests': interests_list}})
