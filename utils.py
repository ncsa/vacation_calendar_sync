import json
import yaml
import os
import sys

SUBJECT = "Vacation Calendar Sync Error Notification"

path = os.getenv('AZURE_GRAPH_AUTH')
with open(path, 'r') as file:
    dictionary = yaml.safe_load(file)
    email_addresses = dictionary['recipient_emails']

def send_email(user_client, access_token, message):

    toRecipients = []
    for email in email_addresses:
        recipient = {
            "emailAddress": {
            "address": email
            }
        }
        toRecipients.append(recipient)

    endpoint = "https://graph.microsoft.com/v1.0/me/sendMail"

    header = {
        "Authorization": str(access_token),
        "Content-Type": "application/json"
    }

    payload = {
        "message": {
            "subject": SUBJECT,
            "body": {
            "contentType": "Text",
            "content": message
            },
            "toRecipients": toRecipients,
            "ccRecipients": [
            {
                "emailAddress": {
                "address": toRecipients
                }
            }
            ]
        },
        "saveToSentItems": "false"
    }

    response = user_client.post(endpoint, data=json.dumps(payload), headers=header)

def report_unhealthy():
    '''
    A fatal error has occured
    '''
    sys.exit(1)

def report_healthy():
    '''
    No error has occured
    '''
    sys.exit(0)