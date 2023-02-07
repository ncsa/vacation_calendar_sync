#!/usr/bin/python
from tracemalloc import start
import sys
import json
from azure.identity import DeviceCodeCredential
from msgraph.core import GraphClient
from base64 import decode
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


# done

class OutlookCalendar:
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

        # self.credential = self.get_credentials() 
        # try:
        #     stream = open("/root/microsoft_graph_auth.yaml", 'r')
        # except:
        #     raise UserWarning('microsoft_graph_auth.yaml does not exist')
        # else:
        #     dictionary = yaml.safe_load(stream)
        #     if 'client_id' in dictionary:
        #         self.CLIENT_ID = dictionary['client_id']
        #     else:
        #         raise UserWarning('client_id is not provided in microsoft_graph_auth.yaml')
            
        #     if 'tenant_id' in dictionary:
        #         self.TENANT_ID = dictionary['tenant_id']
        #     else:
        #         raise UserWarning('tenant_id is not provided in microsoft_graph_auth.yaml')
            
        #     if 'scope' in dictionary:
        #         self.graphUserScopes = dictionary['scope']
        #     else:
        #         raise UserWarning('scope is not provided in microsoft_graph_auth.yaml')
            
        #     if 'group_members' in dictionary:
        #         self.group_members = dictionary['group_members'] # this would be a dictionary

        #     if 'shared_calendar_name' in dictionary:
        #         self.shared_calendar_name = dictionary['shared_calendar_name'] 
        #         # TODO: What if the user doesn't provide shared_calendar_name. What if they just want a report and not the shared calendar feature 
           
            # self.user_client = self.initialize_graph_for_user_auth(self.CLIENT_ID, self.TENANT_ID, self.graphUserScopes, is_initial_use)
            
            #self.keywords = ['vacation', 'break', 'timeoff', 'PTO', 'sick']
        

    def get_credentials(self):
        """
        Retrieves the credential of the user through the netrc file which should include login and password and return a tuple of username and password

        Raised
        ------
        UserWarning 
            A UserWarning is raised when either the login or password doesn't exist in the netrc file 
        """

        netrc_fn = os.getenv('NETRC')
        print("netrc_fn: "  + str(netrc_fn))
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
    print(args)

    sanitize_input(args)
    
    start_date = args.start_date
    end_date = args.end_date
    
    my_calendar = OutlookCalendar(args.is_initial_use)

    # Retrieves each group member's default calendar 
    calendar = my_calendar.get_group_members_calendars(my_calendar.user_client, start_date, end_date)

    if (args.report == True):
        print("Generating Report")
        # Generates the report 
        GenerateReport(calendar, my_calendar.group_members, "r", start_date, end_date)

    if (args.dump_json == True):
        print("Dumping Table Data To Console")
        GenerateReport(calendar, my_calendar.group_members, "d")

    if (args.shared == True):
        print("Updating Shared Calendar")
        # Retrieves the shared calendar among the group members 
        shared_calendar = my_calendar.get_shared_calendar(start_date, end_date)
        # Updates the shared calendar 
        SharedCalendar(calendar, shared_calendar, my_calendar.shared_calendar_id, my_calendar.access_token, my_calendar.user_client, start_date[:4] + start_date[5:7] + start_date[8:])
