import json
import yaml
import os
import subprocess

SUBJECT = "Vacation Calendar Sync Error Notification"

path = os.getenv('AZURE_GRAPH_AUTH')
with open(path, 'r') as file:
    dictionary = yaml.safe_load(file)
    recipient_email = dictionary['recipient_email']

def send_mail_using_host(message):
    with open("email.txt", 'w') as f:
        email = [f"To: {recipient_email}\n", f"Subject: {SUBJECT}\n", f"{message}\n"]
        f.writelines(email)
    
    subprocess.run(f"sendmail {recipient_email} < email.txt", shell=True)

        

def send_email(user_client, access_token, message):

    toRecipients = []
    
    recipient = {
        "emailAddress": {
        "address": recipient_email
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

