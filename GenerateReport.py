import json
from multiprocessing import Event
from signal import ITIMER_REAL
from tabulate import tabulate, SEPARATING_LINE
from datetime import datetime
import collections
from dataclasses import dataclass
from SimpleEvent import SimpleEvent

@dataclass
class GenerateReport:
    """
    Generates a report of the members' calendars within a start-end timeframe  
    """
    calendar_as_json : dict
    
    def generate(self, mode, start_date, end_date):
        filtered_events = self.filter_events(self.calendar_as_json)
        
        if (mode == "r"):
            self.print_table(filtered_events, start_date, end_date)
        elif (mode == "d"):
            self.dump_calendar_to_json(filtered_events)
        
    def filter_events(self, shared_calendar_events):

        # a dictionary with the key as the date (YYYY-MM-DD) and a list of simple events occuring on that day
        date_to_events = {}
        
        for event in shared_calendar_events[0]:    
            if event.date in date_to_events:
                date_to_events[event.date].append(event)
            else:
                date_to_events[event.date] = [event]
        
        date_to_events = collections.OrderedDict(sorted(date_to_events.items()))
        
        return date_to_events

    def dump_calendar_to_json(self, events_by_date_dict, start_date, end_date):
        """
        Dumps the events_by_date_dict as json onto console 
        """
        #for date, events_on_date in events_by_date_dict.items():
        events = []

        start_date = ''.join(start_date.split('-'))
        end_date = ''.join(end_date.split('-'))

        for date, events_on_date in events_by_date_dict.items():
            # This condition would make sure that we only show the dates that the user asked for 
            tmp_date = ''.join(date.split('-'))
            if int(tmp_date) < int(start_date) or int(tmp_date) >= int(end_date):
                continue

            for event in events_on_date:
                events.append([event.net_id, event.subject, event.date])
            
        print(json.dumps(events))

    def print_table(self, events_by_date_dict, start_date, end_date):
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

        for date, events in events_by_date_dict.items():
            # This condition would make sure that we only show the dates that the user asked for 
            tmp_date = ''.join(date.split('-'))
            if int(tmp_date) < int(start_date) or int(tmp_date) >= int(end_date):
                continue
            
            # Figure out the day (Monday, Wednesday, etc) 
            day_of_the_week = (datetime(int(tmp_date[:4]), int(tmp_date[4:6]), int(tmp_date[6:]), 0, 0, 0)).strftime('%A')
            
            num_of_whitespace_to_add = 0 if len(day_of_the_week) == max_length else max_length - len(day_of_the_week)            
            
            column_one_title = day_of_the_week + " " + tmp_date[4:6] + "-" + tmp_date[6:] + "-" + tmp_date[:4] + (num_of_whitespace_to_add * " ")
            column_two_title = " " * 7
            
            print(tabulate(events, headers=["net_id", column_one_title, column_two_title], tablefmt="simple")) 
            print("")