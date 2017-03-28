"""ChannelSupport EulerBot Integration

This integration module provides channel support for all channels that
EulerBot is listening in."""
import re
import logging
import string
import spacy


class ChannelSupport(object):
    """Provide infrastructure engineering support for active channels."""

    def __init__(self, bot, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.bot = bot
        self._parser = None
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
        self.bot.events_processed += 1
