FROM python:3.6-alpine

COPY requirements.txt grafolean-worker-ping.py /opt/
RUN pip install -r /opt/requirements.txt
RUN echo -e "* * * * * source /etc/environment; export BACKEND_URL BOT_TOKEN; python /opt/grafolean-worker-ping.py > /proc/1/fd/1 2> /proc/1/fd/2\n" > /etc/crontabs/root

# https://stackoverflow.com/a/47960145/593487
ENTRYPOINT ["crond", "-f", "-d", "8"]
