FROM python:3

ENV TZ=America/Chicago
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# COPY . /outlook_calendar_report_generator
# WORKDIR /outlook_calendar_report_generator
# RUN python -m pip install -r /outlook_calendar_report_generator/requirements.txt
RUN apt-get update -y && 
    # apt-get install ssmtp -y && \ 
    # apt-get install vim && \
    # echo mailhub=smtp-server >> /etc/ssmtp/ssmtp.conf && \
    # echo FromLineOverride=YES >> /etc/ssmtp/ssmtp.conf && \
    # apt-get clean


COPY . /vacation_calendar_sync
WORKDIR /vacation_calendar_sync
RUN python -m pip install -r /vacation_calendar_sync/requirements.txt

RUN ln -s /home/.netrc /root/.netrc
# RUN ln -s /home/microsoft_graph_auth.yaml /root/microsoft_graph_auth.yaml
RUN ln -s /home/vacation_calendar_sync_config.yaml /root/vacation_calendar_sync_config.yaml
ENV AZURE_GRAPH_AUTH="/root/vacation_calendar_sync_config.yaml"
#RUN mkdir /duo_auth/app

CMD ["bash"]

#CMD [ "python3 OutlookCalendar.py" ]


