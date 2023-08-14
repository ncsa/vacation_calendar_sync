#!/usr/bin/python
import SharedCalendar 
import argparse
from datetime import datetime
from SimpleEvent import SimpleEvent
from datetime import timedelta 
import time
import logging
from logging import handlers
import utils
from msal import PublicClientApplication
import IndividualCalendar
import GenerateReport
        
def process_args():
        parser = argparse.ArgumentParser(
            prog = 'vacation_calendar_sync',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description = 'Updates shared calendar among team members using each member\'s calendar with events marked as status \'away\'',
            epilog = 
                '''
Program is controlled using the following environment variables:
    VCS_CONFIG
        path to the yaml configuration file          
                ''')

        parser.add_argument('-s', '--update_shared_calendar', action='store_true', help='Update shared calendar')
        parser.add_argument('-g', '--generate_report', action='store_true', help='Generate a report of the shared calendar')
        parser.add_argument('-d', '--dump_json', action='store_true', help='Dump table data to console as json')
        parser.add_argument('-m', '--manual_update', action='store', nargs=2, help="Manually update the shared calendar with start and end time "+
                            "with format YYYY-MM-DD")
        
        args = parser.parse_args()
        
        return args
   
def sanitize_input(start_date, end_date):    
    """ 
    Sanitizes the user arguments to verify their validity 
    """

    # If the start_date and end_date given by user doesn't fit the format, then the datetime.strptime will 
    # throw its own error
    start_date = datetime.strptime(start_date,"%Y-%m-%d")
    end_date = datetime.strptime(end_date,"%Y-%m-%d")

    # Check whether start date occurs before end_date
    if (end_date - start_date).days < 0:
        raise ValueError('start date should start prior to the end date')
    
    return (start_date, end_date)

def main(configs):
    args = process_args()
    
    start_date = None
    end_date = None
    days_out = timedelta(days=configs['days_out'])
    group_members = None

    # Define the msal public client
    app = PublicClientApplication(client_id=configs['client_id'], authority=f"https://login.microsoftonline.com/{configs['tenant_id']}")

    count = 0
    while True:
        if args.update_shared_calendar or args.generate_report:
            logger.info(f"Updating shared calendar -> count: {count}") 
            today = datetime.today()
            start_date = datetime(year=today.year, month=today.month, day=today.day, hour=0,minute=0)
            end_date = start_date + days_out
        elif args.manual_update:
            logger.info(f"Running manually")
            dates = sanitize_input(args.manual_update[0], args.manual_update[1])
            start_date = dates[0]
            end_date = dates[1]

        # Retrieve the group member emails 
        group_members = utils.get_email_list(configs['group_name'], configs['email_list_update_interval'])

        # Get access token
        access_token = utils.acquire_access_token(app, configs['scopes'])

        # Retrieve the individual calendar and process it 
        individual_calendars_events = []
        grouping = 10
        
        for group in [group_members[i : i + grouping] for i in range(0, len(group_members), grouping)]:
            individual_calendars = IndividualCalendar.get_individual_calendars(start_date, end_date, group, access_token)
            individual_calendars_events.extend(IndividualCalendar.process_individual_calendars(individual_calendars, start_date, end_date))
                
        # Retrieve the shared calendar and process it 
        shared_calendar_id = SharedCalendar.get_shared_calendar_id(configs['shared_calendar_name'], access_token)
        shared_calendar = SharedCalendar.get_shared_calendar(shared_calendar_id, start_date, end_date, access_token)
        shared_calendar_events, event_ids = SharedCalendar.process_shared_calendar(shared_calendar, group_members)

        # Update the shared calendar
        SharedCalendar.update_shared_calendar(individual_calendars_events, shared_calendar_events, event_ids, shared_calendar_id, configs['category_name'], configs['category_color'], access_token)

        if args.manual_update: break
        if args.generate_report:
            shared_calendar_id = SharedCalendar.get_shared_calendar_id(configs['shared_calendar_name'], access_token)
            shared_calendar = SharedCalendar.get_shared_calendar(shared_calendar_id, start_date, end_date, access_token)
            shared_calendar_events, event_ids = SharedCalendar.process_shared_calendar(shared_calendar, group_members)
            GenerateReport.print_table(GenerateReport.filter_simple_events(shared_calendar_events))
            break
        
        count = count + 1
        time.sleep(configs['update_interval'])
            
if __name__ == '__main__':
    configs = utils.get_configurations()
    
    formater = logging.Formatter('%(name)s:%(asctime)s:%(filename)s:%(levelname)s:%(message)s')

    rotate_file_handler_info = handlers.RotatingFileHandler(f"{configs['vcs_directory']}vcs.log", mode='a', maxBytes=2000000, backupCount=2)
    rotate_file_handler_info .setFormatter(fmt=formater)
    rotate_file_handler_info .setLevel(logging.DEBUG)

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(rotate_file_handler_info)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(fmt=logging.Formatter('%(name)s:%(asctime)s:%(filename)s:%(levelname)s:%(message)s'))
    logger.addHandler(stream_handler)

    main(configs)