"""Jira Integration


Integration to support retrieving and manipulating Jira Issues, Epics, and
Boards."""
import re
import logging
import uuid
import requests
import os
import jira
import hashlib
import urllib
import dateutil.parser
from time import mktime
from beaker.cache import Cache
from jira import JIRA


class IssueLink(object):
    """IssueLink

    Object to represent a Jira Issue Link."""

    def __init__(self, issue, jira=None, users=[], logger=None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.issue = issue
        self.logger.debug("Created IssueLink: {}".format(self))
        self._attachment = {}
        self._attachment['fields'] = []
        self.attachment_built = False
        self.users = users
        self.jira = jira

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.__dict__)

    def __str__(self):
        return '<{}, {}>'.format(
            self.__class__.__name__,
            self.issue.key)

    @property
    def attachment(self):
        """Return a completed attachment

        This property builds the attachment with all possible components."""
        if not self.attachment_built:
            self._attachment['fallback'] = 'something broken'
            self._add_issue_title()
            self._add_status()
            self._add_issue_description()
            self._add_thumbnail_icon()
            self._add_color()
            self._add_assignee()
            self._add_reporter()
            self._add_story_points()
            self._add_epic()
            self._add_labels()
            self._add_footer()
            self.attachment_built = True
        return [self._attachment]

    def hash_email(self, email):
        """Return MD5 hash of email for use with gravatar."""
        return hashlib.md5('{}'.format(email).encode('utf-8')).hexdigest()

    def gravatar(self, emailhash):
        """Return link to gravatar icon based on md5hash"""
        options = {
            'd': 'mm',
            's': '75',
            'r': 'g'
        }
        url = 'https://www.gravatar.com/avatar/{}?'.format(emailhash)
        url += urllib.parse.urlencode(options)
        return url

    def _add_status(self):
        """Add the status of the message as the title"""
        try:
            status = self.issue.fields.status
            self._attachment['title'] = 'Status: {}'.format(status)
        except AttributeError:
            self.logger.debug(
                'could not determine status for issue {}'.format(self))

    def _add_footer(self):
        """Add the updated date as the ts field"""
        try:
            updated = self.issue.fields.updated
            updated = dateutil.parser.parse(updated)
            ts = int(
                mktime(updated.timetuple()) + updated.microsecond/1000000.0)
            self._attachment['ts'] = ts
            self._attachment['footer'] = 'Last updated'
            footer_icon = self.issue.fields.priority.iconUrl
            self._attachment['footer_icon'] = footer_icon
        except AttributeError:
            self.logger.error(
                'could not get updated time from issue {}'.format(self))
        except ValueError:
            self.logger.error(
                'could not parse date from Jira Issue {}'.format(self))

    def _add_epic(self):
        """If the issue has an epic, add this field"""
        try:
            epic_key = self.issue.fields.customfield_10751
            if epic_key:
                epic = self.jira.issue(epic_key)
                field = {
                    'title': 'Epic',
                    'value': '<{}|{}>'.format(
                        epic.permalink(),
                        epic.fields.summary),
                    'short': True
                }
                self._attachment['fields'].append(field)
        except AttributeError as e:
            self.logger.debug('issue {} has no epic attached.'.format(self))
            self.logger.debug(e)

    def _add_story_points(self):
        """If story points have been assigned, add this field"""
        try:
            points = self.issue.fields.customfield_10003
            if not points:
                return
            points = int(points)
            field = {
                'title': 'Estimation',
                'value': ':clock2: {} hours'.format(points),
                'short': True
            }
            self._attachment['fields'].append(field)
        except AttributeError:
            self.logger.debug('issue {} has no story points'.format(self))
        except ValueError:
            self.logger.error('issue {} has non integer story points'.format(
                self))

    def _add_labels(self):
        """If the issue has labels, add this field"""
        try:
            labels = self.issue.fields.labels
            if not labels:
                return
            field = {
                'title': 'Labels',
                'value': ', '.join(labels),
                'short': False

            }
            self._attachment['fields'].append(field)
        except AttributeError:
            self.logger.debug('issue {} has no labels'.format(self))

    def _email_to_slack(self, email, default="Mystery Man"):
        """Try and find email in slack users or return default username"""
        u = None
        for user in self.users:
            if email == user.profile.get('email', ''):
                u = '<@{}>'.format(user.uid)
        if not u:
            u = default
        return u

    def _add_reporter(self):
        """If the ticket has a reporter field, add to our attachment"""
        try:
            reporter = self.issue.fields.reporter
            reporter = {
                'title': 'Reported',
                'value': ':bust_in_silhouette: {}'.format(
                    reporter.displayName
                ),
                'short': True
            }
            self._attachment['fields'].append(reporter)
        except AttributeError:
            self.logger.debug('issue {} has no reporter'.format(self))

    def _add_assignee(self):
        """If the ticket is assigned, add it as a field"""
        try:
            assignee = self.issue.fields.assignee
            name = self._email_to_slack(assignee.emailAddress,
                                        assignee.displayName)
            assignment = {
                'title': 'Assigned',
                'value': ':bust_in_silhouette: {}'.format(name),
                'short': True
            }
            self._attachment['fields'].append(assignment)
        except AttributeError:
            self.logger.debug('issue {} is not assigned'.format(self))

    def _add_thumbnail_icon(self):
        """Add assigned thumbnail if available."""
        try:
            author = self.issue.fields.assignee
            emailhash = self.hash_email(author.emailAddress)
            url = self.gravatar(emailhash)
            self._attachment['thumb_url'] = url
        except AttributeError as e:
            self.logger.debug(
                'issue {} is not assigned, gravatar not possible'.format(self))
            self.logger.debug(e)

    def _add_color(self):
        """Add attachment color based on issuetype"""
        color = '#a9a9a9'
        try:
            issue_type = self.issue.fields.issuetype.name.lower()
            if issue_type == 'story':
                color = 'good'
            if issue_type == 'bug':
                color = 'danger'
        except AttributeError as e:
            self.logger.error(
                'could not determine issue type for issue {}'.format(self))
            self.logger.debug(e)
        self._attachment['color'] = color

    def _add_issue_title(self):
        """Add the issue title and link as slack attachment title"""
        try:
            summary = self.issue.fields.summary
            key = self.issue.key.upper()
            title = '{} - {}'.format(key, summary)
            link = self.issue.permalink()
            icon = self.issue.fields.issuetype.iconUrl
            self._attachment['author_name'] = title
            self._attachment['author_link'] = link
            self._attachment['author_icon'] = icon
        except AttributeError as e:
            self.logger.warn('issue {} has errors in title fields: {}'.format(
                self, e))

    def _add_issue_description(self):
        """Add description to the issue link"""
        try:
            description = self.issue.fields.description
            if len(description) > 100:
                description = description[:100]
                description += '... <{}|read more>'.format(
                    self.issue.permalink())
            self._attachment['text'] = description
        except AttributeError as e:
            self.logger.warn('issue {} has no description field: {}'.format(
                self, e))


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

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.__dict__)

    def __str__(self):
        return 'Jira Manager'

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
                key = 'jira.issue.link.{}'.format(issue.key)
                if key in self.cache:
                    self.logger.debug(
                        'issue {} cooling off...'.format(issue.key))
                    return
                il = IssueLink(issue,
                               jira=self.manager,
                               users=self.bot.users)
                print("ISSUE LINK: {}".format(il.attachment))
                self.bot.post_message(channel, '', attachments=il.attachment)
                self.cache.set_value(key, '', expiretime=60)
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
