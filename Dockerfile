FROM python:3

ENV AZURE_GRAPH_AUTH="/home/vacation_calendar_sync_config.yaml"

ENV TZ=America/Chicago
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY . /srv
WORKDIR /srv
RUN python -m pip install -r /srv/requirements.txt

CMD ["bash"]
