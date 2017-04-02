"""Language Processor

Test the NLP of the support integration."""
import pytest
import spacy
import string
import testing_data as TD
from eulerbot.integrations.support import LanguageParser

pytestmark = pytest.mark.support_nlp


@pytest.fixture
def LPMS(mocker):
    """Return an instance of the LanguageParser"""
    mocker.patch('spacy.load', return_value='spacy loaded')
    return LanguageParser()


@pytest.mark.slow
@pytest.fixture()
def LP(monkeypatch):
    """Return an instance of LanguageParser without spacy mocked."""
    monkeypatch.setenv('SLACKBOT_SUPPORT_NLP_MODEL', 'en_core_web_sm')
    return LanguageParser()


def text_blob_id(param):
    """Return a test id for large text blobs."""
    return "Slack event text: {}...".format(param[-10:-1])


def test_nlp_parser_property_loads_once(LPMS):
    """Test that we only load NLP parser once"""
    LPMS.parser
    assert LPMS.parser == 'spacy loaded'
    spacy.load.call_count == 1


def test_nlp_parser_property_loads_correct_model(mocker, monkeypatch):
    """Test that the correct spacy model is loaded."""
    monkeypatch.setenv('SLACKBOT_SUPPORT_NLP_MODEL', 'test_model')
    mocker.patch('spacy.load', return_value='spacy')
    lp = LanguageParser()
    assert lp.parser
    spacy.load.assert_called_once_with('test_model')


def test_parsing_remove_punctuation(LPMS):
    """Test that remove_punctuation works as expected."""
    s = "This is a sentence; however, it doesn't {} work".format(
        string.punctuation)
    o = LPMS.remove_punctuation(s)
    assert string.punctuation not in o


@pytest.mark.parametrize("blob, url", [
    ('This is <http://www.google.com>', 'http://www.google.com'),
    ('A second <http://www.dom.com|some site>', 'http://www.dom.com')],
    ids=['single url', 'url with title']
)
def test_urls_can_be_found_in_test(LPMS, blob, url):
    """Test that url extraction works."""
    r = LPMS.find_urls(blob)
    assert url in r


@pytest.mark.parametrize("blob", [
    'This is <http://www.google.com>',
    'A second <http://www.dom.com|some site>'],
    ids=['single url', 'url with title']
)
def test_urls_extraction_from_text(LPMS, blob):
    """Test that url extraction works."""
    r = LPMS.remove_urls(blob)
    assert not LPMS.find_urls(r)


def test_doc_property_loads_the_document(LPMS, mocker):
    """Test to make sure the document gets loaded in the property."""
    mocker.patch('eulerbot.integrations.support.LanguageParser.parser',
                 return_value='doc parsed')
    LPMS.doc = 'testing'
    assert LPMS._doc == 'doc parsed'


def test_noun_chunks_returns_empty_dict_with_no_text(LPMS):
    """Test that property for doc returns and empty list if no
    test has been parsed."""
    l = LPMS.noun_chunks()
    assert isinstance(l, list)
    assert len(l) == 0


def test_noun_chunks_returns_a_non_empty_list(LP):
    """Test that noun_chunks returns a list of chunks."""
    LP.doc = "Let leash the dogs of war"
    chunks = LP.noun_chunks()
    l = []
    for chunk in chunks:
        l.append(chunk)
    assert len(l) > 0


@pytest.mark.parametrize("blob", TD.SupportChannel.get('text_blobs'),
                         ids=text_blob_id)
def test_nlp_subject_parsing(LP, blob):
    LP.doc = blob
    r = LP.subject()
    assert r
    assert isinstance(r, str)


@pytest.mark.parametrize("blob", TD.SupportChannel.get('text_blobs'),
                         ids=text_blob_id)
def test_nlp_object_parsing(LP, blob):
    LP.doc = blob
    r = LP.sobject()
    if r:
        assert isinstance(r, str)
