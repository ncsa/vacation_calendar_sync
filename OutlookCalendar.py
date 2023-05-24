#!/usr/bin/python
import json
from azure.identity import DeviceCodeCredential
from msgraph.core import GraphClient
import yaml
from GenerateReport import GenerateReport
import SharedCalendar 
import argparse
from datetime import datetime
from dataclasses import dataclass
from SimpleEvent import SimpleEvent
import os 
from datetime import timedelta 
import time

class OutlookCalendar:

    def __init__(self):    
        """
        Initializes the members variables by retrieving the netrc and yaml file
        """

        required_attributes = ['client_id', 'tenant_id', 'scope', 'group_members', 'shared_calendar_name']

        # Created ENV variable using docker's ENV command in Dockerfile
        path = os.getenv('AZURE_GRAPH_AUTH')
        with open(path, 'r') as file:
            dictionary = yaml.safe_load(file)
            for attribute in required_attributes:
                assert attribute in dictionary, f"{attribute} is not provided in microsoft_graph_auth.yaml"
                setattr(self, attribute, dictionary[attribute])
                
            self.device_code_credential = DeviceCodeCredential(client_id = self.client_id, tenant_id = self.tenant_id)
            self.user_client = GraphClient(credential=self.device_code_credential, scopes=self.scope.split(' '))  

    def get_individual_calendars(self, start_date, end_date):
        """
        Retrieves and returns a json object of individuals'calendar events
          that are within/overlap between the start_date and end_date

        Args:
            start_date (datetime object): the start date of the calendar (YYYY-MM-DD)
            end_date (dateime object): the end date of the calendar (YYYY-MM-DD)
        
        Returns:
            json: json object of the events within/overlap between the start and end date
        """

        header = {
            'Authorization': str(self.device_code_credential.get_token(self.scope)), # Retrieves the access token
            'Content-Type': "application/json",
            'Prefer': "outlook.timezone=\"Central Standard Time\""
        }
        
        data = {        
            "schedules": list(self.group_members.keys()), # List of the net_ids of each individual listed in the yaml file
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

        # If succcesful, the response.json() includes the events that occur within the inverval of start_date and end_date 
        # This would include events that:
        # start before start_date and end before end_date, 
        # start before start_date and end after end_date, 
        # start after start_date and end before end_date, 
        # start after start_date and end after end_date
        # The exception is if the event start on the end_date. That event will not be included in the response.json()
        response = self.user_client.post('/me/calendar/getSchedule', data=json.dumps(data), headers=header)

        #print(response.json())

        if (response.status_code == 200):
            return response.json()
        else:
            raise Exception(response.json())

    def get_shared_calendar(self, start_date, end_date):
        """
        Retrieves and returns a json object of the shared calendar events
          that are within/overlap between the start_date and end_date

        Args:
            user_client (Graph Client Object) : msgraph.core._graph_client.GraphClient 
            start_date (str): The start date of the timeframe
            end_date (str): The end date of the timeframe
        
        Returns:
            json: json object of the events within/overlap between the start and end date
        """

        access_token = self.device_code_credential.get_token(self.scope)
        
        header = {
            'Authorization': str(access_token),
            'Content-Type': 'application/json'
        }
        response = self.user_client.get('/me/calendars', headers=header)
        
        # Loop through all the calendars available to the user, and find the one indicated in the yaml file and retrieve its calendar ID
        #print(response.json())
        for calendar in response.json()['value']:
            if calendar['name'] == self.shared_calendar_name:
                self.shared_calendar_id = calendar['id']
                break

        # start_date = datetime.strftime(start_date, "%Y-%m-%dT%H:%M:%S")
        # end_date = datetime.strftime(end_date, "%Y-%m-%dT%H:%M:%S")

        start_date = str(start_date.date())
        end_date = str(end_date.date())
        
        header = {
            'Authorization': str(access_token),
            'Prefer': "outlook.timezone=\"Central Standard Time\""
        }

        # If succcesful, the response.json() includes the events that occur within the inverval of start_date and end_date 
        # This would include events that:
        # start before start_date and end before end_date, 
        # start before start_date and end after end_date, 
        # start after start_date and end before end_date, 
        # start after start_date and end after end_date
        # The exception is if the event start on the end_date. That event will not be included in the response.json()
        request = '/me/calendars/' + self.shared_calendar_id +'/events' + '?$select=subject,body,start,end,showAs&$top=100&$filter=start/dateTime ge ' + '\''+ start_date + '\'' + ' and start/dateTime lt ' + '\'' + end_date + '\''    
        response = self.user_client.get(request, headers=header)
        
        if (response.status_code == 200):
            return response.json()
        else:
            raise Exception(response.json())


    def process_individual_calendars(self, calendar, user_start_date):
        """
        Creates simple event objects using the the individual work calendars 

        Args:
            calendar (json): json object of the events within/overlap between a specified start and end date for indvidual calendars
            user_start_date (datetime): a datetime object that represents the start time specified by the user (the current date)

        Returns: 
            list: A list of SimpleEvent objects

        """

        filtered_events = []
        for member in calendar['value']:
            net_id = member['scheduleId'].split('@')[0]
            for event in member['scheduleItems']:
                if event['status'] != 'oof': continue
         
                simple_events = SimpleEvent.create_event_for_individual_calendars(event, user_start_date, net_id)
                filtered_events.extend(simple_events)
                
        return filtered_events
    
    def process_shared_calendar(self, shared_calendar):
        """
        Creates simple event objects using the the individual work calendars 

        Args:
            calendar (json): json object of the events within/overlap between a specified start and end date for indvidual calendars
            user_start_date (datetime): a datetime object that represents the start time specified by the user (the current date)

        Returns: 
            tuple: A tuple containing a list of SimpleEvent objects and a list of the correspending event ids 
        """

        filtered_events = []
        event_ids = {}
        # the events can be multiday
        
        for event in shared_calendar['value']:
    
            if event['showAs'] != 'free': continue
            
            simple_event = SimpleEvent.create_event_for_shared_calendar(event)
            # Only valid events are returned as a simpleEvent object
            if simple_event == None: continue
            
            filtered_events.append(simple_event)
            event_date = str(simple_event.date.date())
            
            event_ids[simple_event.subject + event_date] = event['id']

        return (filtered_events, event_ids)
    
    # @TODO: get rid of this function and call self.device_code_credential.get_token(self.scope) straight up instead
    def get_access_token(self):
        return self.device_code_credential.get_token(self.scope)

def process_args():
        parser = argparse.ArgumentParser(
            prog = 'OutlookCalendar',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description = 'Generate a report for employees who are status \'away\' within a timeframe. \n' +
            'Updates shared calendar among team members using each member\'s calendar with events marked with status \'away\'',
            epilog = 
        '''
Program is controlled using the following environment variables:
    NETRC
        path to netrc file (default: ~/.netrc)                    
            where netrc file has keys "OUTLOOK_LOGIN" 
            and the "OUTLOOK_LOGIN" key has values for login, password
        ''')

        parser.add_argument('-s', '--update_shared_calendar', action='store_true', help='Update shared calendar')
        parser.add_argument('-r', '--report', action='store_true', help='Generate report using the shared calendar')        
        parser.add_argument('-d', '--dump_json', action='store_true', help='Dump table data to console as json')
        parser.add_argument(dest= 'start_date', action='store', help='The start date of the timeframe. date format: YYYY-MM-DD')
        parser.add_argument(dest= 'end_date', action='store', help='The end date of the timeframe. date format: YYYY-MM-DD')

        args = parser.parse_args()
        
        return args
   
def sanitize_input(user_args):    
    """ Sanitizes the user arguments to verify their validity """

    # If the start_date and end_date given by user doesn't fit the format, then the datetime.strptime will 
    # throw its own error
    start = datetime.strptime(user_args.start_date,"%Y-%m-%d")
    end = datetime.strptime(user_args.end_date,"%Y-%m-%d")

    # Check whether start date occurs before end_date
    assert (end - start).days >= 0, "start date should start date prior to the end date"    
    return (start, end)

if __name__ == '__main__':
    # PROGRESS: Looking into whether I should include the headers for some of the calls because some of them seem to be working without headers
    # Just changed the access_code of individual 


    # python3 OutlookCalendar.py [start date] [end date]
    # date format: YYYY-MM-DD
    args = process_args()
    #print(args)

    start_date, end_date = sanitize_input(args)
    days_out = timedelta(days=7)

    calendar = OutlookCalendar()
    
    #shared_calendar_events, event_ids = calendar.process_shared_calendar(calendar.get_shared_calendar(start_date, end_date))    
    # individual_calendars = calendar.process_individual_calendars(calendar.get_individual_calendars(start_date, end_date), start_date)   
    # SharedCalendar.update_shared_calendar(individual_calendars, shared_calendar_events, event_ids, calendar.shared_calendar_id, calendar.get_access_token(), calendar.user_client)

   
    if args.report:
        shared_calendar_events, event_ids = calendar.process_shared_calendar(calendar.get_shared_calendar(start_date, end_date))    
        GenerateReport(shared_calendar_events).generate("r", start_date, end_date)

    if args.shared:
        count = 0
        while True:
            print("Updating shared calendar")
            print("count: " + str(count))

            today = datetime.today()
            start_date = today.strftime("%Y-%m-%d")
            end_date = (today + days_out).strftime("%Y-%m-%d")

            print("current date and time: " + str(today))

            individual_calendar_events = calendar.process_individual_calendars(calendar.get_individual_calendars(start_date, end_date), start_date)
            shared_calendar_events, event_ids = calendar.process_shared_calendar(calendar.get_shared_calendar(start_date, end_date)) 
            
            SharedCalendar.update_shared_calendar(individual_calendar_events, shared_calendar_events, event_ids, calendar.shared_calendar_id, calendar.get_access_token(), calendar.user_client)

            count = count + 1
            print("--------------------------------------------------------")
            time.sleep(900)
            

    if args.dump_json:
        GenerateReport(shared_calendar_events, None).dump_calendar_to_json(shared_calendar_events, start_date, end_date)

    
   
# pttran - OUT
# pttran - OUT AM
# pttran - OUT PM


