#!/usr/bin/python
import sys
import json
from azure.identity import DeviceCodeCredential
from msgraph.core import GraphClient
import os 
import netrc
from io import StringIO
import sys
import threading
import time
from AuthenticateDevice import AuthenticateDevice
import yaml
from GenerateReport import GenerateReport
from SharedCalendar import SharedCalendar
import argparse
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from SimpleEvent import SimpleEvent

# done
# If I break it down day by day, then i will have to do the dictionary structure. 
# Actually, not necessarily. If the multiday events can be represtend by its own individual event (visually), then we can still use a list. 
# GenerateReport -> just print out the dictionary 
# 

class OutlookCalendar:
    

    class Status(Enum):
        OUT = 0
        OUT_AM = 1
        OUT_PM = 2

    # @dataclass
    # class SimpleEvent:
    #     net_id : str 
    #     subject : str # Our own formatted subject 
    #     status : Enum 
    #     date : str 
    #     #count : int # The duration of the event in terms of days


    """
    A class used to start the program

    Attribute
    ---------
    credentials : tuple 
        Includes username and password
    client_id : str
        The Application (client) ID that is shown on the Microsfot Azure Project Page
    tenant_id : str
        The Directory (tenant) ID that is shown on the Microsoft Azure Project Page 
    graphUserScopes : str
        The scope that list the permissions for the project
    group_members : dictionary
        A key:pair of name and netid 
    shared_calendar_name
        Name of the shared calendar
    get_group_members_calendars
        Retrieves and returns a json object that has the groups member's calendar events
    get_shared_calendar
        Retrieves and returns a json object of the shared calendar events that are within/overlap with between the start_date and end_date
    

    Methods
    -------
    get_credentials
        Retrieves the credential of the user through the netrc file which should include login and password and return a tuple of username and password
    initialize_graph_for_user_auth
        Initializes the Microsoft Graph API abd return user_client object returned by GraphClient 
    authentication_to_outlook
        Authenticates to Outlook as part of the the initialization process to the Microsoft Graph API
    """
    
    def __init__(self, is_initial_use) -> None:    
        """
        Initializes the members variables by retrieving the netrc and yaml file 

        Parameters
        ----------
        is_initial_use
            Indicates whether this is first time running script
        """

        self.credential = self.get_credentials() 
        
        required_attributes = ['client_id', 'tenant_id', 'scope', 'group_members', 'shared_calendar_name']

        #path = os.getenv('AZURE_GRAPH_AUTH')
        #print("path: " + str(path))
        with open("/root/microsoft_graph_auth.yaml", 'r') as file:
            dictionary = yaml.safe_load(file)
            for attribute in required_attributes:
                assert attribute in dictionary, f"{attribute} is not provided in microsoft_graph_auth.yaml"
                setattr(self, attribute, dictionary[attribute])
            self.user_client = self.initialize_graph_for_user_auth(self.client_id, self.tenant_id, self.scope, is_initial_use)        

    def get_credentials(self):
        """
        Retrieves the credential of the user through the netrc file which should include login and password and return a tuple of username and password

        Raised
        ------
        UserWarning 
            A UserWarning is raised when either the login or password doesn't exist in the netrc file 
        """

        netrc_fn = os.getenv('NETRC')
        #print("netrc_fn: "  + str(netrc_fn))
        nrc = netrc.netrc(netrc_fn)
        nrc_parts = nrc.authenticators('OUTLOOK_LOGIN')
        if nrc_parts:
            username = nrc_parts[0]
            password = nrc_parts[2]
        if not username:
            raise UserWarning('Empty username not allowed' )
        if not password:
            raise UserWarning('Empty passwd not allowed')
        return (username, password)

    def initialize_graph_for_user_auth(self, client_id, tenant_id, scope, is_initial_use):
        """
        Initializes the Microsoft Graph API and return user_client object returned by GraphClient 

        Parameters
        ----------
        client_id  : str
            The Application (client) ID that is shown on the Microsfot Azure Project Page
        tenant_id : str
            The Directory (tenant) ID that is shown on the Microsoft Azure Project Page 
        scope : str
            The scope that list the permissions for the project
        is_initial_use
            Indicates whether this is first time running script

        """

        device_code_credential = DeviceCodeCredential(client_id, tenant_id = tenant_id)
        user_client = GraphClient(credential=device_code_credential, scopes=scope.split(' '))


        if (is_initial_use == False): 
            # Creates a background thread to authenticate with Outlook including verifying access code, logging into Outlook, and accepting DUO Push notification
            tmp = sys.stdout
            redirected_output = StringIO()
            sys.stdout = redirected_output
        
            background_thread = threading.Thread(target=self.authentication_to_outlook, args=(redirected_output, tmp))
            background_thread.start()

        self.access_token = device_code_credential.get_token(scope)
        
        return user_client

    def authentication_to_outlook(self, redirected_output, tmp):
        """
        Authenticates to Outlook as part of the the initialization process to the Microsoft Graph API

        Parameters
        ----------
        redirected_output : _io.StringIO'
            The output from console that is redirected to redirected_output
        tmp  : _io.TextIOWrapper
            The pointer to the standard output 
        """

        #sleep 2 second to wait for the prompt with the link and access code to load into std.out
        time.sleep(2)
        sys.stdout = tmp
        
        console_output = redirected_output.getvalue()
        start_index = console_output.find("code")
        end_index = console_output.find(" ", start_index + 5)
        code = console_output[start_index + 5: end_index]

        start_index = console_output.find("http")
        end_index = console_output.find(" ", start_index)
        url = console_output[start_index : end_index]

        try:
            AuthenticateDevice(url, code, self.credential, self.tenant_id)
        except Exception as e:
            print(e)
            print("Error occured - Attempting to log in again")
            AuthenticateDevice(url, code, self.credential, self.tenant_id)

    def get_group_members_calendars(self, user_client, start_date, end_date):
        """
        Retrieves and returns a json object that has the groups member's calendar events

        Parameters 
        ----------
        user_client : msgraph.core._graph_client.GraphClient (Graph Client Object)
        start_date : str
            The start date of the timeframe
        end_date : str
            The end date of the timeframe
        """

        header = {
            'Authorization': str(self.access_token),
            'Content-Type': "application/json",
            'Prefer': "outlook.timezone=\"Central Standard Time\""
        }

        schedules = []
        for key in self.group_members:
            schedules.append(key)
        
        data = {        
            "schedules": schedules,
            "startTime": {
                "dateTime": start_date + "T00:00:00",
                "timeZone": "Central Standard Time"
            },
            "endTime": {
                "dateTime": end_date + "T00:00:00",
                "timeZone": "Central Standard Time"
            },
            "availabilityViewInterval": 1440
        }
        data_as_json = json.dumps(data)
        user_calendar = user_client.post('/me/calendar/getSchedule', data=data_as_json, headers=header)
        return user_calendar.json()

    def get_shared_calendar(self, start_date, end_date):
        """
        Retrieves and returns a json object of the shared calendar events that are within/overlap with between the start_date and end_date

        Parameters 
        ----------
        user_client : msgraph.core._graph_client.GraphClient (Graph Client Object)
        start_date : str
            The start date of the timeframe
        end_date : str
            The end date of the timeframe
        """

        header = {
            'Authorization': str(self.access_token),
            'Content-Type': 'application/json'
        }
        calendars = self.user_client.get('/me/calendars', headers=header)
        list_of_calendars = json.dumps(calendars.json())
        dict_of_calendars = json.loads(list_of_calendars)
    
        for item in dict_of_calendars['value']:
            if item['name'] == self.shared_calendar_name:
                self.shared_calendar_id = item['id']

        #print("Shared calendar id: " + self.shared_calendar_id)

        header = {
            'Authorization': str(self.access_token),
            'Prefer': "outlook.timezone=\"Central Standard Time\""
        }
        
        # This request includes events that start between the start_date and end_date 
        request = '/me/calendars/' + self.shared_calendar_id +'/events' + '?$select=subject,body,start,end,showAs&&$filter=start/dateTime ge ' + '\''+ start_date + '\'' + ' and start/dateTime lt ' + '\'' + end_date + '\''    
        response_one = self.user_client.get(request, headers=header)

        # This request includes events that start before the start_date and end anytime after the start_date 
        request =  '/me/calendars/' + self.shared_calendar_id +'/events' + '?$select=subject,body,start,end,showAs&&$filter=start/dateTime lt ' + '\''+ start_date + '\'' + ' and end/dateTime ge ' + '\'' + start_date + '\''
        response_two = self.user_client.get(request, headers=header)
        
        calendar = response_one.json()

        for item in response_two.json()['value']:
            calendar['value'].append(item)
        
        #print(calendar)
        return calendar


    def process_individual_calendars(self, calendar):
        list_of_events = []
        for member in calendar['value']:
            net_id = member['scheduleId']
            net_id = net_id.split('@')[0]
            #name_of_group_member = self.group_members[member['scheduleId']]
            for event in member['scheduleItems']:
                if event['status'] == 'oof': # For some reason, 'oof' is Outlook's away status. 
                    
                    start_date_time = event['start']['dateTime'].split('T')
                    end_date_time = (event['end']['dateTime']).split('T')

                    start_date = start_date_time[0]
                    end_date = end_date_time[0]
                
                    if (start_date != end_date): # this could mean it's multiday or one single day event
                        self.process_multiday_event(start_date, end_date, start_date_time[1], end_date_time[1], list_of_events, net_id)
                        continue       
        
                    event_status = self.get_event_status(start_date_time[1], end_date_time[1])

                    if (event_status == None):
                        continue

                    event_subject = self.get_event_subject(net_id, event_status)
                        
                    simple_event = SimpleEvent(net_id, event_subject, event_status, start_date)
                    list_of_events.append(simple_event)
      
        # print("Individual calendar: ")
        # print(list_of_events)
        return list_of_events
    
    def process_shared_calendar(self, shared_calendar):

        list_of_events = []
    
        for event in shared_calendar['value']:
            if event['showAs'] == 'oof': 
                start_date_time = event['start']['dateTime'].split('T')
                start_date = start_date_time[0]
    
                subject = event['subject']
                event_identifier = subject.split(' ', 1) # net_id status
                if (len(event_identifier) == 2):
                    status = self.is_valid_status(event_identifier[1])

                    if (status != -1):
                        net_id = event_identifier[0]
                        simple_event = SimpleEvent(net_id, subject, status, start_date)
                        list_of_events.append(simple_event)
        
        # print("shared event: ")
        # print(list_of_events)
        return list_of_events

    def process_multiday_event(self, start_date, end_date, start_time, end_time, list_of_events, net_id): 
            """
            Breaks multiday events into their own day and adding it to date_dict 
            """
            # if an event goes in here, then it's all day because the start date and end date differ by one day so it has to be at least be 1 All Day
            # Automatically All Day 

            start_object = datetime.strptime(start_date,"%Y-%m-%d")
            end_object = datetime.strptime(end_date,"%Y-%m-%d")

            delta = end_object - start_object
    
            diff = (end_object  - start_object ) / delta.days
            
            for i in range(delta.days + 1): # The plus accounts for the last day of the multiday event. Even if it's just one All-Day
                date = (start_object + diff * i).strftime("%Y-%m-%d")

                temp_start_time = start_time
                temp_end_time = end_time

                if (i == 0):
                    temp_end_time = "23:59:59.0000000"
                elif (i == delta.days):
                    temp_start_time = "00:00:00.0000000" 
                else:
                    temp_start_time = "00:00:00.0000000" 
                    temp_end_time = "23:59:59.0000000" 

                event_status = self.get_event_status(temp_start_time, temp_end_time)

                if (event_status == None):
                    continue
                
                event_subject = self.get_event_subject(net_id, event_status)

                simple_event = SimpleEvent(net_id, event_subject, event_status, date)
                list_of_events.append(simple_event)

    def get_event_status(self, start_time, end_time):
        is_AM = self.is_AM(start_time, end_time)
        is_PM = self.is_PM(start_time,end_time)

        if (is_AM == True and is_PM == True):
            return self.Status.OUT
        elif (is_AM == True):
            return self.Status.OUT_AM
        elif (is_PM == True):
            return self.Status.OUT_PM

        return None

    def get_event_subject(self, net_id, event_status):
        # if event_status == -1:
        #     continue
        if event_status == self.Status.OUT:
            return net_id + " OUT"
        elif event_status == self.Status.OUT_AM:
            return net_id + " OUT AM"
        elif event_status == self.Status.OUT_PM:
            return net_id + " OUT PM"
        
        return None

    def is_valid_status(self, status_as_string):
        if status_as_string == "OUT":
            return self.Status.OUT
        elif status_as_string == "OUT AM":
            return self.Status.OUT_AM
        elif status_as_string == "OUT PM":
            return self.Status.OUT_PM

        return -1


    def is_AM(self, start_time, end_time):
        start_time_in_minutes = int(start_time[:2]) * 60 + int(start_time[3:5])
        end_time_in_minutes = int(end_time[:2]) * 60 + int(end_time[3:5])

        # start: 9AM = 9 * 60 = 540
        # end: 11:50AM = 11 * 60 + 50 = 710
        if (start_time_in_minutes <= 540 and end_time_in_minutes >= 710):
            return True
        return False

    def is_PM(self, start_time, end_time):
        start_time_in_minutes = int(start_time[:2]) * 60 + int(start_time[3:5])
        end_time_in_minutes = int(end_time[:2]) * 60 + int(end_time[3:5])

        # start: 1PM = 13 * 60 = 780
        # end: 3:50PM = 15 * 60 + 50 = 950
        if (start_time_in_minutes <= 780 and end_time_in_minutes >= 950):
            return True
        return False


    
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

        parser.add_argument('-s', '--shared', action='store_true', help='Feature to generate report')
        parser.add_argument('-r', '--report', action='store_true', help='Feature to update shared calendar')        
        parser.add_argument('-d', '--dump_json', action='store_true', help='Dump table data to console as json')
        parser.add_argument('-i', '--is_initial_use', action='store_true', help='Indicates whether this is first time running script')        
        parser.add_argument(dest= 'start_date', action='store', help='The start date of the timeframe. date format: YYYY-MM-DD')
        parser.add_argument(dest= 'end_date', action='store', help='The end date of the timeframe. date format: YYYY-MM-DD')

        args = parser.parse_args()
        
        #print(args.start_date, args.end_date, args.shared, args.report)
        return args

        
