"""Unit tests for slackbot"""

import copy
import pytest
import testing_data as TD
import time
import eulerbot.slackbot
from mock import MagicMock


def test_slackuser_default_object():
    u = eulerbot.slackbot.SlackUser()
    assert u.uid is None
    assert u.admin is False
    assert u.name is None
    assert u._profile == {}


def test_slackbot_default_initialization(monkeypatch):
    """Test that slackbot default initialization is correct."""
    monkeypatch.delenv('SLACKBOT_BOT_NAME', raising=False)
    monkeypatch.delenv('SLACKBOT_TOKEN', raising=False)
    slackbot = eulerbot.slackbot.SlackBot()
    assert slackbot.name == 'SlackBot'
    assert slackbot.token is None


def test_slackbot_os_env_initialization(slackbot):
    """Test that slackbot ENV variables are assigned as expected."""
    assert slackbot.name == TD.slackbot.get('name')
    assert slackbot.token == TD.slackbot.get('token')


def test_slackbot_repr(slackbot):
    """Test slackbot repr"""
    assert repr(slackbot).startswith('SlackBot(')


def test_slackbot_string_repr(slackbot):
    """Test slackbot string representation"""
    s = "{} ({})".format(TD.slackbot.get('name'), slackbot.uid)
    assert str(slackbot) == s


def test_slackbot_api_call_return_value_when_method_is_invalid(slackbot):
    """Test that an empty dictionary is returned if slack client api fails."""
    slackbot.sc.api_call = MagicMock(return_value={'ok': False})
    result = slackbot._api_method('failmethod')
    assert isinstance(result, dict)
    assert len(result.keys()) == 0
    slackbot.sc.api_call.assert_called_once_with('failmethod')


def test_slackbot_api_call_return_results_valid_request(slackbot):
    """Test that the slackbot api method returns a valid dictionary of
    results."""
    eulerbot.slackbot.SlackClient.api_call.return_value = TD.slackbot.get(
        'api_call')
    assert eulerbot.slackbot.SlackClient.api_call.call_count == 0
    result = slackbot._api_method('chat.PostMessage', channel='testing')
    assert eulerbot.slackbot.SlackClient.api_call.call_count == 1
    eulerbot.slackbot.SlackClient.api_call.assert_called_with(
        "chat.PostMessage", channel='testing')
    assert isinstance(result, dict)
    assert result['ok'] is True


def test_slackbot_api_call_cached_results(slackbot):
    """Test that the slackbot API caches API calls"""
    eulerbot.slackbot.SlackClient.api_call.return_value = TD.slackbot.get(
        'api_call')
    assert eulerbot.slackbot.SlackClient.api_call.call_count == 0
    for i in range(30):
        slackbot._api_method("testmethod")
    assert eulerbot.slackbot.SlackClient.api_call.call_count == 1
    eulerbot.slackbot.SlackClient.api_call.assert_called_once_with(
        "testmethod")


def test_slackbot_api_call_cache_bypass(slackbot):
    """Test that cached results can be invalided on request."""
    eulerbot.slackbot.SlackClient.api_call.return_value = TD.slackbot.get(
        'api_call')
    assert eulerbot.slackbot.SlackClient.api_call.call_count == 0
    slackbot._api_method("testmethod", Cache=False)
    slackbot._api_method("testmethod", Cache=False)
    assert eulerbot.slackbot.SlackClient.api_call.call_count == 2


@pytest.mark.slow
def test_slackbot_api_call_cache_timeout(slackbot):
    """Test that cache timeout invalidates API cache."""
    slackbot.expiretime = 10
    eulerbot.slackbot.SlackClient.api_call.return_value = TD.slackbot.get(
        'api_call')
    assert eulerbot.slackbot.SlackClient.api_call.call_count == 0
    slackbot._api_method("test.timeout")
    assert eulerbot.slackbot.SlackClient.api_call.call_count == 1
    time.sleep(12)
    slackbot._api_method("test.timeout")
    assert eulerbot.slackbot.SlackClient.api_call.call_count == 2


def test_slackbot_slack_users_success(slackbot):
    """Test SlackBot slack_users returns expected users"""
    eulerbot.slackbot.SlackClient.api_call.return_value = TD.slackbot.get(
        'user_list')
    users = slackbot.slack_users()
    assert isinstance(users, list)
    assert len(users) == len(TD.slackbot.get('user_list')['members'])


