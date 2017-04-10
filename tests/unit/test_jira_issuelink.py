"""Jira IssueLink


Test the IssueLink object.

Notes:
    PropertyMock does not work when with a side_effect of AttributeError
    In order to get this behavior we need a basic mock with an empty spec
"""
import pytest
import testing_data as TD
from eulerbot.integrations.jira import IssueLink
from eulerbot.slackbot import SlackUser
from unittest.mock import Mock, MagicMock, PropertyMock

pytestmark = pytest.mark.jira


@pytest.fixture
def SlackUsers():
    """Return a list of SlackUsers"""
    users_list = TD.load_json('tests/data/slackbot_user_list.json').get(
        'user_list').get('members')
    users = []
    for member in users_list:
        u = SlackUser()
        u.uid = member.get('id')
        u.name = member.get('name')
        u._profile = member.get('profile')
        users.append(u)
    return users


@pytest.fixture
def IssueFields():
    """return dict of issuelink attachment"""
    return TD.load_json('tests/data/jira_single_issue.json')['fields']


@pytest.fixture
def IL(MockEulerBot):
    """Return an instance of a patched IssueLink"""
    MockEulerBot.sc.rtm_connect = MagicMock(autospec=True)
    MockEulerBot.sc.rtm_read = MagicMock(autospec=True)
    j = IssueLink(
        TD.MockJiraIssue(),
        MagicMock(),
        []
    )
    return j


@pytest.fixture
def ILM(IL):
    """Return an instanced of IssueLink that will raise an AttributeError when
    access a field."""
    IL.issue.fields = Mock(spec=[])
    return IL


@pytest.mark.parametrize("email, md5hash", [
    ('user@dom', '16332cdac2d732f22bbf56ff844a096f'),
    ('user1@dom', 'e34f246f527378d1a2b2fabe8fb4af37'),
    ('user2@dom', 'd848ce2b9dcacc28ce57d8f09b479306'),
    ('user2@sub.dom', '168df7f8ef2a4b6b40f313c2975a515a'),
])
def test_hash_email_returns_md5(IL, email, md5hash):
    """Test that hash email returns expected MD5 sum"""
    assert IL.hash_email(email) == md5hash


def test_hash_works_with_unicode(IL):
    """Test that hash doesn't blow up with non-ascii character sets"""
    assert IL.hash_email(
        '甲斐@黒川.日本') == 'b072b7430d7c799ca1be2c392ee21322'


@pytest.mark.parametrize("email_hash", [
    '16332cdac2d732f22bbf56ff844a096f',
    'e34f246f527378d1a2b2fabe8fb4af37',
    'd848ce2b9dcacc28ce57d8f09b479306',
    '168df7f8ef2a4b6b40f313c2975a515a',
    'b072b7430d7c799ca1be2c392ee21322'
])
def test_gravatar_url_generation(IL, email_hash):
    """test that gravatar method returns valid gravatar URL"""
    expected_url = 'https://www.gravatar.com/avatar/{}'.format(
        email_hash)
    assert expected_url in IL.gravatar(email_hash)


def test_add_status_with_a_valid_field(IL):
    """Test that status gets added to attachment if field exists"""
    IL.issue.fields.status = 'Open'
    IL._add_status()
    assert IL._attachment['title'] == 'Status: Open'


def test_add_stats_with_missing_field(ILM):
    """Test that add status does not add a title if the field is missing."""
    ILM._add_status()
    assert not ILM._attachment.get('title')


def test_add_footer_with_updated_field_no_priority(IL, IssueFields):
    """Test that the correct footer is generated when updated field exists."""
    type(IL.issue.fields).updated = PropertyMock(
        return_value=IssueFields.get('updated'))
    IL._add_footer()
    assert IL._attachment['footer'] == 'Last updated'
    assert IL._attachment['ts'] == 77640039


def test_add_footer_with_updated_field_and_priority(IL, IssueFields):
    """Test that the correct footer is generated with time and priority"""
    type(IL.issue.fields).updated = PropertyMock(
        return_value=IssueFields.get('updated'))
    type(IL.issue.fields).priority = PropertyMock()
    type(IL.issue.fields.priority).iconUrl = PropertyMock(
        return_value=IssueFields.get('priority').get('iconUrl'))
    IL._add_footer()
    assert IL._attachment['footer'] == 'Last updated'
    assert IL._attachment['ts'] == 77640039
    assert IL._attachment['footer_icon'] == IssueFields.get('priority').get(
        'iconUrl')


