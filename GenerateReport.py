import json
from multiprocessing import Event
from signal import ITIMER_REAL
from tabulate import tabulate, SEPARATING_LINE
from datetime import datetime
import collections
from dataclasses import dataclass

@dataclass
class GenerateReport:
    """
    Generates a report of the members' calendars within a start-end timeframe  
    """
    calendar_as_json : dict
    credentials_of_members : dict

    @dataclass
    class UserEvent:
        net_id : str
        status : str

    def generate(self, mode, start_date, end_date):
        filtered_events = self.filter_dates(self.calendar_as_json)
        
        if (mode == "r"):
            self.print_table(filtered_events, start_date, end_date)
        elif (mode == "d"):
            self.dump_calendar_to_json(filtered_events)
        

    def filter_dates(self, calendar):
        """
        Parses the calendar and return a dictionary with key:value of dates and list of events on each day
        """

        # date_dict is a dictionary with keys representing the dates, following the YYYYMMDD format, and each value contains a list of event objects.
        # Within each list, the All-Day and Multi-Day events will be prioritized first. If an event is multiday, then each day in the time span will be made into an event object. (call mutliday_event_hander())
        date_dict = {}
        for member in calendar['value']:
            name_of_group_member = self.credentials_of_members[member['scheduleId']]
            for event in member['scheduleItems']:
                if event['status'] == 'oof': # For some reason, 'oof' is Outlook's away status. 

                    start_date = (event['start']['dateTime']).split('T')
                    end_date = (event['end']['dateTime']).split('T')
                    # Change variable day into a YYYYMMDD format 
                
                    #print("simplified: " + ''.join(start_date[0].split('-')))
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
        
        return collections.OrderedDict(sorted(date_dict.items()))

    def mutliday_event_hander(self, start_day, end_day, date_dict, event, user): 
        """
        Breaks multiday events into their own day and adding it to date_dict 
        """

        # if an event goes in here, then it's all day because the start date and end date differ by one day so it has to be at least be 1 All Day
        # Automatically All Day 

        start_object = datetime.strptime(start_day,"%Y-%m-%d")
        end_object = datetime.strptime(end_day,"%Y-%m-%d")

        delta = end_object - start_object
  
        diff = (end_object  - start_object ) / delta.days
        
        for i in range(delta.days + 1): # The plus accounts for the last day of the multiday event. Even if it's just one All-Day
            day = (start_object + diff * i).strftime("%Y%m%d")
            #print("day: " + day)
            #print("type: " + str(type(day)))
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
        """
        # Problem: We want to keep the length of each column the same as we print out x different tables.
        # The tabulate library doesn't allow to create a fixed length for a column.
        # Solution: Have the title of each column be the a long fixed length, in such a way that the values of the columns 
        # are either less than or equal to to the fixed length

        tabulate.PRESERVE_WHITESPACE = True
        # The max length of the name of the days of the week
        max_length = 9
        start_date = ''.join(start_date.split('-'))
        end_date = ''.join(end_date.split('-'))

        for date, list_of_events in filtered_calendar.items():
            # This condition would make sure that we only show the dates that the user asked for 
            if int(date) < int(start_date) or int(date) >= int(end_date):
                continue
            
            # Figure out the day (Monday, Wednesday, etc) 
            day_of_the_week = (datetime(int(date[:4]), int(date[4:6]), int(date[6:]), 0, 0, 0)).strftime('%A')
            
            num_of_whitespace_to_add = 0 if len(day_of_the_week) == max_length else  max_length - len(day_of_the_week)            
            
            column_one_title = day_of_the_week + " " + date[4:6] + "-" + date[6:] + "-" + date[:4] + (num_of_whitespace_to_add * " ")
            column_two_title = " " * 7

            print(tabulate(list_of_events, headers=[column_one_title, column_two_title], tablefmt="simple")) 
            print("")
        
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
