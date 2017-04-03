"""Jira Integration


Integration to support retrieving and manipulating Jira Issues, Epics, and
Boards."""
import re
import logging
import uuid
import requests
import os
import jira
from beaker.cache import Cache
from jira import JIRA


class JiraManager(object):
    """Jira Manager for issues

    Uses the python-jira dependency to manage issues and other settings of
    jira."""

    def __init__(self, cache, logger=None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.cache = cache
        self.server = os.getenv('JIRA_SERVER', 'http://127.0.0.1')
        self.user = os.getenv('JIRA_USER', 'admin')
        self.password = os.getenv('JIRA_PASSWORD', 'admin')
        self.options = {
            'server': self.server,
        }
        self.issue_fields = [
            'assignee',
            'issuetype',
            'status',
            'labels',
            'components',
            'reporter',
            'watches',
            'created',
            'updated',
            'description',
            'summary',
            'comment',
            'priority',
            'customfield_10751',
            'customfield_10003'
        ]
        self._jira = None
        self.logger.debug("Loaded JiraManager for {}".format(self.server))

    def issue(self, _id):
        """Return a copy of the requested issue"""
        key = 'jira.issue.{}'.format(_id)
        if key in self.cache:
            self.logger.debug('returning cached issue...')
            return self.cache.get_value(key)

        try:
            f = ','.join(self.issue_fields)
            issue = self.jira.issue(_id, fields=f)
            self.cache.set_value(key, issue, expiretime=60)
            return issue
        except jira.exceptions.JIRAError as e:
            self.logger.warning("Error retrieving issue {}: {}".format(
                _id, e))

    @property
    def jira(self):
        """Return an attached copy of the jira parser"""
        if self._jira:
            return self._jira

        try:
            self._jira = JIRA(
                self.options,
                basic_auth=(self.user, self.password),
                async=True,
                max_retries=1,
            )
            return self._jira
        except requests.exceptions.ConnectionError as e:
            self.logger.error("could not connect to jira: {}".format(e))
            self._jira = None


class JiraManagement(object):
    """Jira EulerBot Integration"""

    def __init__(self, bot, message_type, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.message_type = message_type
        self.bot = bot
        self.events_received = 0
        self.events_processed = 0
        self.uuid = uuid.uuid4()
        self.cache = Cache('EulerBot-Jira-{}'.format(self.uuid),
                           lock_dir='/tmp/slackbot.cache.d/{}'.format(
                               self.uuid), type='memory')
        self.key = os.getenv('JIRA_PROJECT_KEY', 'SDO')
        self.manager = JiraManager(self.cache)
        self.logger.info('Loaded Jira Management Integration for {}'.format(
            self.message_type))

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.__dict__)

    def __str__(self):
        return 'Jira Management Integration'

    def has_jira_key(self, text):
        """Check if the text contains the Jira project key"""
        if '{}-'.format(self.key) in text.upper():
            return True

    def extract_issue_id(self, text):
        """Extract JIRA issue from text and return issue id."""
        if self.has_jira_key(text):
            pattern = '{}-[0-9]+'.format(self.key)
            try:
                found = re.search(pattern, text.upper()).group(0)
                return found
            except AttributeError:
                self.logger.warning(
                    "Jira key found in text, but could not extract")

    def post_issue_link(self, channel, user, text):
        """If text contains an issue id, post a link to it."""
        if not channel or not text:
            return

        _id = self.extract_issue_id(text)
        if _id:
            issue = self.manager.issue(_id)
            if issue:
                message = "{} <{}|{}>".format(
                    issue.key, issue.permalink(), issue.fields.summary)
            else:
                message = "<@{}>, are you sure {} is a valid Jira issue? "\
                    "I couldn't find it.".format(user, _id)
            self.bot.post_message(channel, message)

    def update(self, event):
        """Update Jira Integration.

        This method is called for each message of message_type received."""
        if not event.get('text'):
            return

        self.post_issue_link(event.get('channel', ''),
                             event.get('user', 'strange'),
                             event.get('text', ''))
