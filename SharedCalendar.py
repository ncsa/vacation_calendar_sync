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

path = os.getenv('AZURE_GRAPH_AUTH')
with open(path, 'r') as file:
    dictionary = yaml.safe_load(file)
    logging_path = dictionary['logging_file_path']

# Define Logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formater = logging.Formatter('%(name)s:%(asctime)s:%(filename)s:%(levelname)s:%(message)s')

file_handler = logging.FileHandler(filename=logging_path)
file_handler.setFormatter(formater)
file_handler.setLevel(logging.INFO)
logger.addHandler(file_handler)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formater)
stream_handler.setLevel(logging.DEBUG)
logger.addHandler(stream_handler)
    
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

    individual_events_set  = set(create_tuple(individual_calendars))
    shared_events_set = set(create_tuple(shared_calendar))
    
    events_to_add = individual_events_set.difference(shared_events_set)
    events_to_delete = shared_events_set.difference(individual_events_set)
    
    batches_to_add = create_batches_for_adding_events(events_to_add, access_token, shared_calendar_id)
    post_batch(user_client, access_token, batches_to_add)

    #events_info = create_dict(events_to_delete, event_ids)
    batches_to_delete = create_batches_for_deleting_events(events_to_delete, access_token, shared_calendar_id, event_ids)
    post_batch(user_client, access_token, batches_to_delete)

    #add_event_to_shared_calendar(user_client, events_to_add, shared_calendar_id, access_token)
    #delete_event_from_shared_calendar(user_client, events_to_delete, shared_calendar_id, event_ids, access_token)

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

def create_dict(events, event_ids):
    event_id_to_subject = {}
    for event in events:
        event_id = event_ids[event[1] + event[2]]
        event_id_to_subject[event_id] = event
    
    return event_id_to_subject

# May not need this function anymore
# def add_event_to_shared_calendar(user_client, events_to_add, calendar_id, access_token):
#     """
#     Make POST request to Outlook to add events to the shared calendar 

#     Args:
#         user_client (GraphClient Object)
#         events_to_add (list): A list of tuple events
#         calendar_id (str): The id of the shared calendar
#         access_token (int): The access token for the project
#     """
#     #logger.debug("Access token: {}".format(access_token))
    
#     # (event.net_id, event.subject, event.date)
#     counter = 0
#     for event in events_to_add:
#         #print(event)
#         start_date_time = event[2] + "T00:00:00.0000000"

#         end_date = datetime.datetime.strptime(event[2],"%Y-%m-%d") + timedelta(days=1)
#         end_date_time = end_date.strftime("%Y-%m-%d") + "T00:00:00.0000000"
        
#         header = {
#             'Authorization': str(access_token),
#             #'Authorization': str(access_token.get_access_token()),
#             'Content-Type': "application/json",
#         }
#         payload = {
#             "subject": event[1],
#             "showAs": "free",
#             "start": {
#                 "dateTime": start_date_time,
#                 "timeZone": "Central Standard Time"
#             },
#             "end": {
#                 "dateTime": end_date_time,
#                 "timeZone": "Central Standard Time"
#             }
#         }

#         data_as_json = json.dumps(payload)
#         request = '/me/calendars/' + calendar_id +'/events'
#         response = user_client.post(request, data=data_as_json, headers=header)

#         if (response.status_code != 201): # 201 Created
#             #print("Unsuccessfully added " + event[1] + " to calendar")
#             logger.info("Unsuccessfully added {event} to calendar",  event[1])
#         else:
#             #print(str(counter) + " Adding Event: " + event[1] + " on " + event[2])
#             logger.info("Adding Event: {event_subject} on {event_date}".format(event_subject = event[1], event_date = event[2]))

#         # counter = counter + 1
#         # if (counter % 10 == 0):
#         #     time.sleep(360)
#         #     counter = 0

# May not need this function anymore
# def delete_event_from_shared_calendar(user_client, events_to_delete, calendar_id, event_ids, access_token):
#     """
#     Make DELETE request to Outlook to delete events from the shared calendar 

#     Args:
#         user_client : GraphClient Object 
#         events_to_delete (list): A list of tuple events
#         calendar_id (str): The id of the shared calendar
#         access_token (int): The access token for the project
#     """
#     counter = 0

#     for event in events_to_delete:
#         event_id = event_ids[event[1] + event[2]]
#         header = {
#             'Authorization': str(access_token)
#         }
#         request = '/me/calendars/' + calendar_id +'/events/' +  str(event_id)
#         response = user_client.delete(request, headers=header)

#         if (response.status_code != 204): #204 No Content
#             #print("Unsuccessfully deleted " + event[1] + " from calendar")
#             logger.info("Unsuccessfully deleted {event} from calendar".format(event=event[1]))
#         else:
#             #print("Deleting Event: " + event[1])
#             logger.info("Deleting Event: {event}".format(event=event[1]))

#         # counter = counter + 1
#         # if (counter % 10 == 0):
#         #     time.sleep(360)
#         #     counter = 0

def create_batches_for_deleting_events(events_to_delete, access_token, calendar_id, event_ids):

    batches = []
    
    num_of_batches = math.ceil(len(events_to_delete) / 20) # 20 is the maximum of request in a batch

    for i in range(num_of_batches):
        payload = {
            "requests": []
        }
        batches.append(payload)
    
    batch_tracker = 0
    id_counter = 1

    for event in events_to_delete:
        event_id = event_ids[event[1] + event[2]]

        request = {
            "id": str(id_counter),
            "url": '/me/calendars/' + calendar_id +'/events/' +  str(event_id),
            "method": "DELETE",
            "headers": {
                'Authorization': str(access_token)
            }
        }

        batches[batch_tracker]["requests"].append(request)
        id_counter = id_counter + 1
        if (id_counter % 21 == 0):
            id_counter = 1
            batch_tracker = batch_tracker + 1

    return batches

def create_batches_for_adding_events(events, access_token, calendar_id):
    # (event.net_id, event.subject, str(event.date.date()))
    # A list of batch requests 

    # A list of dictionaries
    batches = []
    num_of_batches = math.ceil(len(events) / 20) # 20 is the maximum of request in a batch
    
    for i in range(num_of_batches):
        payload = {
            "requests": []
        }
        batches.append(payload)

    batch_tracker = 0
    id_counter = 1
    for event in events:
    #print(event)
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

        batches[batch_tracker]["requests"].append(request)

        id_counter = id_counter + 1
        if (id_counter % 21 == 0):
            id_counter = 1
            batch_tracker = batch_tracker + 1
    
    return batches

def post_batch(user_client, access_token, batches):
    endpoint = 'https://graph.microsoft.com/v1.0/$batch'

    header = {
        'Content-type': 'application/json'
    }
        
    for batch in batches:
        response = user_client.post(endpoint,data=json.dumps(batch), headers=header)
        batch_responses = response.json()["responses"]
        
        for response in batch_responses:
            if response["status"] == 201: # 201 is the response for Created
                logger.info("Event {subject} on {date} was successfully added".format(subject=response['body']['subject'], date=response['body']['start']['dateTime']))
            elif response["status"] == 204: #201 is the response for No Content 
                logger.info("Event was Deleted")
                #logger.info("Event {subject} was successfully Deleted".format(subject=events_info[]))

            else:
                id = int(response['id'])
                subject = batch['requests'][id - 1]['body']['subject']
                date = batch['requests'][id - 1]['body']['start']['dateTime']
                logger.error("Event {subject} on {date} was unccessfully added".format(subject=subject, date=date))
                logger.error("Error: {error}".format(error=response['body']['error']))

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