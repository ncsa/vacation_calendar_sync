from dataclasses import dataclass
from datetime import datetime
from datetime import time
from datetime import timedelta 
import utils

# If a multiday event starts at 12:00 AM on a Monday and ends at 5PM on a Wednesday. Then only two events will be created: 
# ALL-DAY for Monday and Tuesday, but no events for Wednesday 
# If a multiday event starts at 11:00 AM on a Monday and ends at 5PM on a Wednesday. Then only three events will be created: 
# ALL-DAY for Tuesday, OUT AM for Monday and OUT PM for Wednesday 
configs = utils.get_configurations()
# AM_config = configs['AM_config']
# PM_config = configs['PM_config']
start_of_workday = configs['start_of_work_day']
end_of_workday = configs['end_of_work_day']
start_of_lunch = configs['start_of_lunch']
end_of_lunch = configs['end_of_lunch']
duration = configs['duration']

@dataclass
class SimpleEvent:
    net_id : str 
    subject : str # Our own formatted subject "[netID] [OUT/OUT AM/OUT PM]"
    date : datetime 
    
    # Returns a list of Simple Events
    # The list will return 1 item if the event is a one day event 
    # Otherwise, the length of the list is equal to length of the event in terms of days
    @classmethod 
    def create_event_for_individual_calendars(cls, event, start_date, end_date, net_id):
        '''
        Create SimpleEvents and returns a list of SimpleEvents using events from individual calendars

        Args:
            event (dict): contains the information about the event
            start_date (datetime): the start date given by the user (today's date)
            net_id (str): the netid of owner of the event 

        Returns:
            A list of SimpleEvents
        '''

        events = []
        # TODO: Change the variable names to make them more specific
        start = SimpleEvent.make_datetime(event['start']['dateTime'])
        end = SimpleEvent.make_datetime(event['end']['dateTime'])

        if start.date() == end.date():
            if SimpleEvent.is_event_valid(start_date, end_date, start, end):
                return [cls(net_id, SimpleEvent.get_event_subject(start, end, net_id), start)]
            return []

        # if an event goes in here, then it's all day because the start date and end date differ by one day so it has to be at least be 1 All Day
        # Automatically All Day 
        dates_interval = end - start
        
        add_on = 0
        remaining_hours = dates_interval.seconds // 3600
 
        if (remaining_hours!= 0):
            add_on = add_on + 1
        
        # if (start.time() >= )

        midnight_start_time  = time(0, 0, 0, 0)   

        if (start.time() != midnight_start_time and end.time() <= start.time()):
            add_on = add_on + 1        

        for i in range(dates_interval.days + add_on): # The plus accounts for the last day of the multiday event. Even if it's just one All-Day
            
            #new_date = start + timedelta(days=i)
            
            # new_start and new_end are just changing the time
            new_start = start + timedelta(days=i)
            new_end = end + timedelta(days=i)
            new_end = new_end.replace(year=new_start.year, month=new_start.month, day=new_start.day)
            
            # Adjust the time so that we can create an accurate subject for the split up event
            # Manipulating the time for the simple event here

            if (i == 0):
                new_end = new_end.replace(hour=23,minute=59,second=59)
            elif (i == dates_interval.days + add_on - 1):
                new_start = new_start.replace(hour=0,minute=0,second=0)
                if (new_end.time() == midnight_start_time):
                    new_end = new_end.replace(hour=23,minute=59,second=59)
            else:
                new_start = new_start.replace(hour=0,minute=0,second=0)
                new_end = new_end.replace(hour=23,minute=59,second=59)

            if SimpleEvent.is_event_valid(start_date, end_date, new_start, new_end):
                events.append(cls(net_id, SimpleEvent.get_event_subject(new_start, new_end, net_id), new_start))
                
        return events

    
    @classmethod 
    def create_event_for_shared_calendar(cls, event, net_ids):
        '''
        Create a SimpleEvent and returns it using event from the shared calendar

        Args:
            event (dict): contains the information about the event
        '''
        temp_net_ids = []
        for net_id in net_ids:
            temp_net_ids.append(net_id.split("@")[0])

        net_ids = temp_net_ids
        
        start = SimpleEvent.make_datetime(event['start']['dateTime'])
        subject = event['subject']
        event_identifier = subject.split(' ', 1) # (net_id, status)
        # event_identifier[1] in valid_subjects 
        if (len(event_identifier) == 2 and (event_identifier[1] == "OUT" or event_identifier[1] == "OUT AM" or  event_identifier[1] == "OUT PM")):
            simple_event = cls(event_identifier[0], subject, start)
            return simple_event

    
    @staticmethod    
    # get_event_subject assumes that start and end are on the same day, so it's just checking their times to create the subject
    def get_event_subject(start, end, net_id):
        '''
        Creates an event subject for the shared calendar event based on the start and end time given by the user

        Args:
            start (datetime): A datetime object of the event's start time
            end (datetime): A datetime object of the event's end time
            net_id (str): the netid of owner of the event  
        
        Returns:
            The subject of the shared calendar event as a str
        '''

        is_AM = SimpleEvent.is_AM(start, end)
        is_PM = SimpleEvent.is_PM(start,end)

        if (is_AM == True and is_PM == True):
            return net_id + " OUT"
        elif (is_AM == True):
            return net_id + " OUT AM"
        elif (is_PM == True):
            return net_id + " OUT PM"    
    
    @staticmethod    
    def is_event_valid(user_start, user_end, start, end):
        '''
        Verify whether the event duration fit within the specified start and end time

        Args:
            user_start (datetime): The start time given by user
            start (datetime): A datetime object of the event's start time
            end (datetime): A datetime object of the event's end time

        Returns:
            True if event is a valid event
            False if not
        '''

        # if user_start <= start and (SimpleEvent.is_AM(start, end) or SimpleEvent.is_PM(start,end)):
        #     return True
        # return False

        if (user_start <= start and user_end > start) and (SimpleEvent.is_AM(start, end) or SimpleEvent.is_PM(start,end)):
            return True
        return False
    
    @staticmethod
    def make_datetime(date):
        '''
        Create and return a datetime object given a date (YYYY-MM-DD)

        Args:
            date (str): The given date in the form YYYY-MM-DD

        Returns:
            A datetime object representing the date
        '''
        
        if "T" in date:
            # The format of date is 2023-03-18T00:00:00.0000000
            # The split is to remove the microseconds b/c datetime only take microseconds up to 6 digits, 
            # but the response date format has 7 digits for microseconds
            return datetime.strptime(date.split('.')[0], "%Y-%m-%dT%H:%M:%S")
        else:
            return datetime.strptime(date, "%Y-%m-%d")
        
    @staticmethod
    def is_AM(start, end):
        '''
        Verify whether the event duration fit within the AM specification

        Args:
            start (datetime): A datetime object of the event's start time
            end (datetime): A datetime object of the event's end time

        Returns: 
            True if the event is AM
            False if not
        '''

        start_time = (start.hour * 60) + start.minute
        end_time= (end.hour * 60) + end.minute

        if start_time > start_of_lunch or end_time < start_of_workday:
            return False

        if start_time < start_of_workday:
            start_time = start_of_workday
        
        if end_time > start_of_lunch:
            end_time = start_of_lunch
        
        if end_time - start_time >= duration:
            return True
        return False

    @staticmethod
    def is_PM(start, end):
        '''
        Verify whether the event duration fit within the PM specification

        Args:
            start (datetime): A datetime object of the event's start time
            end (datetime): A datetime object of the event's end time

        Returns: 
            True if the event is PM
            False if not
        '''
    
        start_time = (start.hour * 60) + start.minute
        end_time= (end.hour * 60) + end.minute

        if start_time > end_of_workday or end_time < end_of_lunch:
            return False

        if start_time < end_of_lunch:
            start_time= end_of_lunch
        
        if end_time > end_of_workday:
            end_time = end_of_workday

        if end_time - start_time >= duration:
            return True
        return False

# event = {
# 			'isPrivate': False,
# 			'status': 'oof',
# 			'subject': 'All Day Test',
# 			'location': '',
# 			'isMeeting': False,
# 			'isRecurring': False,
# 			'isException': False,
# 			'isReminderSet': True,
# 			'start': {
# 				'dateTime': '2023-03-18T00:00:00.0000000',
# 				'timeZone': 'Central Standard Time'
# 			},
# 			'end': {
# 				'dateTime': '2023-03-22T00:00:00.0000000',
# 				'timeZone': 'Central Standard Time'
# 			}
# 		}