def sanitize_input(user_args):
    date_format = '%Y-%m-%d'
    dates = [user_args.start_date, user_args.end_date]
    for date in dates:
        try:
            datetime.strptime(date, date_format)
        except ValueError:
            # Should I just raise an error instead?
            assert False, "Incorrect data format, it should be YYYY-MM-DD"
    
    start_object = datetime.strptime(user_args.start_date,"%Y-%m-%d")
    end_object = datetime.strptime(user_args.end_date,"%Y-%m-%d")
    
    assert (end_object - start_object).days >= 0, "start date should start date prior to the end date"    

if __name__ == '__main__':
    # python3 OutlookCalendar.py [start date] [end date]
    # date format: YYYY-MM-DD
    args = process_args()
    #print(args)

    sanitize_input(args)
    
    start_date = args.start_date
    end_date = args.end_date
    
    my_calendar = OutlookCalendar(args.is_initial_use)

    # Retrieves each group member's default calendar 
    
    calendar = my_calendar.get_group_members_calendars(my_calendar.user_client, start_date, end_date)
    shared_calendar = my_calendar.get_shared_calendar(start_date, end_date)
    #print(shared_calendar)
    my_calendar.process_individual_calendars(calendar)
    my_calendar.process_shared_calendar(shared_calendar)
    #print(calendar)

    # counter = 0

    # while (counter <= 5):
    #     print("counter: " + str(counter))
    #     calendar = my_calendar.get_group_members_calendars(my_calendar.user_client, start_date, end_date)
    #     GenerateReport(calendar, my_calendar.group_members).generate("r", start_date, end_date)
    #     time.sleep(10)
    #     counter = counter + 1
    #     print("-------------------------------------------------------")
        



    # if (args.report == True):
    #     print("Generating Report")
    #     # Generates the report 
    #     GenerateReport(calendar, my_calendar.group_members).generate("r", start_date, end_date)


    # if (args.dump_json == True):
    #     print("Dumping Table Data To Console")
    #     GenerateReport(calendar, my_calendar.group_members).generate("r")

    # if (args.shared == True):
    #     print("Updating Shared Calendar")
    #     # Retrieves the shared calendar among the group members 
    #     shared_calendar = my_calendar.get_shared_calendar(start_date, end_date)
    #     #print(shared_calendar)
    #     #print(calendar)
    #     # Updates the shared calendar 
    #     SharedCalendar(calendar, shared_calendar, my_calendar.shared_calendar_id, my_calendar.access_token, my_calendar.user_client, start_date[:4] + start_date[5:7] + start_date[8:])



# pttran - OUT
# pttran - OUT AM
# pttran - OUT PM