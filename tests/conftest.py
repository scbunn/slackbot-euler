"""PyTest common fixtures and utilities."""

import pytest
import testing_data as TD
import eulerbot.slackbot
import eulerbot.eulerbot


@pytest.fixture
def slackbot(monkeypatch, mocker):
    mocker.patch.object(eulerbot.slackbot.SlackClient, 'api_call')
    assert eulerbot.slackbot.SlackClient.api_call.call_count == 0
    monkeypatch.setenv('SLACKBOT_BOT_NAME', TD.slackbot.get('name'))
    monkeypatch.setenv('SLACKBOT_TOKEN', TD.slackbot.get('token'))
    b = eulerbot.slackbot.SlackBot()
    return b


@pytest.fixture
def MockEulerBot(monkeypatch, mocker):
    mocker.patch.object(eulerbot.slackbot.SlackClient, 'api_call')
    assert eulerbot.slackbot.SlackClient.api_call.call_count == 0
    monkeypatch.setenv('SLACKBOT_BOT_NAME', TD.slackbot.get('name'))
    monkeypatch.setenv('SLACKBOT_TOKEN', TD.slackbot.get('token'))
    b = eulerbot.eulerbot.EulerBot()
    for k in b._integrations.keys():
        b._integrations[k].clear()
    return b
