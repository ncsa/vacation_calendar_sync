FROM python:3

ENV TZ=America/Chicago
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY . /outlook-calendar-report-generator
WORKDIR /outlook-calendar-report-generator
RUN python -m pip install -r /outlook-calendar-report-generator/requirements.txt

RUN ln -s /home/.netrc /root/.netrc
RUN ln -s /home/microsoft_graph_auth.yaml /root/microsoft_graph_auth.yaml

#RUN mkdir /duo_auth/app

CMD ["bash"]