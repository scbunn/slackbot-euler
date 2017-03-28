"""Support Integration Tests

Unit test the support integration module."""
import pytest
import string
import spacy
import testing_data as TD
from eulerbot.integrations.support import ChannelSupport
from unittest.mock import MagicMock


def text_blob_id(param):
    """Return a test id for large text blobs."""
    return "Slack event text: {}...".format(param[-10:-1])


@pytest.fixture
def Module(MockEulerBot):
    """ChannelSupport integration module instance."""
    MockEulerBot.sc.rtm_connect = MagicMock(autospec=True)
    MockEulerBot.sc.rtm_read = MagicMock(autospec=True)
    return ChannelSupport(MockEulerBot)


@pytest.mark.parametrize("v, t", [
    ("_parser", None),
    ("trigger_words", list)
])
def test_module_default_initialization_state(Module, v, t):
    """Test that the module has a default state that is expected"""
    if t is None:
        assert Module.__dict__[v] is None
    else:
        assert isinstance(Module.__dict__[v], t)


@pytest.mark.slow
@pytest.mark.NLP
def test_nlp_parser_property_loads_once(Module):
    """Test that we only load NLP parser once"""
    Module.parser
    assert Module._parser is not None
    Module.parser


@pytest.mark.slow
@pytest.mark.NLP
def test_nlp_parser_property_loads_spacy_english_parser(Module):
    """Test that spacy loads as expected"""
    Module.parser
    assert isinstance(Module._parser, spacy.en.English)


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


def test_parsing_remove_punctuation(Module):
    """Test that remove_punctuation works as expected."""
    s = "This is a sentence; however, it doesn't {} work".format(
        string.punctuation)
    o = Module.remove_punctuation(s)
    assert string.punctuation not in o


@pytest.mark.parametrize("blob, url", [
    ('This is <http://www.google.com>', 'http://www.google.com'),
    ('A second <http://www.dom.com|some site>', 'http://www.dom.com')],
    ids=['single url', 'url with title']
)
def test_url_extraction(Module, blob, url):
    """Test that url extraction works."""
    t, r = Module.extract_urls(blob)
    assert url in r


@pytest.mark.slow
@pytest.mark.nlp
@pytest.mark.parametrize("blob", TD.SupportChannel.get('text_blobs'),
                         ids=text_blob_id)
def test_nlp_subject_object_parsing(Module, blob):
    """Test that various blobs don't blow parsing up.

    TODO: do something better here."""
    doc = Module.parser(blob)
    s, o = Module._get_subject_objects(doc)


@pytest.mark.parametrize("event", TD.SupportChannel.get('test_events'))
def test_module_update_method(Module, event):
    """Test module update method"""
    b = Module.bot.post_message = MagicMock(autospec=True)
    assert b.call_count == 0
    Module.update(event)

    if event.get('text'):
        assert Module.bot.events_processed == 1

    if Module.has_trigger_word(event.get('text')):
        assert b.call_count == 1
        assert event.get('user') in b.call_args[0][1]
