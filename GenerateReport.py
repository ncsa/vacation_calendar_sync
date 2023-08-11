from datetime import datetime
import collections

def filter_simple_events(simple_events):
    filtered_events = {}
    for event in simple_events:
        if event.date not in filtered_events:
            filtered_events[event.date] = [event]
        else:
            filtered_events[event.date].append(event)
  
    return collections.OrderedDict(sorted(filtered_events.items()))

def print_table(sorted_simple_events):
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
            
                

    
