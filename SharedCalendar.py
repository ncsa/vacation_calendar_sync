from datetime import datetime
import json
import datetime
from datetime import timedelta 
    
def update_shared_calendar(individual_calendars, shared_calendar, event_ids, shared_calendar_id, access_token, user_client):
    individual_events_set  = set(create_tuple(individual_calendars))
    shared_events_set = set(create_tuple(shared_calendar))
    
    events_to_add = individual_events_set.difference(shared_events_set)
    events_to_delete = shared_events_set.difference(individual_events_set)

    add_event_to_shared_calendar(user_client, events_to_add, shared_calendar_id, access_token)
    delete_event_from_shared_calendar(user_client, events_to_delete, shared_calendar_id, event_ids, access_token)

def create_tuple(calendar):
    events = []
    for event in calendar:
        event_tuple = (event.net_id, event.subject, str(event.date.date()))
        events.append(event_tuple)
    return tuple(events)

def add_event_to_shared_calendar(user_client, events_to_add, calendar_id, access_token):
    """
    Make POST request to Outlook to add events to the shared calendar 

    Parameters
    ----------
    user_client : GraphClient Object 
    events : dictionary 
        A dictionary with key:value pair of date and list of events to be added 
    calendar_id : str
        The id of the shared calendar 
    access_token : int 
        The access token for the project
    """

    # (event.net_id, event.subject, event.date)
    for event in events_to_add:
        #print(event)
        start_date_time = event[2] + "T00:00:00.0000000"

        end_date = datetime.datetime.strptime(event[2],"%Y-%m-%d") + timedelta(days=1)
        end_date_time = end_date.strftime("%Y-%m-%d") + "T00:00:00.0000000"
        
        header = {
            'Authorization': str(access_token),
            'Content-Type': "application/json",
        }
        payload = {
            "subject": event[1],
            "showAs": "oof",
            "start": {
                "dateTime": start_date_time,
                "timeZone": "Central Standard Time"
            },
            "end": {
                "dateTime": end_date_time,
                "timeZone": "Central Standard Time"
            }
        }

        data_as_json = json.dumps(payload)
        request = '/me/calendars/' + calendar_id +'/events'
        response = user_client.post(request, data=data_as_json, headers=header)

        if (response.status_code != 201): # 201 Created
            print("Unsuccessfully added " + event[1] + " to calendar")
        else:
            print("Adding Event: " + event[1] + " on " + event[2])

def delete_event_from_shared_calendar(user_client, events_to_delete, calendar_id, event_ids, access_token):
    """
    Make DELETE request to Outlook to delete events from the shared calendar 

    Parameters
    ----------
    user_client : GraphClient Object 
    events : dictionary 
        A dictionary with key:value pair of date and list of events to be added 
    calendar_id : str
        The id of the shared calendar 
    access_token : int 
        The access token for the project
    """

    for event in events_to_delete:
        event_id = event_ids[event[1] + event[2]]
        header = {
            'Authorization': str(access_token)
        }
        request = '/me/calendars/' + calendar_id +'/events/' +  str(event_id)
        response = user_client.delete(request, headers=header)

        if (response.status_code != 204): #204 No Content
            print("Unsuccessfully deleted " + event[1] + " from calendar")
        else:
            print("Deleting Event: " + event[1])
        

