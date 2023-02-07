from dbm import dumb
from email import header
import json
from mimetypes import init
from multiprocessing import Event
from signal import ITIMER_REAL
from tracemalloc import start
from tabulate import tabulate, SEPARATING_LINE
from datetime import date, datetime
import collections
import copy
from dataclasses import dataclass

class GenerateReport:
    """
    Generates a report of the members' calendars within a start-end timeframe 

    Attributes
    ----------
    calendar : dictionary 
        A json dictionary of the events occuring within the start-end timeframe 
    group_members: dictionary 
        A dictionary with key:value pair of name and netid of the team members 
    

    Methods
    -------
    date_parser
        Parses the date into a tuple of date (str) and time (str) and return the tuple
    filter_dates
        Parses the calendar and return a dictionary with key:value of dates and list of events on each day
    dump_calendar_to_json
        Dumps the filtered_calendar as json onto console 
    calculate_mutliday_event_duration
        Calculates the time duration between two dates in terms of days and return the duration as a str in X HR format 
    print_table
        Print out the report
    mutliday_event_hander
        Breaks multiday events into their own day and adding it to date_dict     
    """
    @dataclass
    class UserEvent:
        net_id : str
        status : str
        #start_date : str
        #end_date : str
    
    def __init__(self,calendar, group_members, mode, start_date, end_date) -> None:
        """
        Parameters
        ----------
        calendar : dictionary 
            A json dictionary of the events occuring within the start-end timeframe 
        group_members: dictionary 
            A dictionary with key:value pair of name and netid of the team members 
        mode: str 
            Either Generate Report (r) mode or Dump Json (d) mode 
        start_date : str
            The start date of the timeframe (YYYY-MM-DD)
        end_date : str
            The end date of the timeframe (YYYY-MM-DD)
        """
        #print(calendar)
        
        self.calendar = calendar
        self.group_members = group_members
        events = self.filter_dates(self.calendar)
        
        if (mode == "r"):
            self.print_table(events, start_date, end_date)
        elif (mode == "d"):
            self.dump_calendar_to_json(events)

    def filter_dates(self, calendar):
        """
        Parses the calendar and return a dictionary with key:value of dates and list of events on each day

        calendar : json dictionary
            A json dictionary of the events occuring within the start-end timeframe 
        """

        # date_dict is a dictionary with keys representing the dates, following the YYYYMMDD format, and each value contains a list of event objects.
        # Within each list, the All-Day and Multi-Day events will be prioritized first. If an event is multiday, then each day in the time span will be made into an event object. (call mutliday_event_hander())
        date_dict = {}
        for member in calendar['value']:
            net_id = member['scheduleId']
            name_of_group_member = self.group_members[net_id]
            for event in member['scheduleItems']:
                if event['status'] == 'oof': # For some reason, 'oof' is Outlook's away status. 
                    start_date = (event['start']['dateTime']).split('T')
                    end_date = (event['end']['dateTime']).split('T')
                    # Change variable day into a YYYYMMDD format 
                
                    print("simplified: " + ''.join(start_date[0].split('-')))
                    start_day = ''.join(start_date[0].split('-'))
                
                    if (start_date[0] != end_date[0]): # this could mean it's multiday or one single day event
                        self.mutliday_event_hander(start_date[0], end_date[0], date_dict, event, name_of_group_member)
                        continue
                    
                    event_status = self.retrieve_event_status(start_date[1], end_date[1])
                    if event_status == None:
                        continue
                  
                    event_as_object = self.UserEvent(name_of_group_member, event_status)

                    if start_day in date_dict:  
                        # member_calendar_on_day is a dictionary with key as NetID and a list of Event objects as value. 
                        date_dict[start_day].append(event_as_object)
                    else:
                        date_dict[start_day] = [event_as_object]

        #print(self.dump_calendar_to_json(event_days_inorder))
        # self.print_table(event_days_inorder)
        return collections.OrderedDict(sorted(date_dict.items()))

    def mutliday_event_hander(self, start, end, date_dict, event, user): 
        """
        Breaks multiday events into their own day and adding it to date_dict 

        Parameters
        ----------

        start : str
            The start date of the multiday event 
        end : str
            The end date of the multiday event 
        date_dict : dictionary 
            A dictionary with key:value pair of dates and list of UserEvent objects 
        item: dictionary
            A dictionary  with information pertaining to the event 
        user : str 
            Name of the user with this event 
        """

        # if an event goes in here, then it's all day because the start date and end date differ by one day so it has to be at least be 1 All Day
        # Automatically All Day 

        start_object = datetime.strptime(start,"%Y-%m-%d")
        end_object = datetime.strptime(end,"%Y-%m-%d")

        delta = end_object - start_object
  
        diff = (end_object  - start_object ) / delta.days
        
        for i in range(delta.days + 1): # The plus accounts for the last day of the multiday event. Even if it's just one All-Day
            day = (start_object + diff * i).strftime("%Y%m%d")

            start_date = event['start']['dateTime'].split('T')
            end_date = event['end']['dateTime'].split('T')

            start_time = start_date[1]
            end_time = end_date[1]
            if (i == 0):
                end_time = "23:59:59.0000000"
            elif (i == delta.days):
                start_time = "00:00:00.0000000" 
            else:
                start_time = "00:00:00.0000000" 
                end_time = "23:59:59.0000000" 

            event_status = self.retrieve_event_status(start_time, end_time)
            if event_status == None:
                continue
         
            event_as_object = self.UserEvent(user, event_status)
            if day in date_dict:
                date_dict[day].insert(0, event_as_object)
            else:
                date_dict[day] = [event_as_object]
        
    def dump_calendar_to_json(self, filtered_calendar):
        """
        Dumps the filtered_calendar as json onto console 

        Parameters
        ----------
        filtered_calendar : dictionary 
            A sorted dictionary of the events occuring within the start-end timeframe 
        """

        calendar_dict = {}

        for key, value in filtered_calendar.items():
            events = []
            calendar_dict[key] = events
            for event in value:
                calendar_dict[key].append(event.net_id, event.status)
        
        calendar_as_json = json.dumps(calendar_dict)
        print(calendar_as_json)        

    def print_table(self, filtered_calendar, start_date, end_date):
        """
        Prints out the report 

        Parameters
        ----------
        filtered_calendar
            A sorted dictionary of the events occuring within the start-end timeframe 
        start_date : str
            The start date of the timeframe (YYYY-MM-DD)
        end_date : str
            The end date of the timeframe (YYYY-MM-DD)
        """
        
        first_row = False
        fake_header = []
        table = []

        start_date = start_date[:4] + start_date[5:7] + start_date[8:]
        end_date = end_date[:4] + end_date[5:7] + end_date[8:]
        
        for key, value in filtered_calendar.items():
            if int(key) < int(start_date) or int(key) >= int(end_date):
                continue
            
            date = datetime(int(key[:4]), int(key[4:6]), int(key[6:]), 0, 0, 0)
            day = date.strftime('%A')
            header = [day + " " + key[4:6] + "-" + key[6:] + "-" + key[:4], ""]

            if (first_row == False):
                fake_header = [day + " " + key[4:6] + "-" + key[6:] + "-" + key[:4], ""]
                first_row = True
            else:
                table.append(header)
                table.append(SEPARATING_LINE)
            for event in value:
                row = [event.net_id, event.status]
                table.append(row)

            table.append([])
        
        #self.json_result = json.dumps(table)
        print(tabulate(table, headers=fake_header, tablefmt="simple")) 
                
    def is_AM(self, start_time, end_time):
        #start_time = event['start']['dateTime'][11:16]
        start_time_in_minutes = int(start_time[:2]) * 60 + int(start_time[3:5])
        #end_time = event['end']['dateTime'][11:16]
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
        
    def retrieve_event_status(self, start_time, end_time):
        is_AM = self.is_AM(start_time, end_time)
        is_PM = self.is_PM(start_time,end_time)

        event_status = None
        if (is_AM == True and is_PM == True):
            event_status = "OUT"
        elif (is_AM == True):
            event_status = "OUT AM"
        elif (is_PM == True):
            event_status = "OUT PM"

        return event_status
