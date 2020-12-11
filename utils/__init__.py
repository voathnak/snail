import json
import os
import re
from functools import reduce


email_regex = '^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+([.]\w{2,10})+$'


def check_email(email):
    if re.search(email_regex, email):
        return True
    else:
        return False


def log_event(event):
    print("#" * 100)
    event_json = json.dumps(event, indent=4, sort_keys=False)
    print("#---- event:", event_json)
    print("#" * 100)


def log_event_body(event):
    body = json.loads(event.get("body"))
    print("#" * 100)
    event_json = json.dumps(body, indent=4, sort_keys=False)
    print("#---- event-body:", event_json)
    print("#" * 100)


def response(status_code, body=None):
    return {
        'statusCode': status_code,
        'body': body,
        "headers": {
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": True,
        }
    }


class OdooServerConnection:
    def __init__(self, users):
        self.status = 200
        self.fail_message = ""
        self.login_detail_keys = ['odoo_host', 'odoo_db', 'odoo_login', 'odoo_password']
        self.login_details = []

        if not users:
            self.fail_message = "No primary account found"
            self.status = 403
        elif not reduce(lambda a, b: a * b, [x in users[0].user_settings for x in self.login_detail_keys]):
            self.status = 403
            self.fail_message = "Login details are required"
        else:
            self.login_details = [users[0].user_settings.get(detail) for detail in self.login_detail_keys]

    def __bool__(self):
        return self.status == 200
