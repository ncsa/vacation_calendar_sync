from datetime import datetime
import json
import datetime
from datetime import timedelta 
import logging
import sys 
import time
import os 
import yaml
import math

MAX_REQUESTS_PER_BATCH = 20

# This logger is a child of the __main__ logger located in OutlookCalendar.py
logger = logging.getLogger("__main__." + __name__)
    
def update_shared_calendar(individual_calendars, shared_calendar, event_ids, shared_calendar_id, access_token, user_client):
    """
    Update the specified shared calendar by adding and deleting events from it

    Args:
        individual_calendars (list): A list of SimpleEvents from each member's calendars
        shared_calendar: A list of SimpleEvents obtained from the shared calendar
        shared_calendar_id (str): The associated id to the shared calendar
        access_token (int): The access token for the project
        user_client (GraphClient Object)
    """

    individual_events  = set(create_tuple(individual_calendars))
    shared_events = set(create_tuple(shared_calendar))
    
    events_to_add = individual_events.difference(shared_events)
    events_to_delete = shared_events.difference(individual_events)
    
    batches = create_batches_for_adding_events(events_to_add, access_token, shared_calendar_id)
    post_batch(user_client, access_token, batches)

    batches = create_batches_for_deleting_events(events_to_delete, access_token, shared_calendar_id, event_ids)
    post_batch(user_client, access_token, batches)
    

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
    
    num_of_batches = math.ceil(len(events) / MAX_REQUESTS_PER_BATCH)

    for i in range(num_of_batches):
        payload = {
            "requests": []
        }
        batches.append(payload)
    
    batch_counter = 0
    id_counter = 1

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

        batches[batch_counter]["requests"].append(request)
        id_counter = id_counter + 1

        if (id_counter % 21 == 0):
            id_counter = 1
            batch_counter = batch_counter + 1

    return batches

def create_batches_for_adding_events(events, access_token, calendar_id):
    """
    Create the batches for events being added to the shared_calendar using the format indicated by the Microsoft Graph API for batch

    Args:
        events (list): a list of tuples (net_id, subject, date). date has format of YYYY-MM-DD
        access_token: a token to use the services offered by the Microsoft Graph API
        calendar_id (str): the id of the specified shared calendar

    Returns:
        A list of dictionaries (batches)
    """
    
    # A list of dictionaries
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
                }
            },
            "headers": {
                "Authorization": str(access_token),
                'Content-type': 'application/json'
            }
        }
        batches[batch_counter]["requests"].append(request)

        id_counter = id_counter + 1
        if (id_counter % 21 == 0):
            id_counter = 1
            batch_counter = batch_counter + 1
    
    return batches

def check_batch_responses(batch, batch_responses):
    """
    Check the responses of each request made in the batch
    """
    for response in batch_responses:
        if response["status"] == 201: # 201 is the response for Created
            logger.info("Event {subject} on {date} was successfully added".format(subject=response['body']['subject'], date=response['body']['start']['dateTime']))
        elif response["status"] == 204: #201 is the response for No Content 
            logger.info("Event was Deleted")
        else:
            id = int(response['id'])
            subject = batch['requests'][id - 1]['body']['subject']
            date = batch['requests'][id - 1]['body']['start']['dateTime']
            logger.error("Event {subject} on {date} was unccessfully added".format(subject=subject, date=date))
            logger.error("Error: {error}".format(error=response['body']['error']))

def post_batch(user_client, access_token, batches):
    """
    Create the batches for events being deleted from the shared_calendar using the format indicated by the Microsoft Graph API for batch

    Args:
        user_client (Graph Client Object) : msgraph.core._graph_client.GraphClient 
        batches (list): A list of dictionaries (batches)
    """
    endpoint = 'https://graph.microsoft.com/v1.0/$batch'
    header = {
        'Content-type': 'application/json'
    }
    for batch in batches:
        response = user_client.post(endpoint,data=json.dumps(batch), headers=header)
        if response.status_code == 400:
            logger.error(response.json()["error"])
            continue
        check_batch_responses(batch, response.json()["responses"])        



    # # body = {    
    # #     "requests": [
    # #         {
    # #             "url": "/me/events",
    # #             "method": "GET",
    # #             "id": "1"
    # #         }
    # #     ]
    # # }
    
    # header = {
    #     'Content-type': 'application/json'
    # }

        # body = {    
    #     "requests": [
    #         {
    #             "url": "/me/events",
    #             "method": "GET",
    #             "id": "1"
    #         }
    #     ]
    # }