#!/usr/bin/python
from http import client
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
import logging
from logging import handlers
import utils
import requests
import sys
import azure


EVENT_STATUS = 'oof' # out of office

class OutlookCalendar:
    def __init__(self, configs):    
        """
        Initializes the members variables by retrieving the netrc and yaml file
        """

        required_attributes = ['client_id', 'tenant_id', 'scope', 'group_members', 'shared_calendar_name', 'logging_file_path', 'days_out', 'update_interval']   
         
        for attribute in required_attributes:
            assert attribute in configs, f"{attribute} is not provided in microsoft_graph_auth.yaml"
            setattr(self, attribute, configs[attribute])
        
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
        
        access_token = self.get_access_token()

        header = {
            #'Authorization': str(self.device_code_credential.get_token(self.scope)), # Retrieves the access token
            'Authorization': access_token, # Retrieves the access token
            'Content-Type': "application/json",
            'Prefer': "outlook.timezone=\"Central Standard Time\""
        }
        
        
        
        payload = {        
            "schedules": self.group_members, # List of the net_ids of each individual listed in the yaml file
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
        
        try:
            response = self.user_client.post('/me/calendar/getSchedule', data=json.dumps(payload), headers=header)
        except Exception as error:
            logging.error(f"An error occured:\n{error}")
            
            with open("status.log", "w") as f:
                f.write(error)


            #utils.send_email(self.user_client, self.get_access_token(), error)
        
        #response = self.user_client.post('/me/calendar/getSchedule', data=json.dumps(payload), headers=header)
        if (response.status_code == 200):
            return response.json()
        else:
            utils.send_email(self.user_client, self.get_access_token(), "Unable to retrieve individual calendars")
            raise Exception(response.json())

    def get_shared_calendar(self, start_date, end_date):
        """
        Retrieves and returns a json object of the shared calendar events
          that are within/overlap between the start_date and end_date

        Args:
            user_client (Graph Client Object): msgraph.core._graph_client.GraphClient 
            start_date (str): The start date of the timeframe
            end_date (str): The end date of the timeframe
        
        Returns:
            json: json object of the events within/overlap between the start and end date
        """

        #access_token = self.device_code_credential.get_token(self.scope)
        access_token = self.get_access_token()
 
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
        request = '/me/calendars/' + self.shared_calendar_id +'/events' + '?$select=subject,body,start,end,showAs&$top=100&$filter=start/dateTime ge ' + '\''+ start_date + '\'' + ' and start/dateTime lt ' + '\'' + end_date + '\''    
        response = self.user_client.get(request, headers=header)

        if (response.status_code == 200):
            return response.json()
        else:
            utils.send_email(self.user_client, self.get_access_token(), "Unable to retrieve shared calendar")
            raise Exception(response.json())


    def process_individual_calendars(self, calendar, user_start_date, user_end_date):
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
            try:
                for event in member['scheduleItems']:
                    if event['status'] != EVENT_STATUS: continue
            
                    simple_events = SimpleEvent.create_event_for_individual_calendars(event, user_start_date, user_end_date, net_id)
                    
                    filtered_events.extend(simple_events)
            except KeyError as e:
                logger.warning(f"Unable to find: " + net_id)
                
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
            
            simple_event = SimpleEvent.create_event_for_shared_calendar(event, self.group_members)
            # Only valid events are returned as a simpleEvent object
            if simple_event == None: continue
            
            filtered_events.append(simple_event)
            event_date = str(simple_event.date.date())
            
            event_ids[simple_event.subject + event_date] = event['id']

        return (filtered_events, event_ids)
    
    # @TODO: get rid of this function and call self.device_code_credential.get_token(self.scope) straight up instead
    def get_access_token(self):
        try:
            access_token = self.device_code_credential.get_token(self.scope)
        except azure.core.exceptions.ClientAuthenticationError as error:
            logger.error("Need to authenticate with Microsoft Graph")
            logger.error(error)
            sys.exit(1)
        
        return access_token
        
def process_args():
        parser = argparse.ArgumentParser(
            prog = 'vacation_calendar_sync',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description = 'Updates shared calendar among team members using each member\'s calendar with events marked as status \'away\'',
            epilog = 
                '''
Program is controlled using the following environment variables:
    AZURE_GRAPH_AUTH
        path to the yaml configuration file          
                ''')

        parser.add_argument('-s', '--update_shared_calendar', action='store_true', help='Update shared calendar')
        parser.add_argument('-d', '--dump_json', action='store_true', help='Dump table data to console as json')
        parser.add_argument('-m', '--manual_update', action='store', nargs=2, help="Manually update the shared calendar with start and end time "+
                            "with format YYYY-MM-DD")
        
        args = parser.parse_args()
        
        return args
   
def sanitize_input(start_date, end_date):    
    """ Sanitizes the user arguments to verify their validity """

    # If the start_date and end_date given by user doesn't fit the format, then the datetime.strptime will 
    # throw its own error
    start_date = datetime.strptime(start_date,"%Y-%m-%d")
    end_date = datetime.strptime(end_date,"%Y-%m-%d")

    # Check whether start date occurs before end_date
    assert (end_date - start_date).days >= 0, "start date should start date prior to the end date"    
    return (start_date, end_date)

def debug(configs):
    print("In debug mode")
    calendar = OutlookCalendar(configs)
    days_out = timedelta(days=3)
    start_date = datetime(year=2023, month=7, day=17)
    end_date = start_date + days_out
    
    individual_calendars = calendar.process_individual_calendars(calendar.get_individual_calendars(start_date, end_date), start_date, end_date)   
    shared_calendar_events, event_ids = calendar.process_shared_calendar(calendar.get_shared_calendar(start_date, end_date))    
    #SharedCalendar.update_shared_calendar(individual_calendars, shared_calendar_events, event_ids, calendar.shared_calendar_id, calendar , calendar.user_client)

    #utils.send_email(calendar.user_client, calendar.get_access_token(), "test")

def main(configs):
    calendar = OutlookCalendar(configs)    
    args = process_args()
    
    start_date = None
    end_date = None
    days_out = timedelta(days=calendar.days_out)

    if args.update_shared_calendar:
        count = 0
        while True:
            logger.info("Updating shared calendar -> Count : {count}".format(count=count))
            
            today = datetime.today()
            start_date = datetime(year=today.year, month=today.month, day=today.day, hour=0,minute=0)
            end_date = start_date + days_out

            individual_calendar_events = calendar.process_individual_calendars(calendar.get_individual_calendars(start_date, end_date), start_date, end_date)
            shared_calendar_events, event_ids = calendar.process_shared_calendar(calendar.get_shared_calendar(start_date, end_date)) 
            
            SharedCalendar.update_shared_calendar(individual_calendar_events, shared_calendar_events, event_ids, calendar.shared_calendar_id, calendar.get_access_token(), calendar.user_client)

            count = count + 1
            time.sleep(calendar.update_interval)
            
    if args.dump_json:
        shared_calendar_events, event_ids = calendar.process_shared_calendar(calendar.get_shared_calendar(start_date, end_date)) 
        GenerateReport(shared_calendar_events, None).dump_calendar_to_json(shared_calendar_events, start_date, end_date)

    if args.manual_update:
        dates = sanitize_input(args.manual_update[0], args.manual_update[1])
        start_date = dates[0]
        end_date = dates[1]
        individual_calendar_events = calendar.process_individual_calendars(calendar.get_individual_calendars(start_date, end_date), start_date, end_date)
        shared_calendar_events, event_ids = calendar.process_shared_calendar(calendar.get_shared_calendar(start_date, end_date)) 
        SharedCalendar.update_shared_calendar(individual_calendar_events, shared_calendar_events, event_ids, calendar.shared_calendar_id, calendar.get_access_token(), calendar.user_client)

if __name__ == '__main__':
    configs = utils.retrieve_from_yaml()
    
    formater = logging.Formatter('%(name)s:%(asctime)s:%(filename)s:%(levelname)s:%(message)s')
    rotate_file_handler = handlers.RotatingFileHandler(configs['logging_file_path'], mode='a', maxBytes=2000000, backupCount=2)
    #rotate_file_handler = handlers.RotatingFileHandler("output_event.log", maxBytes=2048, backupCount=2)
    rotate_file_handler.setFormatter(fmt=formater)
    rotate_file_handler.setLevel(logging.DEBUG)

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(rotate_file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(fmt=logging.Formatter('%(name)s:%(asctime)s:%(filename)s:%(levelname)s:%(message)s'))
    logger.addHandler(stream_handler)

    main(configs)
    #debug(configs)

