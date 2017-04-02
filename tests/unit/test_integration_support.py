"""Support Integration Tests

Unit test the support integration module."""
import pytest
import testing_data as TD
from eulerbot.integrations.support import ChannelSupport
from unittest.mock import MagicMock

pytestmark = pytest.mark.support_integration


@pytest.fixture
def Module(MockEulerBot):
    """ChannelSupport integration module instance."""
    MockEulerBot.sc.rtm_connect = MagicMock(autospec=True)
    MockEulerBot.sc.rtm_read = MagicMock(autospec=True)
    cs = ChannelSupport(MockEulerBot)
    cs.nlp._parser = MagicMock(autospec=True)
    cs.ogschedule.on_call = MagicMock(autospec=True)
    cs.ogschedule.on_call.return_value = 'testinggoat@slack.com'
    return cs


@pytest.mark.parametrize("word, boolean", TD.SupportChannel.get('word_bag'))
def test_channel_support_has_trigger_word(Module, word, boolean):
    """Test a variety of text blobs for trigger words"""
    s = """No poor dumb bastard {} ever won a war by dying for his country.
    He won the war, by making the other poor dumb bastard die for his country.
    """.format(word)
    assert Module.has_trigger_word(s) is boolean


@pytest.mark.parametrize("word", [None, '', 0])
def test_channel_support_has_trigger_no_data(Module, word):
    """Test trigger word selection works with no data"""
    assert not Module.has_trigger_word(word)


def test_oncall_returns_a_valid_string(Module):
    """Test that the on_call method always returns a valid string."""
    assert isinstance(Module.on_call(), str)


def test_oncall_caches_value(Module):
    """Test that the on_call method caches its value."""
    with pytest.raises(KeyError):
        Module.bot.cache.get_value('og.schedule.oncall')
    Module.ogschedule.on_call = MagicMock(autospec=True,
                                          return_value='citest')
    Module.on_call()
    assert Module.bot.cache.get_value('og.schedule.oncall')
    assert Module.on_call() == 'citest'
    Module.ogschedule.on_call.call_count == 1


def test_oncall_returns_user_if_email_match(Module):
    """Test that method returns the user ID on oncall email match."""
    Module.bot.slack_users = MagicMock(autospec=True)
    Module.bot.slack_users.return_value = \
        TD.slackbot.get('user_list')['members']
    assert Module.on_call() == 'U023BECGF'


def test_parse_query_returns_subject_and_object(Module):
    """Test parse query returns a two item tuple."""
    r = Module.parse_query('foo')
    assert len(r) == 2
    assert isinstance(r, tuple)


def test_generate_repsponse_without_obj(Module):
    """Test generate response when no object exists."""
    assert 'should be able to help you' in Module.generate_response('test')


def test_generate_response_with_obj(Module):
    """Test generate response with a valid object."""
    Module.parse_query = MagicMock(autospec=True,
                                   return_value=('subject', 'object'))
    r = Module.generate_response('test')
    assert 'guaranteed to eliminate _object_' in r


@pytest.mark.parametrize("event", TD.SupportChannel.get('test_events'))
def test_module_update_method(Module, event):
    """Test module update method"""
    b = Module.bot.post_message = MagicMock(autospec=True)
    assert b.call_count == 0
    Module.update(event)

    assert Module.events_received == 1
    if event.get('text'):
        assert Module.events_processed == 1
