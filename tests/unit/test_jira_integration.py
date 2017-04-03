"""Jira Integration


Test the Jira Integration."""
import beaker
import pytest
import testing_data as TD
from eulerbot.integrations.jira import JiraManagement
from unittest.mock import MagicMock

pytestmark = pytest.mark.jira


@pytest.fixture
def JiraInt(MockEulerBot):
    """Return an instance of the JiraManagement integration."""
    MockEulerBot.sc.rtm_connect = MagicMock(autospec=True)
    MockEulerBot.sc.rtm_read = MagicMock(autospec=True)
    j = JiraManagement(MockEulerBot, 'channel')
    j.key = 'TID'
    return j


def test_default_state(JiraInt):
    """Test the default state of the JiraManagement object."""
    assert JiraInt.message_type == 'channel'
    assert JiraInt.events_received == 0
    assert JiraInt.events_processed == 0
    assert isinstance(JiraInt.key, str)
    assert isinstance(JiraInt.cache, beaker.cache.Cache)


@pytest.mark.parametrize("text, expected", TD.jira.get('key_blobs'))
def test_has_jira_key_returns_true_if_project_key(JiraInt, text, expected):
    r = JiraInt.has_jira_key(text)
    if r:
        assert r is True
        return
    assert r is None


@pytest.mark.parametrize("text, expected", TD.jira.get('key_blobs'))
def test_extract_key_extracts_the_right_key(JiraInt, text, expected):
    if JiraInt.has_jira_key(text):
        issue_id = JiraInt.extract_issue_id(text)
        if issue_id:
            assert issue_id == 'TID-123'


def test_post_issue_link_with_valid_issue(JiraInt):
    JiraInt.manager.issue = MagicMock(autospec=True)
    JiraInt.manager.issue.side_effect = TD.MockJiraIssue
    JiraInt.bot.post_message = MagicMock(autospec=True)
    text = 'This line of text has a valid TID-123 project key'
    JiraInt.post_issue_link('CHANNEL', 'USER1', text)
    JiraInt.bot.post_message.assert_called_once_with(
        'CHANNEL',
        'TID-123 <https://jira.dom/browse/TID-123|Ticket Summary>'
    )


def test_post_issue_link_with_invalid_issue(JiraInt):
    JiraInt.manager.issue = MagicMock(autospec=True)
    JiraInt.manager.issue.return_value = None
    JiraInt.bot.post_message = MagicMock(autospec=True)
    text = 'This line of text contains a TID-123234234 key that is 404'
    JiraInt.post_issue_link('CHANNEL', 'USER1', text)
    t = '<@USER1>, are you sure TID-123234234 is a valid Jira issue? '
    t += "I couldn't find it."
    JiraInt.bot.post_message.assert_called_once_with(
        'CHANNEL',
        t
    )


def test_update_returns_if_event_has_no_text(JiraInt):
    event = {'channel': 'CHANNEL'}
    JiraInt.post_issue_link = MagicMock(autospec=True)
    JiraInt.update(event)
    assert JiraInt.post_issue_link.call_count == 0


def test_update_triggers_post_issue_link(JiraInt):
    event = {'channel': 'CHANNEL', 'user': 'USER1', 'text': 'foo'}
    JiraInt.post_issue_link = MagicMock(autospec=True)
    JiraInt.update(event)
    assert JiraInt.post_issue_link.call_count == 1
