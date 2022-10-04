FROM python:3

ENV TZ=America/Chicago
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY . /duo_auth
WORKDIR /duo_auth
RUN python -m pip install -r /duo_auth/requirements.txt

RUN mkdir /duo_auth/app

CMD ["bash"]