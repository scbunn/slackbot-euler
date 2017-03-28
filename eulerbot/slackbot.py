"""SlackBot generic slack bot

This module contains components necessary for a basic Slack Bot."""
import logging
import os
from beaker.cache import Cache
from slackclient import SlackClient


class SlackUser(object):
    """Representation of a Slack User

    This class is used as a data structure to represent an individual user
    connected to Slack."""

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.uid = None
        self.admin = False
        self.name = None
        self._profile = {}

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.__dict__)

    def __str__(self):
        return '(%s, %s)' % (self.uid, self.name)

    @property
    def profile(self):
        """Return the SlackUsers profile"""
        return self._profile

    @profile.setter
    def profile(self, user_profile):
        """Set the users profile

        If the SlackUser has been passed a valid profile, then set it."""
        if isinstance(user_profile, dict):
            self._profile = user_profile
        else:
            self.logger.warning("could not set profile for {}."
                                " The profile passed was not valid: {}".format(
                                    self.name, user_profile))


class SlackBot(object):
    """SlackBot is a generic slack bot.

    This class can be used as a base class for creating a more specialized
    slack bot.

    Attributes:
        name (str): The name of the bot
        token (str): Slack Bot Token
        sc (:obj: `slackclient`): SlackClient instance
        logger (:obj: `logger', optional): An instance of a python logger
    """
    def __init__(self, logger=None):
        self.name = os.environ.get('SLACKBOT_BOT_NAME', 'SlackBot')
        self.token = os.environ.get('SLACKBOT_TOKEN')
        self.logger = logger or logging.getLogger(__name__)
        self._uid = None
        self.cache = Cache('slackbot', lock_dir='/tmp/slackbot.cache.d',
                           type='memory')
        self.expiretime = 120
        self.cache.clear()
        self._users = []
        self.sc = SlackClient(self.token)
        self.logger.debug("SlackBot initialized as {}".format(self.name))

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.__dict__)

    def __str__(self):
        return '%s (%s)' % (self.name, self.uid)

    def _api_method(self, method, **kwargs):
        """Call method of slackclient

        All methods are cached for self.cache_refresh time Cache=False is
        passed.

        Arguments:
            method (str): method of the SlackClient API to call
            kwargs (dict): keywaord args to pass to method

        Returns:
            A dictionary representation of the JSON output from the API call.
        """
        key = 'slackclient.api.{}'.format(method)
        should_cache = kwargs.get('Cache', True)
        if key in self.cache and should_cache:
            self.logger.debug('{} api call is cached, returning the cached'
                              ' data'.format(key))
            return self.cache.get_value(key)

        result = self.sc.api_call(method, **kwargs)
        self.logger.debug("SlackClient API Call: {}".format(method))
        self.logger.debug("API Results: {}".format(result))
        if result.get('ok'):
            self.cache.set_value(key, result, expiretime=self.expiretime)
            return result
        return {}

    @property
    def uid(self):
        """Return the slack UID of the SlackBot"""
        key = 'slackbot.uid'
        if key in self.cache:
            return self.cache.get_value(key)
        self.logger.info("{} UID is unknown, trying to find".format(self.name))
        for user in self.slack_users():
            print("SLACK USER: {}".format(user))
            print("BOT NAME: {}".format(self.name))
            if self.name in user.get('name'):
                self._uid = user.get('id')
                self.cache.set_value(key, self._uid)
        return self._uid

    @property
    def users(self):
        """Slack user list.

        Return or generate a list of all known slack users as SlackUser
        objects."""
        self.logger.info("Retrieving all SlackBots known users")
        key = 'slackbot.users'
        if key in self.cache:
            self.logger.debug('returning cached value for {}'.format(key))
            return self._users
        self.logger.debug('no valid cache data, requesting from slack')
        del self._users[:]
        users = self.slack_users()
        for user in users:
            u = SlackUser()
            u.uid = user.get('id')
            u.profile = user.get('profile')
            if u.profile:
                u.name = u.profile.get('real_name', u.uid)
            else:
                u.name = user.get('real_name', u.uid)
            u.admin = user.get('is_admin')
            self.logger.debug('Created {} user'.format(u))
            self._users.append(u)
        self.cache.set_value(key, '', expiretime=60)
        return self._users

    def slack_users(self):
        """Return data for all known slack users"""
        self.logger.debug('Asking slack for all known users.')
        result = self._api_method("users.list")
        return result.get('members', [])

    def post_message(self, tid, text, **kwargs):
        """Post a message to a channel or user.

        Post a message to a channel or user using the chat.postMessage API
        call.

        Arguments:
            tid (str): The channel or user target id
            text (str): Formatted text to post
            kwargs (dict): additional keywords to pass to API

        Returns:
            Returns API JSON is successful, none otherwise
        """
        result = self._api_method("chat.postMessage", channel=tid,
                                  text=text, username=self.name,
                                  as_user=self.name, Cache=False, **kwargs)
        if result:
            return result
