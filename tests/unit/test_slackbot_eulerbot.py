"""EulerBot unit tests

This module unit tests the EulerBot object."""
import testing_data as TD
import pytest
import eulerbot.slackbot
from unittest.mock import patch, MagicMock

pytestmark = pytest.mark.eulerbot


@pytest.fixture
def EulerBotMockedRTM(MockEulerBot):
    MockEulerBot.sc.rtm_connect = MagicMock(autospec=True)
    MockEulerBot.sc.rtm_read = MagicMock(autospec=True)
    return MockEulerBot


def test_eulerbot_default_init(MockEulerBot):
    """Test that EulerBot has expected initial values"""
    assert MockEulerBot
    assert MockEulerBot.running
    assert MockEulerBot.events_received == 0
    assert len(MockEulerBot._dms) == 0
    assert isinstance(MockEulerBot.birth, float)


@pytest.mark.parametrize("dm",
                         [dm.get('id') for dm in TD.slackbot.get(
                             'im_list')['ims']])
def test_direct_message_property_list(MockEulerBot, dm):
    """Test that dm property returns a list of direct messages"""
    eulerbot.slackbot.SlackClient.api_call.return_value = TD.slackbot.get(
        'im_list')
    dms = MockEulerBot.dms
    assert dm in dms


def test_eulerbot_rtm_connection_failure(EulerBotMockedRTM):
    """Test EulerBot exits if it fails to connect to RTM API"""
    b = EulerBotMockedRTM
    b.sc.rtm_connect.return_value = False
    b.run()
    assert b.sc.rtm_connect.call_count == 1
    b.sc.rtm_connect.assert_called_once_with()
    assert b.events_received == 0


@patch('time.sleep', side_effect=TD.ErrorAfter(2), autospec=True)
def test_eulerbot_rtm_connection_empty_messages(_time, EulerBotMockedRTM):
    """Test EulerBot run connection runs"""
    b = EulerBotMockedRTM
    b.sc.rtm_connect.return_value = True

    with pytest.raises(TD.CallableExhausted):
        b.run()

    assert b.events_received == 0
    b.sc.rtm_connect.assert_called_once_with()
    assert b.sc.rtm_read.call_count == 3


@patch('time.sleep', side_effect=AssertionError, autospec=True)
@pytest.mark.parametrize("event_type", [
    "message",
    "hello",
    "reconnect_url",
    "presence_change",
    "",
    1,
    0,
    -1,
    None
])
def test_eulerbot_run_rtm_event_types(_time, event_type, EulerBotMockedRTM):
    """Test that run() can handle known and unexpected events"""
    rv = [{'type': event_type, 'param1': 'value1', 'text': 'foo'}]
    b = EulerBotMockedRTM
    b.sc.rtm_read.return_value = rv
    b.sc.rtm_connect.return_value = True
    b.process_event = MagicMock(autospec=True)
    b.slack_users = MagicMock(autospec=True)
    b.slack_users.return_value = TD.slackbot.get('user_list')['members']

    with pytest.raises(AssertionError):
        b.run()

    if event_type == 'message':
        print("Events Received: {}".format(b.events_received))
        assert b.events_received == 1
        assert b.events_processed == 1
        assert b.process_event.call_count == 1
    else:
        print("Event Type: {}".format(event_type))
        assert b.events_processed == 0


@pytest.mark.parametrize("event", TD.eulerbot.get('message_events'),
                         ids=["channel", "mention", "direct"])
def test_eulerbot_parse_message_types(event, EulerBotMockedRTM):
    eulerbot.slackbot.SlackClient.api_call.return_value = TD.slackbot.get(
        'im_list')
    b = EulerBotMockedRTM
    b.slack_users = MagicMock(autospec=True)
    b.slack_users.return_value = TD.slackbot.get('user_list')['members']
    check = event.get('text')
    assert b._get_event_type(event) in check


@patch('time.sleep', side_effect=AssertionError, autospec=True)
@pytest.mark.parametrize("event", TD.eulerbot.get('message_events'),
                         ids=["channel", "mention", "direct"])
def test_eulerbot_run_rtm_event_type_processing(_time, event,
                                                EulerBotMockedRTM):
    b = EulerBotMockedRTM
    b.sc.rtm_read.return_value = [event]

    b.slack_users = MagicMock(autospec=True)
    b.process_event = MagicMock(autospec=True)
    b.slack_users.return_value = TD.slackbot.get('user_list')['members']

    with pytest.raises(AssertionError):
        b.run()
    assert b.events_received == 1


@pytest.mark.parametrize("event_type", ['direct', 'mention', 'channel'])
def test_eulerbot_process_event_integrations(event_type,
                                             EulerBotMockedRTM):
    event = {
        "type": "message",
        "text": "testing message"
    }

    b = EulerBotMockedRTM
    b.integrations[event_type].clear()
    b.integrations[event_type].append(TD.MockIntegration())
    b.process_event(event, event_type)
    for integration in b.integrations[event_type]:
        assert integration.call_count == 1


@pytest.mark.parametrize("event_type", ['direct', 'mention', 'channel'])
def test_eulerbot_process_events_not_insane(event_type, EulerBotMockedRTM):
    """Test that the event processor does not process messages originating
    from the bot."""
    b = EulerBotMockedRTM
    event = {
        "type": "message",
        "user": b.uid,
        "text": "testing message"
    }
    b.integrations[event_type].clear()
    b.integrations[event_type].append(TD.MockIntegration())
    b.process_event(event, event_type)
    for integration in b.integrations[event_type]:
        assert integration.call_count == 0
