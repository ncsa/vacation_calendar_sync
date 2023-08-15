from datetime import datetime
import collections
import utils
import IndividualCalendar
def filter_simple_events(simple_events):
    filtered_events = {}
    for event in simple_events:
        if event.date not in filtered_events:
            filtered_events[event.date] = [event]
        else:
            filtered_events[event.date].append(event)
  
    return collections.OrderedDict(sorted(filtered_events.items()))

def print_table(simple_events):
    sorted_simple_events = filter_simple_events(simple_events)
    for key in sorted_simple_events:
        line = f"{key.date()},"
        for count, event in enumerate(sorted_simple_events[key]):
            event_attributes = event.subject.split(' ')
            if len(event_attributes) == 2:
                line = line + event_attributes[0] 
            else:
                line = line + event_attributes[0] + " " + event_attributes[2]

            if count < len(sorted_simple_events[key]) - 1:
                line = line + ","
        print(line)
            
def generate_report_for_specified_group(group_name, start_date, end_date, access_token):
    emails = utils.get_email_list_from_ldap(group_name)
    calendars = IndividualCalendar.get_individual_calendars(start_date, end_date, emails, access_token)
    events = IndividualCalendar.process_individual_calendars(calendars, start_date, end_date)
    print_table(events)



    