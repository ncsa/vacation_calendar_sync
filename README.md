# outlook_calendar_report_generator
- Generate a report of members are are "away" based on their Outlook Calendar within a start-end timeframe. 
- Update shared calendar to synchronize with members' calendars with events that are "away". 

# Setup

Microsoft Azure Project Config (`/root/microsoft_graph_auth.yaml`)
``` yaml
---
client_id : '...'
tenant_id : '...'
scope : 'user.read calendar.readwrite'
group_members : 
    'net_id_1' : 'name_1'
    'net_id_2' : 'name_2'
shared_calendar_name : '...'
...
```

Netrc setup (/home/.ssh/netrc)
``` 
machine OUTLOOK_LOGIN
login ...
password ...
```

## Pull Image from DockerHub 
```
docker pull phongtran27/outlook_calendar_report_generator
```

# Build Container 
```
docker run -it --name outlook-calendar-container --mount type=bind,source=$HOME,dst=/home outlook-calendar-report-generator
```


# Quick Start
The commnad below will generate a report to console of events that occurs between the start and end date. 
```
python3 OutlookCalendar.py [optional flags] [year]-[month]-[day] [year]-[month]-[day]

Example: python3 OutlookCalendar.py -r 2022-10-26 2022-10-29
```

Other optional flags include:

`-r` : Generates the a report of each members' availability occuring between start and end timeframe.

`-s` : Retrieves members' calendar events and synchronize them to the shared calendar

`-d` : Dumps the json data of member's events occuring between the start and end date

`-i` : Indicates whether this is first time running script. If it is, this flag must be used.

`-h` : Display the help screen
# Notes

The `.netrc` file needs to have the correct permission (`-rw-------`).

If not, do: `chmod u+rw,u-x,go-rwx ~/.netrc`

To check: `ls -la ~/.netrc`