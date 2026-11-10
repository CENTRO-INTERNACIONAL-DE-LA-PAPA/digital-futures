from digital_futures.nodes.drivers import task
from digital_futures.nodes.scope import DEFAULT_SCOPE


def test_task_includes_scope_and_seeds():
    prompt = task({"scope": {**DEFAULT_SCOPE, "seed_drivers": ["Cognitive debt"]}})
    assert "Global South" in prompt and "about 80 drivers" in prompt
    assert "Cognitive debt" in prompt
    assert "feedback" not in prompt.lower()


def test_task_on_revision_carries_previous_list_and_feedback():
    previous = [{"id": "d1", "name": "Pollinator decline", "steeple": "environmental"}]
    prompt = task({"scope": DEFAULT_SCOPE, "drivers": previous, "feedback": "add water drivers"})
    assert "Pollinator decline" in prompt
    assert "Reviewer feedback: add water drivers" in prompt
