from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta 

@dataclass
class SimpleEvent:
    net_id : str 
    subject : str # Our own formatted subject "[netID] [OUT/OUT AM/OUT PM]"
    date : datetime 
    
    # Returns a list of Simple Events
    # The list will return 1 item if the event is a one day event 
    # Otherwise, the length of the list is equal to length of the event in terms of days
    @classmethod 
    def create_event_for_individual_calendars(cls, event, user_start_date, net_id):
        events = []
        start = SimpleEvent.make_datetime(event['start']['dateTime'])
        end = SimpleEvent.make_datetime(event['end']['dateTime'])

        if start.date() == end.date():
            if SimpleEvent.is_event_valid(user_start_date, start, end):
                return [cls(net_id, SimpleEvent.get_event_subject(start, end, net_id), start)]
            return []

        # if an event goes in here, then it's all day because the start date and end date differ by one day so it has to be at least be 1 All Day
        # Automatically All Day 
        dates_interval = end - start
        
        for i in range(dates_interval.days + 1): # The plus accounts for the last day of the multiday event. Even if it's just one All-Day
            
            #new_date = start + timedelta(days=i)
            
            # new_start and new_end are just changing the time
            new_start = start + timedelta(days=i)
            new_end = start + timedelta(days=i)
            
            # Adjust the time so that we can create an accurate subject for the split up event
            if (i == 0):
                new_end = new_end.replace(hour=23,minute=59,second=59)
            elif (i == dates_interval.days):
                new_start = new_start.replace(hour=0,minute=0,second=0)
            else:
                new_start = new_start.replace(hour=0,minute=0,second=0)
                new_end = new_end.replace(hour=23,minute=59,second=59)

            if SimpleEvent.is_event_valid(user_start_date, new_start, new_end):
                events.append(cls(net_id, SimpleEvent.get_event_subject(new_start, new_end, net_id), new_start))
                
        return events

    
    @classmethod 
    def create_event_for_shared_calendar(cls, event):
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
        is_AM = SimpleEvent.is_AM(start, end)
        is_PM = SimpleEvent.is_PM(start,end)

        if (is_AM == True and is_PM == True):
            return net_id + " OUT"
        elif (is_AM == True):
            return net_id + " OUT AM"
        elif (is_PM == True):
            return net_id + " OUT PM"    
    
    @staticmethod    
    def is_event_valid(user_start, start, end):
        if user_start <= start and (SimpleEvent.is_AM(start, end) or SimpleEvent.is_PM(start,end)):
            return True
        return False
    

    @staticmethod    
    # TODO: Have the user input the time values in the yaml file
    # is_AM assumes that start and end are on the same day, so it's just checking their times 
    def is_AM(start, end):
        # start: 9AM = 9 * 60 = 540
        # end: 11:50AM = 11 * 60 + 50 = 710
        if ((start.hour * 60) + start.minute <= 540 and (end.hour * 60) + end.minute >= 710):
            return True
        return False
    
    @staticmethod   
    # start and end are datetime objects 
    # TODO: Have the user input the time values in the yaml file
    # is_PM assumes that start and end are on the same day, so it's just checking their times 
    def is_PM(start, end):
        # start: 1PM = 13 * 60 = 780
        # end: 3:50PM = 15 * 60 + 50 = 950
        # 1:00 PM 3:50 PM
        if ((start.hour * 60) + start.minute <= 780 and (end.hour * 60) + end.minute >= 950):
            return True 
        return False
    
    @staticmethod
    def make_datetime(date):
       
        if "T" in date:
            # The format of date is 2023-03-18T00:00:00.0000000
            # The split is to remove the microseconds b/c datetime only take microseconds up to 6 digits, 
            # but the response date format has 7 digits for microseconds
            return datetime.strptime(date.split('.')[0], "%Y-%m-%dT%H:%M:%S")
        else:
            return datetime.strptime(date, "%Y-%m-%d")


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

# print(SimpleEvent.create_event_for_individual_calendars(event, "2023-03-19", "pttran3"))