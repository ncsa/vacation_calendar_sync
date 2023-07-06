# Vacation Calendar Sync
- Generate a report of members are are "away" based on their Outlook Calendar within a start-end timeframe. 
- Update shared calendar to synchronize with members' calendars with events that are "away". 

# Setup

Microsoft Azure Project Config (`/root/vacation_calendar_sync_config.yaml`)
``` yaml
---
client_id : '...'
tenant_id : '...'
scope : 'user.read calendars.readwrite https://graph.microsoft.com/offline_access'
group_members : 
    'net_id_1' : 'name_1'
    'net_id_2' : 'name_2'
shared_calendar_name : '...'
logging_file_path : '...'
AM_config :
    start : 540 
    end : 710
PM_config :
    start : 780
    end : 950
days_out : 14
update_interval : 900
...
```
Can retrieve `client_id` and `tenant_id` from the Azure App Registration page

`logging_file_path` is the path where log files can be written onto the host machine starting at the root

`AM_config` and `PM_config` has values in minutes. The event starts before the start and ends after the end for AM_config and PM_config

`days_out` indicates the stretch of time that the program will update on the shared calendar relative to the start date

`update_interval` indicates how often the program run in minutes


# Netrc setup (`/home/.ssh/netrc`)
``` 
machine OUTLOOK_LOGIN
login ...
password ...
```

<!-- ## Pull Image from DockerHub 
```
docker pull phongtran27/outlook_calendar_report_generator
``` -->

# Build Container 
```
docker run -it --name ncsa_vacation_calendar_sync --mount type=bind,source=$HOME,dst=/home ghcr.io/ncsa/vacation_calendar_sync
```


# Quick Start
The commnad below will generate a report to console of events that occurs between the start and end date. 
```
python3 OutlookCalendar.py [optional flags] [year]-[month]-[day] [year]-[month]-[day]

Example: python3 OutlookCalendar.py -m 2022-10-26 2022-10-29

Example: python3 OutlookCalendar.py -s

```

# Optional flags include:

`-s` : Retrieves members' calendar events and synchronize them to the shared calendar

`-d` : Dumps the json data of member's events occuring between the start and end date

`-m` : Manually update the shared calendar with start and end time with format YYYY-MM-DD

`-h` : Display the help screen

# Notes

The `.netrc` file needs to have the correct permission (`-rw-------`).

If not, do: `chmod u+rw,u-x,go-rwx ~/.netrc`

To check: `ls -la ~/.netrc`