def test_add_footer_with_no_updated_field(ILM):
    """Test that if updated field is missing, the footer is skipped"""
    ILM._add_footer()
    assert not ILM._attachment.get('footer')
    assert not ILM._attachment.get('footer_icon')


def test_add_footer_with_malformed_date(IL):
    """Test that footer is skipped with a bad date"""
    type(IL.issue.fields).updated = PropertyMock(
        return_value='foobar')
    IL._add_footer()
    assert not IL._attachment.get('footer')
    assert not IL._attachment.get('ts')
    assert not IL._attachment.get('footer_icon')


def test_add_epic_with_no_epic_on_issue(ILM):
    """Test that a missing epic key does not add epic field"""
    ILM._add_epic()
    assert len(ILM._attachment['fields']) == 0


def test_add_epic_creates_epic_field(IL):
    """Test that epic field is added if issue has valid epic id"""
    IL.jira.issue = MagicMock(side_effect=TD.MockJiraIssue)
    IL._add_epic()
    epic = IL._attachment['fields'][0]
    epic_url = '<{}|{}>'.format(
        'https://jira.dom/browse/EPIC-01',
        'Ticket Summary')
    assert epic['title'] == 'Epic'
    assert epic['value'] == epic_url
    assert epic['short'] is True


def test_add_story_points_with_no_field(ILM):
    """Test that estimation field is skipped if missing story point field."""
    ILM._add_story_points()
    assert len(ILM._attachment['fields']) == 0


@pytest.mark.parametrize("data", ['', '13.2', None])
def test_add_story_points_with_empty_field_data(IL, data):
    """Test that method skips field with empty data"""
    type(IL.issue.fields).customfield_10003 = PropertyMock(
        return_value=data)
    IL._add_story_points()
    assert len(IL._attachment['fields']) == 0


def test_add_story_points_with_valid_estimation_value(IL):
    """Test that estimation field is added with valid story points."""
    type(IL.issue.fields).customfield_10003 = PropertyMock(
        return_value=20)
    IL._add_story_points()
    sp = IL._attachment['fields'][0]
    print(sp)
    assert sp['title'] == 'Estimation'
    assert sp['value'] == ':clock2: 20 hours'
    assert sp['short'] is True


def test_add_labels_with_no_field(ILM):
    """Test that no label field is added if field is missing from issue."""
    ILM._add_labels()
    assert len(ILM._attachment['fields']) == 0


def test_add_labels_field_with_valid_labels(IL):
    """Test that label field is added with valid labels from issue."""
    type(IL.issue.fields).lables = PropertyMock(
        return_value=['label1', 'label2'])
    IL._add_labels()
    labels = IL._attachment['fields'][0]
    assert labels['title'] == 'Labels'
    assert labels['value'] == 'label1, label2'
    assert labels['short'] is False


def test_slack_to_email_user_match_returns_right_data(IL, SlackUsers):
    """Test that a matching email address returns the correct data"""
    IL.users = SlackUsers
    assert '<@U023BECGF>' == IL._email_to_slack('testinggoat@slack.com')


def test_slack_to_email_returns_default_if_no_match(IL, SlackUsers):
    """Test that a non email match returns the default user name"""
    IL.users = SlackUsers
    assert 'Mystery Man' == IL._email_to_slack('notreal@dom')
    assert 'Default 1' == IL._email_to_slack('notreal@dom',
                                             default='Default 1')


def test_reporter_field_added_with_valid_reporter(IL):
    """Test that reporter field is added when a valid reporter field exists
    with the issue."""
    type(IL.issue.fields).reporter = PropertyMock()
    type(IL.issue.fields.reporter).displayName = PropertyMock(
        return_value="Test user")
    IL._add_reporter()
    reporter = IL._attachment['fields'][0]
    assert reporter['title'] == 'Reported'
    assert reporter['value'] == ':bust_in_silhouette: Test user'
    assert reporter['short'] is True


def test_reporter_field_skipped_with_missing_data(ILM):
    """Test that no reporter field is added when reporter field is missing
    from the issue."""
    ILM._add_reporter()
    assert len(ILM._attachment['fields']) == 0


def test_assigned_skipped_if_not_unassigned_issue(ILM):
    """Test that no assigned field is added if the ticket is not assigned."""
    ILM._add_assignee()
    assert len(ILM._attachment['fields']) == 0


