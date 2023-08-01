from datetime import datetime
import json
import datetime
from datetime import timedelta 
import logging
import math
import utils
import requests
from SimpleEvent import SimpleEvent

MAX_REQUESTS_PER_BATCH = 20

# This logger is a child of the __main__ logger located in OutlookCalendar.py
logger = logging.getLogger("__main__." + __name__)

def get_shared_calendar_id(shared_calendar_name, access_token):
    """
    Retrieves the calendar of the specified calendar

    Args:
        shared_calendar_name (str): the name of the user specified calendar
        access_token (str): the token used make calls to the Microsoft Graph API 
        as part of the Oauth2 Authorization code flow
    
    Returns:
        str: the id of the user specified calendar
    """

    header = {
        'Authorization': str(access_token),
        'Content-Type': 'application/json'
    }
    endpoint = "https://graph.microsoft.com/v1.0/me/calendars"
    response = requests.get(endpoint, headers=header)
    
    if response.status_code != 200:
        message = f"Unable to connect to the {endpoint} endpoint to retrieve {shared_calendar_name}"
        logger.error(response.json())
        utils.send_email(message, access_token)
        raise ConnectionError(message)

    # Loop through all the calendars available to the user, and find the one indicated in the yaml file and retrieve its calendar ID
    for calendar in response.json()['value']:
        if calendar['name'] == shared_calendar_name:
            return calendar['id']
    
    message = f"{shared_calendar_name} was not found"
    logger.error(response.json())
    utils.send_email(message, access_token)
    raise KeyError(message)

def get_shared_calendar(shared_calendar_id, start_date, end_date, access_token):
    """
    Retrieves a json object of the shared calendar events \
    between the start_date to end_date (including start_date and excluding end_date)

    Args:
        start_date (datetime): the start date of timeframe being updated
        end_date (dateime):  the end date of timeframe being updated
        access_token (str): the token used make calls to the Microsoft Graph API \
        as part of the Oauth2 Authorization code flow
    
    Returns:
        json: json object of the events between the start and end date
        (including start_date and excluding end_date)
    """

    start_date = str(start_date.date())
    end_date = str(end_date.date())
    
    header = {
        'Authorization': str(access_token),
        'Prefer': "outlook.timezone=\"Central Standard Time\""
    }

    # If succcesful, the response.json() includes the events that occur within the inverval of start_date and end_date 
    # Include events that:
    # start between start_date and end_date (includes start_date)
    # The exception is if the event start on the end_date. That event will not be included in the response.json()

    endpoint = 'https://graph.microsoft.com/v1.0/me/calendars/' + shared_calendar_id +'/events?$select=subject,body,start,end,showAs&$top=100&$filter=start/dateTime ge ' + '\''+ start_date + '\'' + ' and start/dateTime lt ' + '\'' + end_date + '\''    
    response = requests.get(endpoint, headers=header)

    if (response.status_code != 200):
        message = f'Unable to retrieve shared calendar from {endpoint} endpoint'
        logging.error(response.json())
        utils.send_email(message)
        raise ConnectionError(message)

    return response.json()

def process_shared_calendar(shared_calendar, group_members):
    """
    Creates simple event objects using the the individual work calendars 

    Args:
        shared_calendar (json): json object of the events within/overlap between a specified start and end date for indvidual calendars
        group_members (list): A list of emails of the group members

    Returns: 
        tuple: A tuple containing a list of SimpleEvent objects and a list of the correspending event ids 
    """

    filtered_events = []
    event_ids = {}
    # the events can be multiday
    
    for event in shared_calendar['value']:

        if event['showAs'] != 'free': continue
        
        simple_event = SimpleEvent.create_event_for_shared_calendar(event, group_members)
        # Only valid events are returned as a simpleEvent object
        if simple_event == None: continue
        
        filtered_events.append(simple_event)
        event_date = str(simple_event.date.date())
        
        event_ids[simple_event.subject + event_date] = event['id']

    return (filtered_events, event_ids)

