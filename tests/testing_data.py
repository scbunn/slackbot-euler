"""Testing data

This module contains testing data for running and mocking tests."""
import os
import time
import json
from datetime import datetime


def load_json(filename):
    """Load a JSON file from disk and return a dict"""
    with open(filename) as f:
        return json.load(f)


dates = {
    'current_time': time.mktime(datetime(2011, 6, 21).timetuple())
}

eulerbot = {
    'message_events': load_json(
        'tests/data/eulerbot_message_events.json')['event_messages'],
}

slackbot = {
    'name': os.environ.get('SLACKBOT_BOT_NAME', 'testgoat'),
    'token': os.environ.get('SLACKBOT_TOKEN', 'abc123'),
    'api_call': load_json(
        'tests/data/slackbot_api_call.json')['api_call'],
    'post_message': load_json(
        'tests/data/slackbot_post_message.json')['post_message'],
    'channel_list': load_json(
        'tests/data/slackbot_channel_list.json')['channel_list'],
    'im_list': load_json(
        'tests/data/slackbot_im_list.json')['im_list'],
    'user_list': load_json(
        'tests/data/slackbot_user_list.json')['user_list'],
}


SupportChannel = {
    'word_bag': [
        ('help', True),
        ('hitman', True),
        ('assistance', True),
        ('assist with', True),
        ('support', True),
        ('<!here|@here>', True),
        ('java', False),
        ('fever', False),
        ('milkshake', False),
        ('stomach', False),
        ('couch', False),
        ('screwdriver', False),
        ('young man', False),
        ('oven', False),
        ('frame', False),
    ],
    'test_events': [
        json.loads(line) for line in open('tests/data/support_test_events.txt')
    ],
    'text_blobs': [line for line in open(
        'tests/data/support_text_blobs.txt')
        if not line.startswith('#')]
}


class ErrorAfter(object):
    """Callable that will raise 'CallableExhausted' exception after
    'limit' calls."""
    def __init__(self, limit):
        self.limit = limit
        self.calls = 0

    def __call__(self, *args):
        self.calls += 1
        if self.calls > self.limit:
            raise CallableExhausted


class CallableExhausted(Exception):
    pass


class MockIntegration(object):
    """Mock EulerBot integration object"""
    def __init__(self, call_count=0):
        self.call_count = 0

    def __repr__(self):
        return "%s (%s)" % (self.__class__.__name__, self.__dict__)

    def update(self, event):
        self.call_count += 1
