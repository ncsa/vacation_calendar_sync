FROM python:3

ENV TZ=America/Chicago
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY . /outlook_calendar_report_generator
WORKDIR /outlook_calendar_report_generator
RUN python -m pip install -r /outlook_calendar_report_generator/requirements.txt

RUN ln -s /home/.netrc /root/.netrc
RUN ln -s /home/microsoft_graph_auth.yaml /root/microsoft_graph_auth.yaml

#RUN mkdir /duo_auth/app

CMD ["bash"]