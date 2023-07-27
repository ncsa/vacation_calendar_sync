import json
import yaml
import os
import os.path
import requests
import ldap3
from datetime import datetime
import logging

SUBJECT = "Vacation Calendar Sync Error Notification"
logger = logging.getLogger("__main__." + __name__)

def init_device_code_flow(app, scopes):
    """
    Start of the Microsoft init device flow process

    Args:
        app (PublicClientApplication object): the public client for the msal library
        scope (list): a list consisting of the Azure permissions
    
    Returns:
        json: json object of the events within/overlap between the start and end date
    """

    flow = app.initiate_device_flow(scopes=scopes)
    print(flow["message"])
    result = app.acquire_token_by_device_flow(flow)
    return result


def acquire_access_token(app, scopes):
    """
    Acquire the access token using the MSAL library

    Args:
        app (PublicClientApplication object): the public client for the msal library
        scope (list): a list consisting of the Azure permissions
    
    Returns:
        str: the access token for the Microsoft Graph API
    """

    collection_path = os.getenv('VCS_COLLECTION_PATH')
    # Note access_token usually lasts for a little bit over an hour
    result = None
    accounts = app.get_accounts()
    if accounts:
        # If accounts exist, that means that it is an iteration, since system rebooting and first time running won't have acccount 
        logger.debug("Tokens found in cache")
        result = app.acquire_token_silent(scopes, accounts[0])
    elif os.path.isfile(collection_path + '/token.txt'):
        # if the token file exist, then read the refresh token and use it to acquire the access_token 
        with open(collection_path + "/token.txt", "r") as file:
            logger.debug("Refresh token found")
            refresh_token = file.readline()
    
        result = app.acquire_token_by_refresh_token(refresh_token, scopes)
    
    if not result or "error" in result:
        result = init_device_code_flow(app, scopes)

    if "access_token" in result:
        with open(collection_path + "/token.txt", "w") as file:
            file.write(result["refresh_token"])
            logger.debug("Writing new refresh token into token")
        return result["access_token"]
    else:
        logger.error(result.get("error"))
        logger.error(result.get("error_description"))
        logger.error(result.get("correlation_id"))

def get_configurations():
    """
    Retrieves the configurations from the vacation_calendar_sync_config file located at VCS_CONFIG

    Returns:
        dict: the configs as a dict
    
    """
    # Created ENV variable using docker's ENV command in Dockerfile
    path = os.getenv('VCS_CONFIG')
    with open(path, 'r') as file:
        return yaml.safe_load(file)
        
def send_email(message, access_token):
    config = get_configurations()
    recipient_email = config['recipient_email']
    
    """
    Sends an email to a list of recipients
    
    Args:
        message (str): the message that is contained in the email
        access_token (str): the token used make calls to the Microsoft Graph API as part of the Oauth2 Authorization code flow
    """

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
            # "toRecipients": [recipient]
           "toRecipients": [
            {
                "emailAddress": {
                "address": recipient_email
                }
            }
            ]
        },
        "saveToSentItems": "false"
    }
    response = requests.post(endpoint, data=json.dumps(payload), headers=header)

    if (response.status_code != 202):
        logger.error(response.json())
        raise Exception()

    # TODO: consider a case if the status code isn't 202
            

def get_email_list(group_name, update_interval, current_email_list = None, last_updated = None):
    """
    Retrieves the email list of the members in group_name

    Args:
        group_name (str): The name of the specified group
        current_email_list (list): The previously held list of emails
        last_updated (datetime object): The last time the current_email_list was updated
    
    Returns:
        A list of emails from the specified group_name
    """
    
    if not last_updated or divmod((last_updated - datetime.today()).total_seconds(), 60)[0] >= update_interval:
        last_updated = datetime.today()
        current_email_list = get_email_list_from_ldap(group_name)
    return (last_updated, current_email_list)
    
def get_email_list_from_ldap(group_name):
    """
    Retrieves the email list of the members in group_name using ldap server
    
    Args:
        group_name (str): The name of the specified group
    
    Returns:
        A list of emails from the specified group_name using ldap server
    """
    ldap_server = "ldaps://ldap1.ncsa.illinois.edu"  # Replace with your LDAP server
    
    ldap_user = None
    ldap_password = None

    search_base = 'dc=ncsa,dc=illinois,dc=edu'
    
    search_scope = ldap3.SUBTREE
    attributes = ldap3.ALL_ATTRIBUTES

    group_list = [
        group_name
    ]

    with ldap3.Connection(ldap_server, ldap_user, ldap_password) as conn:
        if not conn.bind():
            logger.error("Error: Could not bind to LDAP server")
        else:
            for group_name in group_list:
                search_filter = f"(cn={group_name})"
                #print("search_filter: " + search_filter)
                result = conn.search(search_base, search_filter, search_scope, attributes=attributes)
                if not result:
                    logger.error(f"Error: Could not find group {group_name}")
                else:
                    members = [ m.split(',')[0].split('=')[1] for m in conn.entries[0].uniqueMember ]
                
            emails = []
            for member in members:    
                result = conn.search(search_base, f"(uid={member})", search_scope, attributes=attributes)
                if not result:
                    logger.error(f"Error: Could not find member with uid {member}")
                else:
                    emails.append(str(conn.entries[0].mail))

            temp_emails = []
            logger.debug(f"{len(emails)} emails were found")
            for email in emails:
                if '@illinois.edu' in email:
                    temp_emails.append(email)
                else:
                    logger.warning(f"{email} is not a illinois affiliated email")
            return temp_emails
        

