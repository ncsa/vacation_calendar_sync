FROM python:3

ENV TZ=America/Chicago
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# RUN apt-get update -y \
#     && apt-get install ssmtp -y \ 
#     && echo mailhub=smtp-server >> /etc/ssmtp/ssmtp.conf \
#     && echo FromLineOverride=YES >> /etc/ssmtp/ssmtp.conf \
#     && apt-get clean

RUN mkdir /home/vacation_calendar_sync

COPY . /vacation_calendar_sync
WORKDIR /vacation_calendar_sync
RUN python -m pip install -r /vacation_calendar_sync/requirements.txt

# RUN ln -s /home/microsoft_graph_auth.yaml /root/microsoft_graph_auth.yaml
RUN ln -s /home/vacation_calendar_sync_config.yaml /root/vacation_calendar_sync_config.yaml

ENV VCS_CONFIG="/root/vacation_calendar_sync_config.yaml"
ENV VCS_COLLECTION_PATH="/home/vacation_calendar_sync"
#RUN mkdir /duo_auth/app

CMD ["bash"]

#CMD [ "python3 OutlookCalendar.py -s" ]

ENTRYPOINT [ "./entrypoint.sh" ]