def update_shared_calendar(individual_calendars, shared_calendar, event_ids, shared_calendar_id, category_name, category_color, access_token):
    """
    Update the specified shared calendar by adding and deleting events from it

    Args:
        individual_calendars (list): a list of SimpleEvents from each member's calendars
        shared_calendar (list): a list of SimpleEvents obtained from the shared calendar
        event_ids (dict): a dictionary containing the ids of the events on the shared calendar
        shared_calendar_id (str): the associated id to the shared calendar
        category_name: the name of the category for the event
        category_color: the color of the category for the event
        access_token (str): the token used make calls to the Microsoft Graph API \
        as part of the Oauth2 Authorization code flow
    """
    
    individual_events  = set(create_tuple(individual_calendars))
    shared_events = set(create_tuple(shared_calendar))
    
    events_to_add = individual_events.difference(shared_events)
    events_to_delete = shared_events.difference(individual_events)
    
    batches = create_batches_for_adding_events(events_to_add, access_token, shared_calendar_id, category_name, category_color)
    post_batch(access_token, batches)

    batches, deleted_event_info = create_batches_for_deleting_events(events_to_delete, access_token, shared_calendar_id, event_ids)
    post_batch(access_token, batches, deleted_event_info)

def create_tuple(calendar):
    """
    Create a tuple for each events in calendar

    Args:
        calendar (list): a list of Simple Events
    
    Returns:
        A set of tuple events
    """

    events = []
    for event in calendar:
        event_tuple = (event.net_id, event.subject, str(event.date.date()))
        events.append(event_tuple)
    return tuple(events)

def create_batches_for_deleting_events(events, access_token, calendar_id, event_ids):
    """
    Create the batches for events being deleted from the shared_calendar using the format indicated by the Microsoft Graph API for batch

    Args:
        events (list): a list of tuples (net_id, subject, date). date has format of YYYY-MM-DD
        access_token: a token to use the services offered by the Microsoft Graph API
        calendar_id (str): the id of the specified shared calendar
        event_ids (dict): (net_id + subject) to event_id paring with event_id being the event id of the event

    Returns:
        A list of dictionaries (batches)
    """

    batches = []
    deleted_events_info = []
    
    num_of_batches = math.ceil(len(events) / MAX_REQUESTS_PER_BATCH)

    for i in range(num_of_batches):
        payload = {
            "requests": []
        }
        batches.append(payload)
    
    batch_counter = 0
    id_counter = 1

    event_info = {}
    for event in events:
        event_id = event_ids[event[1] + event[2]]

        request = {
            "id": str(id_counter),
            "url": '/me/calendars/' + calendar_id +'/events/' +  str(event_id),
            "method": "DELETE",
            "headers": {
                'Authorization': str(access_token)
            }
        }

        event_info[str(id_counter)] = event

        batches[batch_counter]["requests"].append(request)
        id_counter = id_counter + 1

        if (id_counter % 21 == 0):
            id_counter = 1
            batch_counter = batch_counter + 1
            deleted_events_info.append(event_info)
            event_info = {}

    deleted_events_info.append(event_info)
    return (batches, deleted_events_info)

def create_batches_for_adding_events(events, access_token, calendar_id, category_name, category_color):
    """
    Create the batches for events being added to the shared_calendar using the format indicated by the Microsoft Graph API for batch

    Args:
        events (list): a list of tuples (net_id, subject, date). date has format of YYYY-MM-DD
        access_token: a token to use the services offered by the Microsoft Graph API
        calendar_id (str): the id of the specified shared calendar
        category_name: the name of the category for the event
        category_color: the color of the category for the event

    Returns:
        A list of dictionaries (batches)
    """
    
    # A list of dictionaries
    category = get_category(access_token, category_name, category_color)
    batches = []
    num_of_batches = math.ceil(len(events) / MAX_REQUESTS_PER_BATCH) 
    
    for i in range(num_of_batches):
        payload = {
            "requests": []
        }
        batches.append(payload)

    batch_counter = 0
    id_counter = 1
    
    for event in events:
        start_date_time = event[2] + "T00:00:00.0000000"
        end_date = datetime.datetime.strptime(event[2],"%Y-%m-%d") + timedelta(days=1)
        end_date_time = end_date.strftime("%Y-%m-%d") + "T00:00:00.0000000"
        
        request = {
            "id": str(id_counter),
            "url": '/me/calendars/' + calendar_id +'/events',
            "method": "POST", # This could be different for for the delete function
            "body": {
                "subject": event[1],
                "showAs": "free",
                "start": {
                    "dateTime": start_date_time,
                    "timeZone": "Central Standard Time"
                },
                "end": {
                    "dateTime": end_date_time,
                    "timeZone": "Central Standard Time"
                },
                "categories": [category]
            },
            "headers": {
                "Authorization": access_token,
                'Content-type': 'application/json'
            }
        }
        batches[batch_counter]["requests"].append(request)

        id_counter = id_counter + 1
        if (id_counter % 21 == 0):
            id_counter = 1
            batch_counter = batch_counter + 1
    
    return batches