def test_slackbot_slack_users_failure(slackbot):
    """Test Slackbot slack_users returns an empty list on failure"""
    eulerbot.slackbot.SlackClient.api_call.return_value = {}
    users = slackbot.slack_users()
    assert isinstance(users, list)
    assert len(users) == 0


def test_slackbot_users_property(slackbot):
    """Test SlackBots users property returns a list of valid SlackUser
    objects."""
    eulerbot.slackbot.SlackClient.api_call.return_value = TD.slackbot.get(
        'user_list')
    users = slackbot.users
    assert 'slackbot.users' in slackbot.cache
    for u in users:
        assert isinstance(u, eulerbot.slackbot.SlackUser)
        assert u.name
        assert u.uid
        assert u.profile
        assert u.name in repr(u)


def test_slackbot_users_property_with_invalid_profile(slackbot):
    """Test that users property can handle no user profile."""
    data = copy.deepcopy(TD.slackbot.get('user_list'))
    data['members'].append(
        {
            'id': 'id0',
            'name': 'user_with_no_profile'
        }
    )
    eulerbot.slackbot.SlackClient.api_call.return_value = data
    users = slackbot.users
    assert len(users) == len(TD.slackbot.get('user_list')) + 1


def test_slackbot_users_property_cache(slackbot):
    """Test that slackbot users property is cached."""
    eulerbot.slackbot.SlackClient.api_call.return_value = TD.slackbot.get(
        'user_list')
    assert not slackbot._users
    slackbot.users
    assert 'slackbot.users' in slackbot.cache
    slackbot.users
    assert slackbot._users


@pytest.mark.slow
def test_slackbot_users_property_cache_timeout(slackbot):
    """Test that the user property cache value timeout"""
    eulerbot.slackbot.SlackClient.api_call.return_value = TD.slackbot.get(
        'user_list')
    assert 'slackbot.users' not in slackbot.cache
    slackbot.users
    assert 'slackbot.users' in slackbot.cache
    time.sleep(61)
    assert 'slackbot.users' not in slackbot.cache
    slackbot.cache.remove('slackclient.api.users.list')
    eulerbot.slackbot.SlackClient.api_call.return_value = {}
    slackbot.users
    assert isinstance(slackbot._users, list)
    assert len(slackbot._users) == 0


def test_slackbot_uid_property_can_find_slackbots_uid(slackbot):
    """Test that the uid property returns the SlackBots correct UID"""
    users = TD.slackbot.get('user_list')
    eulerbot.slackbot.SlackClient.api_call.return_value = users
    assert not slackbot._uid
    uid = slackbot.uid
    assert uid


def test_slackbot_uid_property_is_cached(slackbot):
    """Test that SlackBots UID property is cached"""
    slackbot.cache.remove('slackbot.uid')
    users = TD.slackbot.get('user_list')
    eulerbot.slackbot.SlackClient.api_call.return_value = users
    assert not slackbot._uid
    slackbot.uid
    assert 'slackbot.uid' in slackbot.cache
    uid = slackbot.uid
    assert uid


def test_slackbot_post_message_method(slackbot):
    """Test post_message method operates as expected."""
    response = TD.slackbot.get('post_message')
    eulerbot.slackbot.SlackClient.api_call.return_value = response
    result = slackbot.post_message(response.get('channel'),
                                   response.get('message').get('text'))
    assert result == response
    eulerbot.slackbot.SlackClient.api_call.assert_called_with(
        "chat.postMessage",
        channel=response.get('channel'),
        text=response.get('message').get('text'),
        username=slackbot.name,
        as_user=slackbot.name,
        Cache=False
    )


def test_slackbot_post_message_method_with_keyword_args(slackbot):
    """Test post_message method with keyword arguments."""
    response = TD.slackbot.get('post_message')
    eulerbot.slackbot.SlackClient.api_call.return_value = response
    result = slackbot.post_message(response.get('channel'),
                                   response.get('message').get('text'),
                                   mrkdwn=True)
    assert result == response
    eulerbot.slackbot.SlackClient.api_call.assert_called_with(
        "chat.postMessage",
        channel=response.get('channel'),
        text=response.get('message').get('text'),
        username=slackbot.name,
        as_user=slackbot.name,
        mrkdwn=True,
        Cache=False
    )
