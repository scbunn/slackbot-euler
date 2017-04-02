"""EulerBot

EulerBot is a SlackBot designed to help and assist Systems Engineers operating
in a Dev/Ops, SRE, or Infrastructure Engineering role.

EulerBot runs a read/eval loop and passes messages to registered integrations.
"""
import logging
import time
from eulerbot.slackbot import SlackBot
from eulerbot.integrations import support


class EulerBot(SlackBot):
    """EulerBot Object

    Attributes:
        logger (:obj: `logger`, optional): An instance of a python logger
        received
    """
    def __init__(self, logger=None):
        super().__init__()
        self.logger = logger or logging.getLogger(__name__)
        self.running = True
        self.birth = time.time()
        self.events_received = 0

        self.events_processed = 0
        self._dms = []
        self._integrations = {
            'direct': [],
            'channel': [],
            'mention': []
        }
        self._integrations['channel'].append(
            support.ChannelSupport(self)
        )
        self._integrations['mention'].append(
            support.ChannelSupport(self)
        )
        self.logger.info("Started {} with UID {}".format(
            self.name, self.uid))

    @property
    def integrations(self):
        """Return a list of registered integration's"""
        return self._integrations

    @property
    def dms(self):
        """return a list of direct messages with the bot"""
        del self._dms[:]
        for dm in self._api_method("im.list").get('ims', {}):
            self._dms.append(dm.get('id'))
        return self._dms

    def _get_event_type(self, event):
        """Return the type of event received from rtm_read()

        Arguments:
            event (dict): Event returned from rtm_read

        Returns:
            (str) value of event type
        """
        # if the channel is a direct message, then its a DM
        if event.get('channel') in self.dms:
            return 'direct'

        # is the bot @ mentioned
        if "<@{}>".format(self.uid) in event.get('text', ''):
            return 'mention'

        # everything else we consider channel text
        return 'channel'

    def process_event(self, event, event_type):
        """Process each message type event

        Pass the event on to any registered integration for that event type."""
        if event.get('user', '') == self.uid:  # Don't process bot traffic
            return

        self.logger.debug("Received {} event".format(event_type))
        for integration in self.integrations.get(event_type, []):
            integration.update(event)

    def run(self):
        """Read/Eval loop

        Get the next event from the Slack firehose as long as we are running
        """
        if self.sc.rtm_connect():
            self.logger.info("connected to the Slack Real Time Messaging API.")

            while self.running:
                for event in self.sc.rtm_read():
                    self.events_received += 1
                    if event.get('type') == 'message':
                        _type = self._get_event_type(event)
                        self.process_event(event, _type)
                        self.events_processed += 1
                time.sleep(1)
        else:
            self.logger.error("Could not connect to Slack Real Time "
                              "Messaging API")
