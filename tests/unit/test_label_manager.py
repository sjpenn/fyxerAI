import pytest
from core.services.label_manager import LabelManager


class FakeGmailService:
    def __init__(self):
        self._batched = []
        self._labels = {'urgent': 'L1', 'important': 'L2', 'routine': 'L3'}
        self._authed = True

    def is_authenticated(self):
        return self._authed

    def setup_fyxerai_labels(self):
        return self._labels

    def batch_modify(self, ids, add_label_ids=None, remove_label_ids=None):
        self._batched.append((tuple(ids), tuple(add_label_ids or [])))
        return True


@pytest.mark.django_db
def test_label_manager_batches_apply_label(monkeypatch):
    lm = LabelManager('user@example.com', platform='gmail')
    fake = FakeGmailService()
    lm.gmail_service = fake

    emails = [{'id': 'A'}, {'id': 'B'}, {'id': 'C'}]
    results = [
        {'category': 'urgent', 'confidence': 0.9},
        {'category': 'urgent', 'confidence': 0.8},
        {'category': 'routine', 'confidence': 0.7},
    ]

    out = lm.process_triage_results(emails, results, use_batch=True)
    # Expect two batch calls (urgent and routine)
    assert len(fake._batched) == 2
    # Urgent includes A,B with label L1
    assert (('A','B'), ('L1',)) in fake._batched
    # Routine includes C with label L3
    assert (('C',), ('L3',)) in fake._batched
    assert out['processed_count'] == 3
