"""JiraManager Unit tests

Test the JiraManager object."""
import pytest
import testing_data as TD
import uuid
import jira
import requests
from beaker.cache import Cache
from eulerbot.integrations.jira import JiraManager
from unittest.mock import MagicMock

pytestmark = pytest.mark.jira


@pytest.fixture
def BeakerCache():
    """Return an cache instance that can be used for testing"""
    cache = Cache('testing-{}'.format(uuid.uuid4()),
                  lock_dir='/tmp/citesting.{}'.format(uuid.uuid4()),
                  type='memory')
    return cache


@pytest.fixture
def JM(BeakerCache):
    """Return a JiraManager with a mocked requests interface."""
    jm = JiraManager(BeakerCache)
    jm._jira = MagicMock(autospec=True)
    return jm


@pytest.mark.parametrize("prop, var, setting", [
    ('server', 'JIRA_SERVER', 'http://jiraserver.dom'),
    ('user', 'JIRA_USER', 'jira_testing_user'),
    ('password', 'JIRA_PASSWORD', 'foobar')
], ids=['JIRA_SERVER', 'JIRA_USER', 'JIRA_PASSWORD'])
def test_environment_variable_overwrites_deafult_setting(monkeypatch,
                                                         prop, var, setting):
    """Assert that env settings overwrite defaults."""
    monkeypatch.setenv(var, setting)
    j = JiraManager(BeakerCache)
    assert getattr(j, prop) == setting


def test_issue_is_cached(JM):
    """Test that an issue is put into the cache"""
    key = 'jira.issue.CIT-01'
    assert key not in JM.cache
    JM.issue('CIT-01')
    JM.issue('CIT-01')
    assert key in JM.cache
    assert JM.jira.issue.call_count == 1


def test_jm_issue_returns_issue_on_success(JM):
    """Test that an issue is returned if Jira call is successful."""
    JM.jira.issue = MagicMock(autospec=True)
    JM.jira.issue.side_effect = TD.MockJiraIssue
    i = JM.issue('TID-01')
    assert 'Ticket Summary' == i.fields.summary
    f = ','.join(JM.issue_fields)
    JM.jira.issue.assert_called_once_with('TID-01', fields=f)


def test_jm_issue_error_returns_none(JM):
    """Test issue exceptions behave responsibly."""
    JM.logger.warning = MagicMock(autospec=True)
    JM.jira.issue = MagicMock(autospec=True)
    JM.jira.issue.side_effect = jira.exceptions.JIRAError('error')
    i = JM.issue('TID-01')
    assert i is None
    JM.logger.warning.assert_called_once()


def test_jm_jira_property(BeakerCache, mocker):
    """Test Jira Property loads jira client on first use."""
    JM = JiraManager(BeakerCache)
    mocker.patch('eulerbot.integrations.jira.JIRA', autospec=True,
                 return_value='Jira Loaded')
    assert not JM._jira
    JM.jira
    assert JM._jira == 'Jira Loaded'


def test_jm_connection_error_is_graceful(mocker):
    """Test that connections to jira are handled gracefully."""
    JM = JiraManager(BeakerCache)
    mocker.patch('eulerbot.integrations.jira.JIRA', autospec=True,
                 side_effect=requests.exceptions.ConnectionError('error'))
    JM.logger.error = MagicMock(autospec=True)
    JM.jira
    assert JM._jira is None
    assert JM.logger.error.call_count == 1