def check_add_response(batch, batch_responses, access_token):
    """
    Checks each of the add event calls from the batch

    Args:
        batch (dict): The request body to the Microsoft Graph batch endpoint
        batch_responses (dict): The response from the batch request
    """
    message = ""
    for response in batch_responses:
        
        if response["status"] == 201: # 201 is the response for Created
            logger.info("Event {subject} on {date} was successfully added".format(subject=response['body']['subject'], date=response['body']['start']['dateTime']))
        else:
            id = int(response['id'])
            subject = batch['requests'][id - 1]['body']['subject']
            date = batch['requests'][id - 1]['body']['start']['dateTime']
            logger.warning(f"Event {subject} on {date} was unccessfully added")
            logger.warning(f"Error: {response['body']['error']}")
            message = message + f"Event {subject} on {date} was unccessfully added\n"
    
    # if (len(message) != 0):
    #     utils.send_email(user_client, access_token, message)

def check_deleted_response(batch, batch_responses, access_token, info):
    """
    Checks each of the delete event calls from the batch

    Args:
        batch_responses (dict): The response from the batch request
        info (dict): a dictionary containing the events set to be deleted
    """

    for response in batch_responses:
        id = response["id"]
        event = info[id]
        if response["status"] == 204:
            logger.info(f"Event {event[1]} on {event[2]} was succesfully deleted")
        else:
            logger.warning(f"Event {event[1]} on {event[2]} was unsuccesfully deleted")
            logger.warning(f"Error: {response['body']['error']}")
    

def post_batch(access_token, batches, info=None):
    """
    Create the batches for events being deleted from the shared_calendar using the format indicated by the Microsoft Graph API for batch

    Args:
        user_client (Graph Client Object) : msgraph.core._graph_client.GraphClient 
        batches (list): A list of dictionaries (batches)
    """
    endpoint = "https://graph.microsoft.com/v1.0/$batch"
    
    header = {
        'Accept': 'application/json',
        'Content-type': 'application/json',
        "Authorization": access_token
    }
   
    for count, batch in enumerate(batches):
        response = requests.post(endpoint, data=json.dumps(batch), headers=header)
        #print(batch)
        if response.status_code != 200:
            message = "Unable to post batch \n" + str(response.json()["error"])
            #utils.send_email(user_client, access_token, message)
            logger.warning(message)
            logger.warning(response.json())
            continue

        if info:
            check_deleted_response(batch, response.json()["responses"], access_token, info[count])
        else:
            check_add_response(batch, response.json()["responses"], access_token)
        
def get_category(access_token, category_name, category_color):
    """
    Retrieves the user category master list, and finds the category_name in it. If not, the specified category will be created

    Args:
        access_token: a token to use the services offered by the Microsoft Graph API
        category_name: the name of the user specified category
        category_color: the color for the category if the category doesn't exist
    
    Returns:
        str: the name of the user specified category
    
    """

    endpoint = 'https://graph.microsoft.com/v1.0/me/outlook/masterCategories'
    headers = {
        'Authorization': access_token
    }
    
    response = requests.get(endpoint, headers=headers)
    if (response.status_code != 200):
        message = f"Unable to connect to {endpoint} endpoint to retrieve the masterCategories"
        logger.error(response.json())
        utils.send_email(message, access_token)
        raise ConnectionError(message)
    
    response = response.json()['value']
    
    for category in response:
        if category['displayName'] == category_name:
            return category_name
    
    return create_category(access_token, category_name, category_color)


def create_category(access_token, category_name, category_color):
    """
    Create the user specified category

    Args:
        access_token: a token to use the services offered by the Microsoft Graph API
        category_name: the name of the user specified category
        category_color: the color for the category if the category doesn't exist
    
    Returns:
        str: the name of the user specified category
    """

    endpoint = 'https://graph.microsoft.com/v1.0/me/outlook/masterCategories'
    headers = {
        'Authorization': access_token,
        'Content-Type': 'application/json'
    }
    # Can find the list of preset colors at https://learn.microsoft.com/en-us/graph/api/resources/outlookcategory?view=graph-rest-1.0
    body = {
        'displayName': category_name,
        'color': category_color
    }

    response = requests.post(endpoint, data=json.dumps(body), headers=headers)

    if response.status_code != 201:
        message = f"Unable to create {category_name}"
        logger.error(response.json())
        utils.send_email(message, access_token)
        raise ConnectionError(message)
    #print("category created")
    return category_name
    
    
