import logging

import certifi as certifi
import collection as collection
from pymongo import MongoClient

ATLAS_URI = "mongodb+srv://ll3598:mb3raWSgGgaeSg6T@teamup.zgtc4hf.mongodb.net/?retryWrites=true&w=majority"
logger = logging.getLogger(__name__)
mongodb_service = {}

mongodb_service["client"] = MongoClient(ATLAS_URI, tlsCAFile=certifi.where())
mongodb_service["db"] = mongodb_service["client"]["TeamUp"]
mongodb_service["collection"] = mongodb_service["db"]["Users"]


for user in mongodb_service["collection"].find():
    if 'interests' in user and isinstance(user['interests'], str):
        interests_list = user['interests'].split(', ')
        mongodb_service["collection"].update_one({'_id': user['_id']}, {'$set': {'interests': interests_list}})
