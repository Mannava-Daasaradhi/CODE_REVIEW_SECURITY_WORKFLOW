import pytest
from pydantic import ValidationError

from app.models.action import Action, Finding
from app.models.observation import Observation
from app.models.reward import StepResult
from app.models.state import EnvironmentState


def test_action_defaults():
    action = Action()
    assert action.flagged_lines == []
    assert action.findings == []
    assert action.review_text == ""


def test_action_with_data():
    action = Action(
        flagged_lines=[1, 2, 3],
        findings=[Finding(type="sql_injection", description="test")],
        review_text="looks bad",
    )
    assert len(action.flagged_lines) == 3
    assert len(action.findings) == 1


def test_observation_required_fields():
    obs = Observation(
        task_id="task1_ep_001",
        difficulty="easy",
        code_snippet="def foo(): pass",
        instructions="Find the bugs.",
    )
    assert obs.task_id == "task1_ep_001"


def test_step_result_reward_bounds():
    obs = Observation(task_id="t", difficulty="easy", code_snippet="x", instructions="y")
    result = StepResult(observation=obs, reward=0.75, done=True, info={})
    assert result.reward == 0.75


def test_step_result_reward_out_of_bounds():
    obs = Observation(task_id="t", difficulty="easy", code_snippet="x", instructions="y")
    with pytest.raises(ValidationError):
        StepResult(observation=obs, reward=1.5, done=True, info={})


def test_environment_state_uninitialized():
    state = EnvironmentState(
        initialized=False,
        current_task_id=None,
        difficulty=None,
        step_count=0,
        last_reward=None,
    )
    assert state.initialized is False
