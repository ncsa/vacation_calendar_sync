import collections
from datetime import datetime
import json
from selectors import EVENT_WRITE

# done

class SharedCalendar:
    """
    Class that represent the shared calendar among the group members 

    Attributes 
    ----------
    event_ids : dictionary
        A dictionary with key:value of formated event name and the id associated with the event
    list_of_day: a list of strings 
        A list containing all the start date of events 
    
    Methods
    -------
    parse_members_calendars 
        Parses the members' calendars and returns a sorted dictionary with key:pair value of date to list of events 
    parse_shared_calendar
        Parses the shared calendar and returns a sorted dictionary with key:pair value of date to list of events 
    add_event_to_shared_calendar
        Make POST request to Outlook to add events to the shared calendar 
    delete_event_from_shared_calendar
        Make DELETE request to Outlook to delete events from the shared calendar 
    date_parser
        Parses the date into a tuple of date (str) and time (str) and return the tuple
    """

    def __init__(self, members_calendars, shared_calendar, shared_calendar_id, access_token, user_client, start):
        """
        Parameters
        ----------
        members_calendars : json dictionary 
            A json dictionary containing the events on the member's calendars within the start-end timeframe 
        shared_calendar : json dictionary 
            A json dictionary containing the events on the shared calendar within the start-end timeframe 
        shared_calendar_id : str
            The id of the shared calendar 
        access_token : int
            The access token for the project
        user_client : GraphClient Object
        """

        self.event_ids = {}
        self.list_of_days = []
        members = self.parse_members_calendars(members_calendars)
        #print(members_calendars)
        shared = self.parse_shared_calendar(shared_calendar)
        self.list_of_days.sort()
        
        dict_add_events = {}
        dict_delete_events = {}
        for day in self.list_of_days:
            # Events that exists in the members, but not the shared calendar
            # Either A or B has to have the day, or else the day wouldn't exist
            # If A has the day, but B doesn't, then add all the events in A to shared Calendar
            # If B has the day, but B doesn't, then delete all the events in B from the shared calendar
            
            if day not in shared: # which means A has the day 
                dict_add_events[day] = set(members[day])
            elif day not in members:
                dict_delete_events[day] = set(shared[day])
            else:
                A = set(members[day])
                B = set(shared[day])    
                dict_add_events[day] = A.difference(B)
                dict_delete_events[day] = B.difference(A)

        self.add_event_to_shared_calendar(user_client, dict_add_events, shared_calendar_id, access_token)
        self.delete_event_from_shared_calendar(user_client, dict_delete_events, shared_calendar_id, access_token)


    def parse_members_calendars(self, members_calendars):
        # returns a list of 
        pass
        """
        Parses the members' calendars and returns a sorted dictionary with key:pair value of date to list of events 

        Parameters
        ----------
        members_calendars : json dictionary 
            A json dictionary containing the events on the member's calendars within the start-end timeframe 
        """
        #print(members_calendars)
        # date_dict is a dictionary with keys representing the dates, following the YYYYMMDD format, and each value contains a list of event objects.
        date_dict = {}
        for member in members_calendars['value']:
            net_id_of_member = member['scheduleId'].split('@')[0]
            for event in member['scheduleItems']:
                # TODO: Change to 'away'
                if event['status'] == 'oof': 
                    start_date = event['start']['dateTime']
                    # Change variable day into a YYYYMMDD format 
                    day = start_date[:10]
                    day = (day[:4] + day[5:7] + day[8:])
                    
                    # if (int(day) < int(user_start)):
                    #     continue

                    if day not in self.list_of_days:
                        self.list_of_days.append(day)

                    start = self.date_parser(event['start']['dateTime'])
                    end = self.date_parser(event['end']['dateTime'])
                    event_as_tuple = (
                        str(start[0]),
                        str(start[1]),
                        str(end[0]),
                        str(end[1]),
                        net_id_of_member + "-" + start[0] + start[1]
                    )

                    if day in date_dict:  
                        date_dict[day].append(event_as_tuple)
                    else:
                        date_dict[day] = [event_as_tuple]
        
        #print(date_dict)
        event_days_inorder = collections.OrderedDict(sorted(date_dict.items()))        
        return event_days_inorder

    def parse_shared_calendar(self, shared_calendar):
        """
        Parses the shared calendar and returns a sorted dictionary with key:pair value of date to list of events 

        Parameters
        ----------
        shared_calendar : json dictionary 
            A json dictionary containing the events on the shared calendar within the start-end timeframe 
        """

        # date_dict is a dictionary with keys representing the dates, following the YYYYMMDD format, and each value contains a list of event objects.
        date_dict = {}
        for event in shared_calendar['value']:
            # TODO: Change to 'away'
            if event['showAs'] == 'oof': 
                start_date = event['start']['dateTime']
                # Change variable day into a YYYYMMDD format 
                day = start_date[:10]
                day = (day[:4] + day[5:7] + day[8:])
    
                if day not in self.list_of_days:
                    self.list_of_days.append(day)

                start = self.date_parser(event['start']['dateTime'])
                end = self.date_parser(event['end']['dateTime'])
                event_as_tuple = (
                    #str(item['subject']),
                    str(start[0]),
                    str(start[1]),
                    str(end[0]),
                    str(end[1]),
                    event['subject'].split(' ')[0] + "-" + start[0] + start[1]
                    )

                if day in date_dict:
                    date_dict[day].append(event_as_tuple)
                else:
                    date_dict[day] = [event_as_tuple]
                self.event_ids[event_as_tuple[4]] = event['id']
                
        event_days_inorder = collections.OrderedDict(sorted(date_dict.items()))
        return event_days_inorder

    def add_event_to_shared_calendar(self, user_client, events, calendar_id, access_token):
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

        for key, value in events.items():
            list_of_tuple_events = list(value)
            for event in list_of_tuple_events:

                print("Adding Event: " + event[0])
                event = list(event)
                start_date = event[0][6:] + '-' + event[0][:5] + 'T' + event[1] + ':00'
                end_date = event[2][6:] + '-' + event[2][:5] + 'T' + event[3] + ':00'
                payload = {
                    "subject": event[4].split('-')[0] + " Away",
                     "start": {
                        "dateTime": start_date,
                        "timeZone": "Central Standard Time"
                    },
                    "end": {
                        "dateTime": end_date,
                        "timeZone": "Central Standard Time"
                    },
                }
                header = {
                    'Authorization': str(access_token),
                    'Content-Type': "application/json",
                }
                data_as_json = json.dumps(payload)
                request = '/me/calendars/' + calendar_id +'/events'
                response = user_client.post(request, data=data_as_json, headers=header)
                print(response)
                #print(response)

    def delete_event_from_shared_calendar(self, user_client, events, calendar_id, access_token):
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

        for key, value in events.items():
            list_of_tuple_events = list(value)
            for event in list_of_tuple_events:
                print("Deleting Event: " + event[0])
                event_id = self.event_ids[event[4]] # the startime and endtime
                header = {
                    'Authorization': str(access_token)
                }
                request = '/me/calendars/' + calendar_id +'/events/' +  str(event_id)
                response = user_client.delete(request, headers=header)
                #print(response)

    def date_parser(self, date):
        """
        Parses the date into a tuple of date (str) and time (str) and return the tuple

        Parameters
        ----------
        date : str
            A string consisting of the exact time of the event 
        """
        date_time = date.split('T')
        date = date_time[0]
        date = date[5:] + "-" + date[:4]
        time = date_time[1]
        return (date, time[:5])
        #return calendar_as_json
                


