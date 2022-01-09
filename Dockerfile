FROM python:3.9-alpine

WORKDIR /app
COPY app/requirements.txt requirements.txt
COPY app/ ./
RUN pip install -r requirements.txt

COPY config/crontab /tmp/crontab
RUN cat /tmp/crontab > /etc/crontabs/root

CMD ["crond", "-f", "-l", "2"]
#CMD ["python", "main.py"]