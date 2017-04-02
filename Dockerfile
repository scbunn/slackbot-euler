FROM python:3

ENV OPSGENIE_API_KEY='__OPSGENIE_API_KEY__'
ENV SLACKBOT_TOKEN='__SLACKBOT_TOKEN__'
ENV SLACKBOT_BOT_NAME='__SLACKBOT_BOT_NAME__'
RUN mkdir -p /usr/eulerbot
COPY . /usr/eulerbot/


RUN pip install -r /usr/eulerbot/tests/requirements.txt && \
    python -m spacy download en_core_web_md && \
    chmod +x /usr/eulerbot/euler

WORKDIR /usr/eulerbot
CMD ["/usr/eulerbot/euler"]

