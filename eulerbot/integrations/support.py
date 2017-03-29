"""ChannelSupport EulerBot Integration

This integration module provides channel support for all channels that
EulerBot is listening in."""
import re
import logging
import os
import requests
import string
import spacy


class OpsGenieSchedule(object):
    """OpsGenieOnCall

    Retrieve current schedule information from OpsGenie"""
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.url = 'https://api.opsgenie.com/v1.1/json/schedule/'
        self.apiKey = os.environ.get('OPSGENIE_API_KEY')

    def _request(self, call, payload):
        """Retrieve call from the OpsGenie API."""
        self.logger.debug('requesting {} with {} from OpsGenie'.format(
            call, payload))
        url = "{}/{}".format(self.url, call)
        payload['apiKey'] = self.apiKey
        r = requests.get(url, payload)
        if r.status_code == 200:
            return r.json()

    def on_call(self, team):
        """Retrieve the current on-call for `team`"""
        payload = {'name': team}
        result = self._request('whoIsOnCall', payload)
        self.logger.debug(result)
        return 'scbunn@sbunn.org'
        return result.get('participants', [])[0].get('name', 'Unknown')


class ChannelSupport(object):
    """Provide infrastructure engineering support for active channels."""

    def __init__(self, bot, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.bot = bot
        self._parser = None
        self.ogschedule = OpsGenieSchedule()
        self.trigger_words = [
            'help',
            'hitman',
            'assistance',
            'assist with',
            'support',
            '<!here|@here>'
        ]

    @property
    def parser(self):
        """Load and return NLP parser"""
        if self._parser:
            return self._parser
        self._parser = spacy.load('en_core_web_md')
        return self._parser

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.__dict__)

    def __str__(self):
        return 'Channel Support Integration'

    def on_call(self):
        """Return the current on-call engineer"""
        key = 'og.schedule.oncall'
        if key in self.bot.cache:
            return self.bot.cache.get_value(key)

        oncall = self.ogschedule.on_call('OpsEng_OnCall_Pri')
        self.logger.debug(oncall)
        u = None
        for user in self.bot.users:
            if oncall == user.profile.get('email', ''):
                self.logger.debug("Found email for on call user")
                u = user.uid
        self.bot.cache.set_value(key, u, expiretime=300)
        return u

    def has_trigger_word(self, text):
        """Check to see if 'text' contains a trigger word."""
        if isinstance(text, str):
            return any(trigger in text for trigger in self.trigger_words)

    def _get_subject_objects(self, parsed):
        """Try and extract the subject, verb, object from parsed"""
        subjects = set()
        objs = set()
        for word in parsed.noun_chunks:
            if word.root.dep_ == 'nsubj':
                subjects.add(word.text)
            if word.root.dep_ == 'dobj' or word.root.dep_ == 'pobj':
                objs.add(word.text)
        return (subjects, objs)

    def extract_urls(self, text):
        """Extract URLs from 'text'

        Return a tuple of the original text with URLs extracted and a set of
        all extracted URLs."""
        urls = re.findall(r"http\S+?(?=\||>)", text)
        text = re.sub(r"http\S+", "", text)
        return (text, urls)

    def remove_punctuation(self, text):
        """Strip punctuation from text and return."""
        if isinstance(text, str):
            return text.translate(
                text.maketrans({key: None for key in string.punctuation}))

    def update(self, event):
        """Update Integration

        This method is called every time EulerBot captures a message that this
        integration has registered for."""
        text = event.get('text')
        if not text:
            return
        self.logger.debug("event text: {}".format(text))
        if self.has_trigger_word(text):
            text, urls = self.extract_urls(text)
            text = self.remove_punctuation(text)
            oncall = self.on_call()
            m = "<@{}>:".format(event.get('user'))
            doc = self.parser(text)
            subjects, objects = self._get_subject_objects(doc)
            if subjects and objects:
                m += " Yes, we can help you with {}".format(
                    max(objects, key=len))
                self.logger.debug('parsed: {} -> {}'.format(
                    subjects, objects))
            else:
                m += " Yes.  We can try and help you."
                self.logger.debug('parse error: {}/{}'.format(
                    subjects, objects))
            if urls:
                m += " ({})".format(urls[0])
            self.bot.post_message(event.get('channel'), m)

            if oncall:
                m = '<@{}> is the current on-call'.format(oncall)
                self.bot.post_message(event.get('channel'), m)
        self.bot.events_processed += 1
