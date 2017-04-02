"""Support Integration OpsGenie

Test the Support OpsGenie integration."""
import pytest
import testing_data as TD
import requests
from eulerbot.integrations.support import OpsGenieSchedule

pytestmark = pytest.mark.support_opsgenie


def mocked_request_get(*args, **kwargs):
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return self.json_data

    if args[0] == 'https://api.opsgenie.com/v1.1/json/schedule/fail':
        return MockResponse(TD.SupportChannel.get('opsgenie')['error'], 403)

    if args[0].startswith('https://api.opsgenie.com/v1.1/json/schedule'):
        return MockResponse(TD.SupportChannel.get('opsgenie')['oncall'], 200)

    if args[0] == 'fail_request':
        return MockResponse(TD.SupportChannel.get('opsgenie')['error'], 500)

    return MockResponse({}, 404)


@pytest.fixture
def OGS(mocker, monkeypatch):
    """Return an instance of the OpsGenieSchedule class"""
    mocker.patch('requests.get', autospec=True)
    requests.get.side_effect = mocked_request_get
    monkeypatch.setenv('OPSGENIE_API_KEY', 'api_key')
    return OpsGenieSchedule()


def test_request_fails_with_bad_payload_type(OGS):
    r = OGS._request('test', 'payload')
    assert requests.get.call_count == 0
    assert r is None


def test_request_builds_correct_url(OGS):
    """Test that the payload is correct"""
    payload = {'name': 'testing'}
    url = 'https://api.opsgenie.com/v1.1/json/schedule/test'
    OGS._request('test', payload)
    payload['apiKey'] = 'api_key'
    requests.get.assert_called_once_with(url, payload)


def test_request_returns_dict_with_status_200(OGS):
    """Test that a successful request with a 200 returns json as dict"""
    d = OGS._request('test', {'name': 'test'})
    assert isinstance(d, dict)


def test_failed_request_returns_none(OGS):
    """Test that none is returned for failed requests."""
    assert OGS._request('fail', {}) is None


def test_oncall_success_returns_participant(OGS):
    """Test that a successful lookup returns one or more participants."""
    r = OGS.on_call('Team2')
    print(r)
    assert 'user@team2.dom' == r


def test_oncall_failure_returns_unknown(OGS):
    """Test that if on_call fails, it returns unknown as the 'user'"""
    r = OGS.on_call('Fail')
    assert r == 'unknown'


def test_oncalls_returns_list_of_on_call_teams(OGS):
    """test that on_calls returns a list of teams"""
    r = OGS.on_calls()
    assert isinstance(r, list)
    requests.get.assert_called_once_with(
        'https://api.opsgenie.com/v1.1/json/schedule/whoIsOnCall',
        {'apiKey': 'api_key'})


def test_oncalls_failure_returns_none(mocker, monkeypatch):
    """Test that a failed opsgenie lookup returns none"""
    monkeypatch.setenv('OPSGENIE_API_KEY', 'api_key')
    mocker.patch('requests.get', autospec=True)
    requests.get.return_value = mocked_request_get('fail_request')
    o = OpsGenieSchedule()
    r = o.on_calls()
    assert r is None
