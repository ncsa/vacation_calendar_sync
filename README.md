# Vacation Calendar Sync
- Generate a report of members are are "away" based on their Outlook Calendar within a start-end timeframe. 
- Update shared calendar to synchronize with members' calendars with events that are "away". 

# Configuration File Setup

Microsoft Azure Project Config (`/root/vacation_calendar_sync_config.yaml`)

Look at [sample_config.yaml](sample_config.yaml)

## Pull Image
```
docker pull ghcr.io/ncsa/vacation_calendar_sync:production
```

# Build Container 
```
docker run -it --name ncsa_vacation_calendar_sync --mount type=bind,source=$HOME,dst=/home ghcr.io/ncsa/vacation_calendar_sync:production
```

Once the container is created, entrypoint will execute the entrypoint.sh file, which effectively runs the program with python3 OutlookCalendar -s mode. To override this default command run:

```
docker run -it --name ncsa_vacation_calendar_sync --entrypoint /bin/bash --mount type=bind,source=$HOME,dst=/home ghcr.io/ncsa/vacation_calendar_sync:production
```

This will take you inside the container where you can run the commands listed below


# Quick Start
The commnad below will generate a report to console of events that occurs between the start and end date. 
```
python3 OutlookCalendar.py [optional flags] [year]-[month]-[day] [year]-[month]-[day]

Example: python3 OutlookCalendar.py -m 2022-10-26 2022-10-29

Example: python3 OutlookCalendar.py -s

Example: python3 OutlookCalendar.py -g
```

# Optional flags include:

`-s` : Retrieves members' calendar events and synchronize them to the shared calendar

`-g` : Generate a report of the shared calendar

`-d` : Dumps the json data of member's events occuring between the start and end date

`-m` : Manually update the shared calendar with start and end time with format YYYY-MM-DD

`-h` : Display the help screen