def test_assigned_added_with_realname_if_no_email_match(IL, SlackUsers):
    """Test that assigned field added with real name if there is no email
    user match."""
    IL.users = SlackUsers
    type(IL.issue.fields).assignee = PropertyMock()
    type(IL.issue.fields.assignee).emailAddress = PropertyMock(
        return_value='notreal@dom')
    type(IL.issue.fields.assignee).displayName = PropertyMock(
        return_value="Reporter User")
    IL._add_assignee()
    assigned = IL._attachment['fields'][0]
    assert assigned['title'] == 'Assigned'
    assert assigned['value'] == ':bust_in_silhouette: Reporter User'
    assert assigned['short'] is True


def test_assigned_added_with_atcall_if_email_match(IL, SlackUsers):
    """Test that assigned field is added with @mention if there is a email
    to slack user match."""
    IL.users = SlackUsers
    type(IL.issue.fields).assignee = PropertyMock()
    type(IL.issue.fields.assignee).emailAddress = PropertyMock(
        return_value='testinggoat@slack.com')
    type(IL.issue.fields.assignee).displayName = PropertyMock(
        return_value="Reporting User")
    IL._add_assignee()
    assigned = IL._attachment['fields'][0]
    assert assigned['title'] == 'Assigned'
    assert assigned['value'] == ':bust_in_silhouette: <@U023BECGF>'
    assert assigned['short'] is True


def test_add_thumbnail_icon_if_assigned(IL, SlackUsers):
    """Test that a thumbnail icon is added if assigned"""
    IL.users = SlackUsers
    type(IL.issue.fields).assignee = PropertyMock()
    type(IL.issue.fields.assignee).emailAddress = PropertyMock(
        return_value="testinggoat@slack.com")
    IL._add_thumbnail_icon()
    thumb_url = \
        'https://www.gravatar.com/avatar/d08987c41a78174527758fff93d61c0e'
    assert thumb_url in IL._attachment['thumb_url']


def test_add_thumbnail_skipped_if_not_assigned(ILM):
    """Test that no thumbnail is added if not assigned"""
    ILM._add_thumbnail_icon()
    assert not ILM._attachment.get('thumb_url')


def test_color_is_gray_if_no_issuetype_field(ILM):
    """Test that attachment color is set to gray if issue type field is
    not part of the issue."""
    ILM._add_color()
    assert ILM._attachment['color'] == '#a9a9a9'


@pytest.mark.parametrize('issue_type, color', [
    ('epic', '#a9a9a9'),
    ('story', 'good'),
    ('bug', 'danger')
])
def test_issue_type_match_color(IL, issue_type, color):
    type(IL.issue.fields).issuetype = PropertyMock()
    type(IL.issue.fields.issuetype).name = PropertyMock(
        return_value=issue_type)
    IL._add_color()
    assert IL._attachment['color'] == color


def test_add_issue_title_skipped_if_no_field(ILM):
    """Test that title is skipped if fields are broke"""
    ILM._add_issue_title()
    assert not ILM._attachment.get('author_name')
    assert not ILM._attachment.get('author_link')
    assert not ILM._attachment.get('author_icon')


def test_add_issue_tile_fields_are_added(IL):
    """Test that issue title is added when fields are available in issue."""
    type(IL.issue.fields).issuetype = PropertyMock()
    type(IL.issue.fields.issuetype).iconUrl = PropertyMock(
        return_value='http://jira.dom/icon.png')
    IL._add_issue_title()
    assert IL._attachment['author_name'] == 'CIT-01 - Ticket Summary'
    assert IL._attachment['author_link'] == 'https://jira.dom/browse/CIT-01'
    assert IL._attachment['author_icon'] == 'http://jira.dom/icon.png'


def test_add_description_skipped_if_missing_field(ILM):
    """Test that no description field is added if missing"""
    ILM._add_issue_description()
    assert not ILM._attachment.get('text')


def test_add_description_if_field_exists(IL):
    """Test that description is added if the field exists"""
    IL._add_issue_description()
    desc = IL._attachment.get('text')
    assert desc == 'Ticket description\r\nSecond Line'


def test_desription_longer_than_100_characters(IL):
    """Test that the description is cutoff at 100 characters."""
    desc = 'A' * 1000
    expected = '{}... <https://jira.dom/browse/CIT-01|read more>'.format(
        desc[:100])
    type(IL.issue.fields).description = PropertyMock(
        return_value=desc)
    IL._add_issue_description()
    assert IL._attachment['text'] == expected
    assert len(IL._attachment['text']) < 150
