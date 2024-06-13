from datetime import datetime
import utils
import requests
import logging
from SimpleEvent import SimpleEvent
import json
import math
import time
EVENT_STATUS = 'oof' # out of office

# This logger is a child of the __main__ logger located in OutlookCalendar.py
logger = logging.getLogger("__main__." + __name__)

def get_individual_calendars(start_date, end_date, group_members, access_token):
    """
    Retrieves a json object of individuals'calendar events 
    that are within/overlap between the start_date and end_date. 
    Note that events that start on end_date is not included

    Args:
        start_date (datetime): the start date of timeframe being updated
        end_date (dateime):  the end date of timeframe being updated
        access_token (str): the token used make calls to the Microsoft 
        Graph API as part of the Oauth2 Authorization code flow
    
    Returns:
        json: json object of the events within/overlap between the start and end date 
        with exception of events that starts on end_date
    """
    
    header = {
        'Authorization': access_token, 
        'Content-Type': "application/json",
        'Prefer': "outlook.timezone=\"Central Standard Time\""
    }

    body = {        
        "schedules": group_members, # List of the net_ids of each individual listed in the yaml file
        "startTime": {
            "dateTime": datetime.strftime(start_date, "%Y-%m-%dT%H:%M:%S"), 
            "timeZone": "Central Standard Time"
        },
        "endTime": {
            "dateTime": datetime.strftime(end_date, "%Y-%m-%dT%H:%M:%S"),
            "timeZone": "Central Standard Time"
        },
        "availabilityViewInterval": 1440 # Duration of an event represented in minutes
    }

    endpoint = "https://graph.microsoft.com/v1.0/me/calendar/getSchedule"
    response = requests.post(endpoint, data=json.dumps(body),headers= header) 

    max_retries = 5
    retry_count = 0
    x = 0
    initial_waiting_time = 30
    while (response.status_code != 200 and retry_count <= max_retries):
        logger.warning(f"Retrying to connect to getSchedule endpoint {retry_count} and {(2**x) * initial_waiting_time}")
        time.sleep((2**x) * initial_waiting_time)
        response = requests.post(endpoint, data=json.dumps(body),headers=header) 
        retry_count = retry_count + 1
        x = x + 1

        '''
        1 * 30 = 30
        2 * 30 = 60
        4 * 30 = 120
        8 * 30 = 240
        16 * 30 = 480
        32 * 30 = 960
        '''

    if response.status_code != 200:
        logger.error(f"status code: {response.status_code}")
        logger.error(f"start date: {start_date}")
        logger.error(f"end date: {end_date}")
        logger.error(f"group members: {group_members}")
        logger.error(f"access_token: {access_token}")
        logger.error(f"response header: {response.headers}")
        logger.error(f"response header type: {type(response.headers)}")
        message = 'Unable to retrieve individual calendar from the getSchedule endpoint'
        utils.send_email(message, access_token)  
        #logger.error(response.json())
        logger.error(f"response.text: \"{response.text}\"")
        raise ConnectionError(message)

    return response.json()



