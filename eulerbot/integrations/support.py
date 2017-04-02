"""ChannelSupport EulerBot Integration

This integration module provides channel support for all channels that
EulerBot is listening in."""
import re
import logging
import os
import requests
import string
import spacy


class LanguageParser(object):
    """Language Parser

    Object to parse and deal with Natural Language Processing."""
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self._parser = None
        self._doc = None
        self.model = os.environ.get('SLACKBOT_SUPPORT_NLP_MODEL',
                                    'en_core_web_md')

    @property
    def parser(self):
        """Load and return NLP parser"""
        if self._parser:
            return self._parser
        self._parser = spacy.load(self.model)
        return self._parser

    @property
    def doc(self):
        """Return the parsed document."""
        return self._doc

    @doc.setter
    def doc(self, text):
        """parse text and set the document."""
        text = self.remove_urls(text)
        text = self.remove_punctuation(text)
        self._doc = self.parser(text)

    def remove_punctuation(self, text):
        """Strip punctuation from text and return."""
        if isinstance(text, str):
            return text.translate(
                text.maketrans({key: None for key in string.punctuation}))

    def remove_urls(self, text):
        """Remove any URL patterns from text"""
        return re.sub(r"http\S+", "", text)

    def find_urls(self, text):
        """Find URL patterns in text

        Return a list of URLs found in the passed text."""
        urls = re.findall(r"http\S+?(?=\||>)", text)
        return urls

    def noun_chunks(self):
        """Return noun chunks from parsed doc"""
        if not self.doc:
            return []
        return self.doc.noun_chunks

    def subject(self):
        """Return the subject of the doc

        If more than one subject is found, return the longest subject."""
        subject = set()
        for word in self.noun_chunks():
            if word.root.dep_ == 'nsubj':
                subject.add(word.text)
        if subject:
            return max(subject, key=len)
        return 'No subject found'

    def sobject(self):
        objects = set()
        for word in self.noun_chunks():
            root = word.root.dep_
            if root == 'dobj' or root == 'pobj':
                objects.add(word.text)
        if objects:
            return max(objects, key=len)


class OpsGenieSchedule(object):
    """OpsGenieOnCall

    Retrieve current schedule information from OpsGenie"""
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.url = 'https://api.opsgenie.com/v1.1/json/schedule/'
        self.apiKey = os.environ.get('OPSGENIE_API_KEY', '')

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
        if result:
            return result.get('participants', [])[0].get('name', 'Unknown')
        return "unknown"


class ChannelSupport(object):
    """Provide infrastructure engineering support for active channels."""

    def __init__(self, bot, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.bot = bot
        self.ogschedule = OpsGenieSchedule()
        self.nlp = LanguageParser()
        self.events_received = 0
        self.events_processed = 0
        self.trigger_words = [
            'help',
            'hitman',
            'assistance',
            'assist with',
            'support',
            '<!here|@here>'
        ]

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.__dict__)

    def __str__(self):
        return 'Channel Support Integration'

    def on_call(self):
        """Return the current on-call engineer"""
        key = 'og.schedule.oncall'
        if key in self.bot.cache:
            return self.bot.cache.get_value(key)

        email = self.ogschedule.on_call('OpsEng_OnCall_Pri')
        self.logger.debug("on-call email: {}".format(email))
        u = None
        for user in self.bot.users:
            if email == user.profile.get('email', ''):
                self.logger.debug("On Call email {} matches {} email".format(
                    email, user.name))
                u = user.uid
        if not u:
            u = email
        self.bot.cache.set_value(key, u, expiretime=300)
        return u

    def has_trigger_word(self, text):
        """Check to see if 'text' contains a trigger word."""
        if isinstance(text, str):
            return any(trigger in text for trigger in self.trigger_words)

    def parse_query(self, text):
        """Parse the text and return a tuple of subject, objects"""
        self.nlp.doc = text
        subject = self.nlp.subject()
        obj = self.nlp.sobject()
        self.logger.debug('Subject: {} -> {}'.format(subject, obj))
        return (subject, obj)

    def generate_response(self, text):
        """Generate a help response"""
        subject, obj = self.parse_query(text)
        hitman = self.on_call()
        if obj:
            return "Our hitman, [<@{}>] is guaranteed to eliminate _{}_ " \
                "problem(s)".format(hitman, obj)
        return "Our hitman [<@{}>] should be able to help you.".format(hitman)

    def update(self, event):
        """Update Integration

        This method is called every time EulerBot captures a message that this
        integration has registered for received ."""
        self.events_received += 1
        text = event.get('text')

        if not text:
            return
        if self.has_trigger_word(text):
            response = "<@{}>, {}".format(
                event.get('user'), self.generate_response(text))
            self.logger.debug(response)
            self.bot.post_message(event.get('channel'), response)
        self.events_processed += 1
