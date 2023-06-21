REGISTRY=ghcr.io
REPO=ncsa/vacation_calendar_sync
BRANCH=main

# Pulls the latest image from main branch
docker pull $REGISTRY/$REPO:$BRANCH

# Creates a docker container
docker run -it --name ncsa_vacation_calendar_sync --mount type=bind,source=$HOME,dst=/home $REGISTRY/$REPO:$BRANCH