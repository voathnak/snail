import decimal
import json
import logging
import uuid
from datetime import datetime

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

from constants.http_status_code import BAD_REQUEST
from snippets.utils import response

dynamodb = boto3.resource('dynamodb')


class CoreModel:

    def __init__(self, table_name):
        self._table = dynamodb.Table(table_name)
        self._has_record = False

    def save(self, values):

        timestamp = str(datetime.utcnow().timestamp())


        for field in self.__getattribute__("_required_fields"):
            if not values.get(field, False):
                error_message = "field: {} is required!".format(field)
                logging.error(error_message)
                self.error_response = response(BAD_REQUEST, json.dumps({"error": error_message}))
                return None

        item = {
            'createdAt': timestamp,
            'updatedAt': timestamp,
        }

        if not values.get('itemId', False):
            item.update({'itemId': str(uuid.uuid1())})

        item.update(values)

        # write the record to the database
        record = self._table.put_item(Item=item)
        if record:
            self._load(item)
            self._has_record = True

        return self.__getattribute__('itemId')

    def get(self, itemId):
        try:
            item = self._table.get_item(Key={'itemId': itemId}).get('Item', [])
            if item:
                self._has_record = True
                self._load(item)
                return self
            else:
                self._has_record = False
        except ClientError as e:
            print(e.response['Error']['Message'])

    def search(self, attr, value):
        try:
            records = self._table.scan(FilterExpression=Attr(attr).eq(value)).get('Items', [])
        except Exception as e:
            print("#" * 100)
            print("###", "Getting records from", self._table)
            print("###", e)
            print("#" * 100)
            raise
        if records:
            self._has_record = True
            return [self._from_dict(record) for record in records]
        else:
            self._has_record = False
            return []

    def list(self):
        try:
            records = self._table.scan().get('Items', [])
        except Exception as e:
            print("#" * 100)
            print("###", "Getting records from", self._table)
            print("###", e)
            print("#" * 100)
            raise
        if records:
            self._has_record = True
            return [self._from_dict(record) for record in records]
        else:
            self._has_record = False
            return []

    def update(self, itemId, update_dict):
        try:
            item = self._table.get_item(Key={'itemId': itemId}).get('Item', [])

            if item:
                self._load(item)
                self._has_record = True
                changed = False
                update_dict.update({'updatedAt': str(datetime.utcnow().timestamp())})
                UpdateExpression = 'SET '
                ExpressionAttributeValues = {}
                ExpressionAttributeNames = {}
                for key, value in update_dict.items():
                    if key != "itemId" and key != 'createdAt':
                        if self.__getattribute__(key) != value:
                            changed = True
                            if isinstance(value, float):
                                value = decimal.Decimal(value)
                            UpdateExpression += "#{} = :{}, ".format(key[:-2], key)
                            ExpressionAttributeValues[":{}".format(key)] = value
                            ExpressionAttributeNames["#{}".format(key[:-2])] = key
                if changed:
                    updated_record = self._table.update_item(
                        Key={
                            'itemId': itemId
                        },
                        ConditionExpression='attribute_exists(itemId)',
                        UpdateExpression=UpdateExpression[:-2],
                        ExpressionAttributeValues=ExpressionAttributeValues,
                        ExpressionAttributeNames=ExpressionAttributeNames,
                        ReturnValues='ALL_NEW',
                    )
                    self._load(updated_record.get('Attributes'))
                    return updated_record.get('Attributes')
                return "No Changed"
            else:
                self._has_record = False
        except ClientError as e:
            print(e.response['Error']['Message'])

    def delete(self, itemId):
        try:
            self._table.delete_item(Key={'itemId': itemId})
            self._has_record = False
        except ClientError as e:
            print(e.response['Error']['Message'])

    def get_dict(self, itemId, fields=None):
        # to get dictionary instead of object
        # itemId: the record ID string to query item
        # fields: to specify the return dictionary key (leave it empty or None to get all fields)

        try:
            item = self._table.get_item(Key={'itemId': itemId}).get('Item', [])
            if item:
                self._has_record = True
                if fields:
                    return {key: item.get(key) for key in item if key in fields}
                return item
            else:
                self._has_record = False
        except ClientError as e:
            print(e.response['Error']['Message'])

    def dict_datatype(self, dictionary):
        def _iterate(dictionary):
            for key, attr in dictionary.items():
                if isinstance(attr, decimal.Decimal):
                    attr = float(attr)
                elif isinstance(attr, dict):
                    attr = self.dict_datatype(attr)
                yield key, attr

        return dict(_iterate(dictionary))

    def _load(self, item):
        for key, value in item.items():
            if isinstance(value, decimal.Decimal):
                value = float(value)
            elif isinstance(value, dict):
                value = self.dict_datatype(value)
            if key[0] != "_":
                self.__setattr__(key, value)

    def _from_dict(self, record_dict):
        record = self.__class__(self._table)
        for key, value in record_dict.items():
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
        else:
            self.__dict__[name] = value

    def __bool__(self):
        return self._has_record
