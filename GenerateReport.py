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

# done

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

    class UserEvent:
        """
        A class that represent each event 

        Attributes
        ----------
        net_id : str
            The net_id of the owner of the event
        status : str
            The status set for the event
        subject : str
            The name of the event
        start_date : tuple
            A tuple that includes the date (str) and time (str) of the start of the event
        end_date : str
            A tuple that includes the date (str) and time (str) of the end of the event

        Methods 
        -------
        date_parser
            Parses the date into a tuple of date (str) and time (str) and return the tuple
        get_event
            Return a list of Event attributes 
        """
        def printEvent(self):

            print('event: ' + self.subject)
            print('status: ' + self.status)
            print('date: ' +  self.start_date[0])
            print('start on: ' + self.start_date[1])
            print('end on: ' + self.end_date[1])
            print("*************************")
            
        def __init__(self, event, user) -> None:
            """
            Parameters
            ----------
            event : dictionary 
                A dictionary  with information pertaining to the event 
            user : str
                Name of the user with this event 
            """

            self.net_id = user
            self.status = event['status']
            self.subject = event['subject']
            self.start_date = self.date_parser(event['start']['dateTime'])
            self.end_date = self.date_parser(event['end']['dateTime'])

            # print("net_id type: " + str(type(self.net_id)))
            # print("status type: " + str(type(self.status)))
            # print("subject type: " + str(type(self.subject)))
            # print("-------------------------")

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

        def get_event(self):
            """
            Return a list of Event attributes 
            """

            event = [
                self.net_id,
                self.status,
                self.subject,
                self.start_date,
                self.end_date
            ]
            return event

    
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
            name = self.group_members[net_id]
            for item in member['scheduleItems']:
                if item['status'] == 'busy': 
                    start_date = item['start']['dateTime']
                    # Change variable day into a YYYYMMDD format 
                    day = start_date[:10]
                    day = (day[:4] + day[5:7] + day[8:])
        
                    if (item['start']['dateTime'][0:10] != item['end']['dateTime'][:10]): # this could mean it's multiday or one single day event
                        self.mutliday_event_hander(item['start']['dateTime'][0:10], item['end']['dateTime'][:10], date_dict, item, name)
                        continue
                    
                    if day in date_dict:  
                        # member_calendar_on_day is a dictionary with key as NetID and a list of Event objects as value. 
                        event = self.UserEvent(item, name)
                        date_dict[day].append(event)
                    else:
                        event = self.UserEvent(item, name)
                        date_dict[day] = [event]

        #print(self.dump_calendar_to_json(event_days_inorder))
        # self.print_table(event_days_inorder)
        return collections.OrderedDict(sorted(date_dict.items()))
        
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
            for item in value:
                #print("here")
                calendar_dict[key].append(item.get_event())
        
        calendar_as_json = json.dumps(calendar_dict)
        print(calendar_as_json)        
        
    def calculate_mutliday_event_duration(self, start, end):
        """
        Calculates the time duration between two dates in terms of days and return the duration as a str in X HR format 

        Parameters:
        ----------
        start : str 
            The start date of the multiday event 
        end: str
            The end date of the multiday event
        """

        duration = ""
        start_hour = int(start[:2])
        end_hour = int(end[:2])
        start_minute = int(start[3:]) + (start_hour * 60)
        end_minute = int(end[3:]) + (end_hour * 60)
        diff_in_total_minutes = end_minute - start_minute

        hour = diff_in_total_minutes // 60
        minute = diff_in_total_minutes % 60

        if (minute > 0):
            hour = hour + 1

        duration = str(hour) + " HR"
        return duration

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
            #print(header)
            if (first_row == False):
                fake_header = [day + " " + key[4:6] + "-" + key[6:] + "-" + key[:4], ""]
                first_row = True
            else:
                table.append(header)
                table.append(SEPARATING_LINE)
            for event in value:
                if event.start_date[1] == "00:00" and event.end_date[1] == "00:00":
                    #print("LINE 168: TIME: " + str(event.start_date[1]) + event.subject)
                    row = [event.net_id, "All Day"]    
                else:
                    duration = self.calculate_mutliday_event_duration(str(event.start_date[1]), str(event.end_date[1]))
                    row = [event.net_id, str(event.start_date[1]) + ' - ' + str(event.end_date[1]) + " (" + duration + ")"]
                table.append(row)

            table.append([])
        
        #self.json_result = json.dumps(table)
        print(tabulate(table, headers=fake_header, tablefmt="simple"))

    def mutliday_event_hander(self, start, end, date_dict, item, user): 
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

        # if an event goes in here, then it's all day

        start_object = datetime.strptime(start,"%Y-%m-%d")
        end_object = datetime.strptime(end,"%Y-%m-%d")

        delta = end_object - start_object
  
        diff = (end_object  - start_object ) / delta.days
        for i in range( delta.days):
            day = (start_object + diff * i).strftime("%Y%m%d")
            if day in date_dict:
                event = self.UserEvent(item, user)
                date_dict[day].insert(0, event)
            else:
                event = self.UserEvent(item, user)
                date_dict[day] = [event]
                
    