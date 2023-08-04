#!/bin/bash
CONFIG_FILE=/root/vacation_calendar_sync_config.yaml
REQUIRED_PARAMETERS="client_id tenant_id recipient_email scopes group_name shared_calendar_name category_name category_color vcs_directory AM_config PM config days_out update_interval"

if [[ -f "$CONFIG_FILE" ]]; then  
  for i in $REQUIRED_PARAMETERS; do 
    result=$(grep -q $i $CONFIG_FILE; echo $?)
    if [ "$result" -ne 0 ]; then
      echo $i is missing
      exit 1
    fi
  done
  python3 OutlookCalendar.py -s
else
  echo Need config file named vacation_calendar_sync_config at your local home directory
fi  
