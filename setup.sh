REGISTRY=ghcr.io
REPO=ncsa/vacation_calendar_sync


# Change it so that it pulls latest from main 
docker pull $REGISTRY/$REPO:main
#docker pull ghcr.io/ncsa/vacation_calendar_sync:1685990588_logging_feature_54634f5

#docker run -it --name ncsa_vacation_calendar_sync --mount type=bind,source=$HOME,dst=/home $REGISTRY/$REPO