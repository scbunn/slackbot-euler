FROM python:3

ENV OPSGENIE_API_KEY='__OPSGENIE_API_KEY__'
ENV SLACKBOT_TOKEN='__SLACKBOT_TOKEN__'
ENV SLACKBOT_BOT_NAME='__SLACKBOT_BOT_NAME__'
ENV JIRA_SERVER='__JIRA_SERVER__'
ENV JIRA_USER='__JIRA_USER__'
ENV JIRA_PASSWORD='__JIRA_PASSWORD__'
ENV JIRA_PROJECT_KEY='__JIRA_PROJECT_KEY__'

RUN mkdir -p /usr/eulerbot
COPY . /usr/eulerbot/


RUN pip install -r /usr/eulerbot/tests/requirements.txt && \
    python -m spacy download en_core_web_md && \
    chmod +x /usr/eulerbot/euler

WORKDIR /usr/eulerbot
CMD ["/usr/eulerbot/euler"]

