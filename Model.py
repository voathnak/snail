#######################################################################################################################
import decimal
import json
import logging
import os
import uuid
from datetime import datetime

import pymongo as pymongo
from bson import ObjectId

from snail.constants.http_status_code import BAD_REQUEST
from snail.utils import response


connection_url = os.environ['MONGODB_URI']
dbname = os.environ["DB_NAME"]
client = pymongo.MongoClient(connection_url)

db = client[dbname]

# db = client.test

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class CoreModel:
    _required_fields = []
    _output_id = True

    def __init__(self):
        self._has_record = False
        self._collection = db[self.__getattribute__("_collection_name")]
        self._required_fields = self.__getattribute__("_required_fields")
        self._error_response = None

    def create(self, values):

        timestamp = str(datetime.utcnow().timestamp())

        for field in self.__getattribute__("_required_fields"):
            if not values.get(field, False):
                error_message = "field: {} is required!".format(field)
                logging.error(error_message)
                self._error_response = response(BAD_REQUEST, {"error": error_message})
                return None

        item = {
                'createdAt': timestamp,
                'updatedAt': timestamp,
        }

        if values.get('_id', False):
            item.update({'_id': str(uuid.uuid1())})

        item.update(values)

        self._has_record = True
        # write the record to the database
        creating_doc = self._collection.insert_one(item)
        if creating_doc:
            self.get(creating_doc.inserted_id)
            return self

    def _fetch_error(self, e):
        logger.error("Getting specific record from {}".format(self._collection))
        logger.error(e)
        raise

    def recorded(self, record):
        if record:
            self._has_record = True
            self._load(record)
            return self
        else:
            self._has_record = False
            return None

    def get_one(self):
        try:
            record = self._collection.find_one()

        except Exception as e:
            self._fetch_error(e)
        return self.recorded(record)

    def get(self, _id):
        try:
            record = self._collection.find_one({"_id": ObjectId(_id)})

        except Exception as e:
            self._fetch_error(e)
        return self.recorded(record)

    def list(self):
        try:
            records = self._collection.find()

        except Exception as e:
            logger.error("Getting records from {}".format(self._collection))
            logger.error(e)
            raise
        if records:
            self._has_record = True
            return [self._from_dict(record) for record in records]
        else:
            self._has_record = False
            return []

    def update(self, _id, values):
        try:
            self._collection.update_one({"_id": ObjectId(_id)}, {"$set": values})
        except Exception as e:
            logger.error("Updating records from {}".format(self._collection))
            logger.error(e)
            raise
        return self.get(_id)

    def delete(self, _id):
        # Todo: will need to implement deleting multiple records
        try:
            self._collection.delete_one({"_id": ObjectId(_id)})

        except Exception as e:
            logger.error("Deleting records from {}".format(self._collection))
            logger.error(e)
            raise

        return True

    def dict_datatype(self, dictionary):
        def _iterate(data):
            for key, attr in data.items():
                if isinstance(attr, decimal.Decimal):
                    attr = float(attr)
                elif isinstance(attr, dict):
                    attr = self.dict_datatype(attr)
                yield key, attr

        return dict(_iterate(dictionary))

    def _load(self, item):
        for key, value in item.items():
            if isinstance(value, dict):
                value = self.dict_datatype(value)
            if key[0] != "_" or key == "_id":
                self.__setattr__(key, value)

    def _from_dict(self, record_dict):
        record = self.__class__()
        for key, value in record_dict.items():
            if key == "_id":
                record.__setattr__(key, str(value))
            else:
                record.__setattr__(key, value)
            if isinstance(value, decimal.Decimal):
                value = float(value)
            elif isinstance(value, dict):
                value = self.dict_datatype(value)
            record.__setattr__(key, value)
        return record

    def __iter__(self):
        iters = dict((x, y) for x, y in self.__dict__.items() if x[:1] != '_')
        for name, attr in iters.items():
            yield name, attr

    def __setattr__(self, name, value):
        if name == 'createdAt' or name == 'updatedAt':
            self.__dict__[name] = datetime.fromtimestamp(float(value)).strftime("%b %d %Y %H:%M:%S")
        elif name == '_id' and self._output_id:
            self.id = str(value)
            self.__dict__[name] = value
        else:
            self.__dict__[name] = value

    def __bool__(self):
        return self._has_record

#######################################################################################################################
