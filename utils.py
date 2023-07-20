import json
import yaml
import os
import subprocess
from msal import PublicClientApplication
import os.path
import requests

SUBJECT = "Vacation Calendar Sync Error Notification"

def init_device_code_flow(app, scopes):
    flow = app.initiate_device_flow(scopes=scopes)
    print(flow["message"])
    result = app.acquire_token_by_device_flow(flow)
    return result


def acquire_access_token(app, scopes):
    # Note access_token usually lasts for a little bit over an hour
    result = None
    accounts = app.get_accounts()
    if accounts:
        # If accounts exist, that means that it is an iteration, since system rebooting and first time running won't have acccount 
        print("Tokens found in cache")
        result = app.acquire_token_silent(scopes, accounts[0])
    elif os.path.isfile('token.txt'):
        # if the token file exist, then read the refresh token and use it to acquire the access_token 
        with open("token.txt", "r") as file:
            print("Refresh token found")
            refresh_token = file.readline()
    
        result = app.acquire_token_by_refresh_token(refresh_token, scopes)
    
    if not result or "error" in result:
        result = init_device_code_flow(app, scopes)

    if "access_token" in result:
        with open("token.txt", "w") as file:
            file.write(result["refresh_token"])
            print("Writing new refresh token into token")
        return result["access_token"]
    else:
        print(result.get("error"))
        print(result.get("error_description"))
        print(result.get("correlation_id"))


path = os.getenv('AZURE_GRAPH_AUTH')
with open(path, 'r') as file:
    dictionary = yaml.safe_load(file)
    recipient_email = dictionary['recipient_email']

def retrieve_from_yaml():
        required_attributes = ['client_id', 'tenant_id', 'scope', 'group_members', 'shared_calendar_name', 'logging_file_path', 'days_out', 'update_interval']

        # Created ENV variable using docker's ENV command in Dockerfile
        path = os.getenv('AZURE_GRAPH_AUTH')
        with open(path, 'r') as file:
            return yaml.safe_load(file)
            # for attribute in required_attributes:
            #     assert attribute in dictionary, f"{attribute} is not provided in microsoft_graph_auth.yaml"
            #     setattr(self, attribute, dictionary[attribute])

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





def get_groups_belonging_to_user(access_token):
    endpoint = "https://graph.microsoft.com/v1.0/me/memberOf"
    endpoint_three = "https://graph.microsoft.com/v1.0/groups?$filter=displayName eq 'NCSA-Org-ICI'"
    header = {
        "Authorization": str(access_token),
    }
    
    endpoint_two = "https://graph.microsoft.com/v1.0/groups?$select=displayName"
    response = requests.get(endpoint_two, headers=header)
    print(response.json())


