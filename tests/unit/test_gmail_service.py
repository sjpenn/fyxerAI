import types
from datetime import datetime, timedelta
from django.utils import timezone
import pytest

from core.services.gmail_service import GmailService


class FakeRequest:
    def __init__(self, result=None, capture=None):
        self._result = result or {}
        self._capture = capture

    def execute(self):
        if self._capture is not None:
            # Return what was captured (e.g., the send body)
            return self._capture
        return self._result


class FakeMessagesAPI:
    def __init__(self, pages, messages_data, send_capture):
        self._pages = pages
        self._messages_data = messages_data
        self._send_capture = send_capture

    # List returns pages by token
    def list(self, userId, q=None, maxResults=None, includeSpamTrash=None, labelIds=None, pageToken=None, fields=None):
        return FakeRequest(self._pages.get(pageToken or ''))

    def get(self, userId, id, format=None, fields=None):
        return FakeRequest(self._messages_data[id])

    def send(self, userId, body):
        # Capture body for assertions
        self._send_capture['last_body'] = body
        return FakeRequest({'id': 'SENT', 'threadId': body.get('threadId')})

    def modify(self, userId, id, body):
        return FakeRequest({'id': id})


class FakeDraftsAPI:
    def __init__(self):
        self._last = None

    def create(self, userId, body):
        self._last = body
        return FakeRequest({'id': 'D1', 'message': {'id': 'M1', 'threadId': body['message'].get('threadId')}})

    def send(self, userId, body):
        return FakeRequest({'id': 'SM1', 'threadId': 'T1'})


class FakeUsersAPI:
    def __init__(self, pages, messages_data, send_capture):
        self._messages = FakeMessagesAPI(pages, messages_data, send_capture)
        self._drafts = FakeDraftsAPI()
        self._watch_body = None

    def messages(self):
        return self._messages

    def drafts(self):
        return self._drafts

    def getProfile(self, userId):
        return FakeRequest({'emailAddress': 'test@example.com', 'messagesTotal': 1, 'threadsTotal': 1, 'historyId': '100'})

    def watch(self, userId, body):
        self._watch_body = body
        # expiration is ms since epoch
        return FakeRequest({'historyId': '200', 'expiration': 32503680000000})


class FakeService:
    def __init__(self, pages, messages_data, send_capture):
        self._users = FakeUsersAPI(pages, messages_data, send_capture)

    def users(self):
        return self._users


@pytest.mark.django_db
def test_fetch_history_since_collects_new_messages(monkeypatch):
    # Prepare a history response with messagesAdded
    history_resp = {
        'history': [
            {'id': '101', 'messagesAdded': [{'message': {'id': 'A'}}, {'message': {'id': 'B'}}]},
            {'id': '102', 'messagesAdded': [{'message': {'id': 'C'}}]},
        ],
        'historyId': '102'
    }

    class FakeHistoryAPI:
        def list(self, userId, startHistoryId, historyTypes, labelId, pageToken=None, fields=None):
            return FakeRequest(history_resp)

    class FakeUsersAPI2(FakeUsersAPI):
        def __init__(self, pages, messages_data, send_capture):
            super().__init__(pages, messages_data, send_capture)
            self._history = FakeHistoryAPI()
        def history(self):
            return self._history

    class FakeService2(FakeService):
        def __init__(self, pages, messages_data, send_capture):
            self._users = FakeUsersAPI2(pages, messages_data, send_capture)

    send_capture = {}
    pages = {'': {}}
    msg_payload = {
        'payload': {'headers': [{'name': 'Subject', 'value': 'Hello'}, {'name': 'From', 'value': 'a@b.com'}, {'name': 'To', 'value': 'x@y.com'}, {'name': 'Date', 'value': datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')}]},
        'labelIds': ['INBOX'], 'threadId': 'T1', 'snippet': 'snip'}
    messages_data = {'A': msg_payload, 'B': msg_payload, 'C': msg_payload}

    monkeypatch.setattr(GmailService, '_initialize_service', lambda self: None)
    svc = GmailService('test@example.com')
    svc.credentials = object()
    svc.service = FakeService2(pages, messages_data, send_capture)

    emails, latest = svc.fetch_history_since('100', max_results=10)
    assert len(emails) == 3
    assert latest == '102'


@pytest.mark.django_db
def test_start_watch_saves_history_and_exp(monkeypatch, django_user_model):
    # Create a user and email account
    user = django_user_model.objects.create_user(username='u1', email='test@example.com', password='x')
    from core.models import EmailAccount
    acct = EmailAccount.objects.create(
        user=user, provider='gmail', email_address='test@example.com', display_name='T',
        access_token='t', refresh_token='r', token_expires_at=timezone.now()
    )
    send_capture = {}
    pages = {'': {}}
    messages_data = {}
    monkeypatch.setattr(GmailService, '_initialize_service', lambda self: None)
    svc = GmailService('test@example.com')
    svc.credentials = object()
    svc.service = FakeService(pages, messages_data, send_capture)
    out = svc.start_watch('projects/p/topics/t', ['INBOX'])
    assert out['historyId'] == '200'
    acct.refresh_from_db()
    assert acct.gmail_history_id == '200'
    assert acct.gmail_watch_expiration is not None


@pytest.mark.django_db
def test_fetch_emails_paginates_and_limits(monkeypatch):
    send_capture = {}
    pages = {
        '': {'messages': [{'id': 'A'}, {'id': 'B'}], 'nextPageToken': 'p2'},
        'p2': {'messages': [{'id': 'C'}]},
    }
    msg_payload = {
        'payload': {'headers': [{'name': 'Subject', 'value': 'Hello'}, {'name': 'From', 'value': 'a@b.com'}, {'name': 'To', 'value': 'x@y.com'}, {'name': 'Date', 'value': datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')}]},
        'labelIds': ['INBOX'], 'threadId': 'T1', 'snippet': 'snip'}
    messages_data = {'A': msg_payload, 'B': msg_payload, 'C': msg_payload}

    # Prevent initializer building real service
    monkeypatch.setattr(GmailService, '_initialize_service', lambda self: None)
    svc = GmailService('test@example.com')
    svc.credentials = object()
    svc.service = FakeService(pages, messages_data, send_capture)

    emails = svc.fetch_emails(since_date=timezone.now()-timedelta(days=1), max_results=2)
    assert len(emails) == 2
    assert emails[0]['subject'] == 'Hello'


@pytest.mark.django_db
def test_send_message_includes_thread_id_for_reply(monkeypatch):
    send_capture = {}
    pages = {'': {}}
    orig_headers = {'payload': {'headers': [{'name': 'Message-Id', 'value': '<mid@id>'} ]}, 'threadId': 'THREAD123'}
    messages_data = {'ORIG': orig_headers}

    monkeypatch.setattr(GmailService, '_initialize_service', lambda self: None)
    svc = GmailService('test@example.com')
    svc.credentials = object()
    svc.service = FakeService(pages, messages_data, send_capture)

    sent = svc.send_message('to@ex.com', 'Re: Subj', 'Body', reply_to_id='ORIG')
    assert sent['thread_id'] == 'THREAD123'
    assert send_capture['last_body'].get('threadId') == 'THREAD123'
