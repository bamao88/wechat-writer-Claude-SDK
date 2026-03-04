"""Tests for State dataclass."""
import pytest
from dataclasses import asdict
from src.agent.hub_spoke.state import State


class TestStateInitialization:
    """Test State initialization and defaults."""

    def test_state_requires_topic(self):
        """State requires topic as mandatory field."""
        with pytest.raises(TypeError):
            State()

    def test_state_accepts_topic(self):
        """State can be initialized with just topic."""
        state = State(topic="测试选题")
        assert state.topic == "测试选题"

    def test_state_has_default_values(self):
        """State initializes with expected default values."""
        state = State(topic="测试选题")
        assert state.user_context == ""
        assert state.use_private is False
        assert state.use_web is False
        assert state.planner_reason == ""
        assert state.structured_points == []
        assert state.raw_voice_clips == []
        assert state.web_structured_points == []
        assert state.web_raw_quotes == []
        assert state.outline == ""
        assert state.draft == ""
        assert state.critic_score == 0
        assert state.critic_reason == ""
        assert state.critic_feedback == ""
        assert state.iteration_count == 0
        assert state.next_step == "planner"
        assert state.status == "PENDING"

    def test_state_accepts_custom_values(self):
        """State accepts custom values for all fields."""
        state = State(
            topic="测试选题",
            user_context="自定义上下文",
            use_private=True,
            use_web=False,
            next_step="miner",
        )
        assert state.topic == "测试选题"
        assert state.user_context == "自定义上下文"
        assert state.use_private is True
        assert state.use_web is False
        assert state.next_step == "miner"


class TestStateFieldTypes:
    """Test State field type validation."""

    def test_topic_is_string(self):
        """Topic field must be a string."""
        state = State(topic="测试选题")
        assert isinstance(state.topic, str)

    def test_structured_points_is_list(self):
        """structured_points field is a list."""
        state = State(topic="测试")
        assert isinstance(state.structured_points, list)
        state.structured_points.append("观点A")
        assert len(state.structured_points) == 1

    def test_raw_voice_clips_is_list(self):
        """raw_voice_clips field is a list."""
        state = State(topic="测试")
        assert isinstance(state.raw_voice_clips, list)
        state.raw_voice_clips.append("原话片段")
        assert len(state.raw_voice_clips) == 1

    def test_boolean_fields(self):
        """Boolean fields accept bool values."""
        state = State(topic="测试", use_private=True, use_web=True)
        assert state.use_private is True
        assert state.use_web is True


class TestStateSerialization:
    """Test State serialization to dict/JSON."""

    def test_state_can_be_converted_to_dict(self):
        """State can be serialized to dict using asdict()."""
        state = State(topic="测试选题")
        state_dict = asdict(state)
        assert isinstance(state_dict, dict)
        assert state_dict["topic"] == "测试选题"
        assert state_dict["status"] == "PENDING"

    def test_serialized_dict_contains_all_fields(self):
        """Serialized dict contains all State fields."""
        state = State(topic="测试")
        state_dict = asdict(state)
        expected_fields = [
            "topic", "user_context", "use_private", "use_web",
            "planner_reason", "structured_points", "raw_voice_clips",
            "web_structured_points", "web_raw_quotes",
            "outline", "draft", "critic_score",
            "critic_reason", "critic_feedback", "iteration_count",
            "next_step", "status"
        ]
        for field in expected_fields:
            assert field in state_dict

    def test_state_with_complex_data_serializes(self):
        """State with lists and nested data serializes correctly."""
        state = State(
            topic="测试",
            structured_points=["观点A", "观点B"],
            raw_voice_clips=["片段1", "片段2"],
        )
        state_dict = asdict(state)
        assert state_dict["structured_points"] == ["观点A", "观点B"]
        assert state_dict["raw_voice_clips"] == ["片段1", "片段2"]


class TestStateMutability:
    """Test State mutability and updates."""

    def test_state_fields_can_be_updated(self):
        """State fields can be updated after initialization."""
        state = State(topic="测试")
        state.use_private = True
        state.planner_reason = "需要私域调研"
        state.next_step = "miner"
        assert state.use_private is True
        assert state.planner_reason == "需要私域调研"
        assert state.next_step == "miner"

    def test_state_lists_can_be_appended(self):
        """State list fields support append operations."""
        state = State(topic="测试")
        state.structured_points.append("观点A")
        state.raw_voice_clips.append("片段1")
        assert len(state.structured_points) == 1
        assert len(state.raw_voice_clips) == 1

    def test_iteration_count_increments(self):
        """iteration_count can be incremented."""
        state = State(topic="测试")
        assert state.iteration_count == 0
        state.iteration_count += 1
        assert state.iteration_count == 1
