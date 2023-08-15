DEBUG=1
REGISTRY=ghcr.io
REPO=ncsa/vacation_calendar_sync
tag=main

# function latest_tag {
#   [[ "$DEBUG" -eq 1 ]] && set -x
#   echo "production"
# }

#[[ "$DEBUG" -eq 1 ]] && set -x

#tag=$(latest_tag)

docker run -it 
--entrypoint bash \
--pull always \
--mount type=bind,src=$HOME,dst=/home \
$REGISTRY/$REPO:$tag 




