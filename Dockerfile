FROM python:3

RUN mkdir -p /usr/eulerbot
COPY . /usr/eulerbot/

RUN pip install -r /usr/eulerbot/tests/requirements.txt && \
    python -m spacy download en_core_web_md && \
    chmod +x /usr/eulerbot/euler

WORKDIR /usr/eulerbot
CMD ["/usr/eulerbot/euler"]

