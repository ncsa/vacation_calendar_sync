FROM python:3

ENV TZ=America/Chicago
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN mkdir /home/vacation_calendar_sync/
RUN mkdir /etc/vcs/
RUN mkdir /var/log/vcs/

COPY . /vacation_calendar_sync
WORKDIR /vacation_calendar_sync
RUN python -m pip install -r /vacation_calendar_sync/requirements.txt

ENV VCS_CONFIG="/etc/vcs/config.yaml"
ENV VCS_LOG="/var/log/vcs/"

ENTRYPOINT [ "./entrypoint.sh" ]