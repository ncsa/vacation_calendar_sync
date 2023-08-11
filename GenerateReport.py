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
        print("--------------------")
        print(key.date())
        print("--------------------")       
        for event in sorted_simple_events[key]:
            print(event.subject)
    
