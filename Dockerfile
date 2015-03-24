FROM ubuntu
MAINTAINER Rob Haswell <me@robhaswell.co.uk>

RUN apt-get -qqy update
RUN apt-get -qqy upgrade
RUN apt-get -qqy install python-pip

ADD dropbot requirements.txt /usr/src/app/
WORKDIR /usr/src/app

RUN pip install -r requirements.txt

CMD ["python", "dropbot/cli.py", "-c", "env"]