def get_individual_calendars_using_batch(start_date, end_date, group_members, access_token):
    """
    Retrieves a json object of individuals'calendar events 
    that are within/overlap between the start_date and end_date. 
    Note that events that start on end_date is not included
    This method uses the Microsoft graph batch endpoint to retrieve 
    individual calendars with each entry retrieving 10 calendars

    Args:
        start_date (datetime): the start date of timeframe being updated
        end_date (datetime):  the end date of timeframe being updated
        access_token (str): the token used make calls to the Microsoft 
        Graph API as part of the Oauth2 Authorization code flow
    
    Returns:
        json (list): a list of the bodies of the entry responses of
        events that are within/overlap between the start and end date 
        with exception of events that starts on end_date
    """
    
    endpoint = "/me/calendar/getSchedule"
    batch = {
        "requests": []
    }
    grouping = 10
    multiplier = math.floor(len(group_members) / grouping)
    for i in range(0, multiplier + 1):
        start = i * grouping
        end = start + grouping
        if end > len(group_members):
            end = len(group_members)
        
        request = {
            "id": str(i + 1),
            "url": endpoint,
            "method": "POST", # This could be different for for the delete function
            "body": {        
                "schedules": group_members[start:end], # List of the net_ids of each individual listed in the yaml file
                "startTime": {
                    "dateTime": datetime.strftime(start_date, "%Y-%m-%dT%H:%M:%S"), 
                    "timeZone": "Central Standard Time"
                },
                "endTime": {
                    "dateTime": datetime.strftime(end_date, "%Y-%m-%dT%H:%M:%S"),
                    "timeZone": "Central Standard Time"
                },
                "availabilityViewInterval": 1440 # Duration of an event represented in minutes
            },
            "headers": {
                'Authorization': access_token, 
                'Content-Type': "application/json",
                'Prefer': "outlook.timezone=\"Central Standard Time\""
            }
        }
        batch["requests"].append(request) 

    endpoint = "https://graph.microsoft.com/v1.0/$batch"

    header = {
        'Accept': 'application/json',
        'Content-type': 'application/json',
        "Authorization": access_token
    }

    response = requests.post(endpoint, data=json.dumps(batch), headers=header)
    
    if response.status_code != 200:
        message = "Unable to make batch post request"
        #utils.send_email(user_client, access_token, message)
        utils.send_email(message, access_token)  
        logger.error(message)
        logger.error(f"response.text: {response.text}")
        #logger.warning(response.json())
        raise ConnectionError(message)

    list_of_responses = []
    for individual_response in response.json()["responses"]:
        if individual_response['status'] != 200: 
            message = 'Unable to retrieve individual calendar from the getSchedule endpoint'
            utils.send_email(message, access_token)  
            logger.error(f"individual_response: {individual_response}")
            logger.error(f"response header: {individual_response['headers']}")
            logger.error(f"response['body']: \"{individual_response['body']}\"")
            raise ConnectionError(message)
        list_of_responses.append(individual_response['body'])
        
    return list_of_responses

def filter(events):
    """
    Removes duplicates in the list of events 
    
    Args:
        events (SimpleEvent list): contains events extracted from individual calendars

    Returns:
        SimpleEvent list: a filtered list of events
    """

    filtered_events = []
    events.sort()
    event_to_add = events[0]

    for event in events:
        if event_to_add.net_id == event.net_id and event_to_add.date.date() == event.date.date():
            event_subject_id = utils.subject_identifier(event.subject)
            event_to_add_subject_id = utils.subject_identifier(event_to_add.subject)
            
            if event_subject_id > event_to_add_subject_id:
                event_to_add = event
            elif ("OUT AM" in event.subject and "OUT PM" in event_to_add.subject) or ("OUT PM" in event.subject and "OUT AM" in event_to_add.subject):
                event_to_add = SimpleEvent.create_all_day_event(event_to_add.net_id, event_to_add.date)
        else:
            filtered_events.append(event_to_add)
            event_to_add = event

    filtered_events.append(event_to_add)
    return filtered_events

def process_individual_calendars(calendar, start_date, end_date):
    """
    Creates simple event objects using the the individual calendars 
    retrived from get_individual_calendars

    Args:
        calendar (json): json object of the events within/overlap between 
        a specified start and end date for indvidual calendars
        start_date (datetime): the start date of timeframe being updated
        end_date (datetime):  the end date of timeframe being updated
        
    Returns: 
        list: A list of SimpleEvent objects

    """

    events = []
    for member in calendar['value']:
        net_id = member['scheduleId'].split('@')[0]
        try:
            for event in member['scheduleItems']:
                if event['status'] != EVENT_STATUS: continue
                events_to_add = SimpleEvent.create_event_for_individual_calendars(event, start_date, end_date, net_id)
                events.extend(events_to_add)
        except KeyError as e:
            logger.warning(f"Unable to find: " + net_id)

    return filter(events)
