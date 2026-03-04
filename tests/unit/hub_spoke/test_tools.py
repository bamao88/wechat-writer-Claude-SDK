"""Tests for tool registration module."""
import pytest
from unittest.mock import Mock, patch
from src.agent.hub_spoke.tools import create_tools, tools_to_backend_format
from src.config.settings import Config


class TestCreateTools:
    """Test create_tools function."""

    def test_create_tools_returns_dict(self):
        """create_tools returns a dictionary."""
        config = Mock()
        tools = create_tools(config)

        assert isinstance(tools, dict)

    def test_tools_have_required_attributes(self):
        """Each tool has name, description, input_schema."""
        config = Mock()
        tools = create_tools(config)

        for tool_name, tool in tools.items():
            assert hasattr(tool, 'name')
            assert hasattr(tool, 'description')
            assert hasattr(tool, 'input_schema')
            assert hasattr(tool, 'execute')


class TestToolsToBackendFormat:
    """Test tools_to_backend_format function."""

    def test_converts_to_list_of_dicts(self):
        """Converts tools dict to list of tool definitions."""
        # Mock tools
        mock_tool1 = Mock()
        mock_tool1.name = "tool1"
        mock_tool1.description = "Tool 1 description"
        mock_tool1.input_schema = {"type": "object", "properties": {}}

        mock_tool2 = Mock()
        mock_tool2.name = "tool2"
        mock_tool2.description = "Tool 2 description"
        mock_tool2.input_schema = {"type": "object", "properties": {}}

        tools = {
            "tool1": mock_tool1,
            "tool2": mock_tool2
        }

        backend_tools = tools_to_backend_format(tools)

        assert isinstance(backend_tools, list)
        assert len(backend_tools) == 2

    def test_backend_format_has_required_fields(self):
        """Backend format includes name, description, parameters."""
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.description = "Test tool"
        mock_tool.input_schema = {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"]
        }

        tools = {"test_tool": mock_tool}
        backend_tools = tools_to_backend_format(tools)

        assert len(backend_tools) == 1
        tool_def = backend_tools[0]

        assert tool_def["name"] == "test_tool"
        assert tool_def["description"] == "Test tool"
        assert tool_def["parameters"]["type"] == "object"
        assert "properties" in tool_def["parameters"]

    def test_empty_tools_dict(self):
        """Empty tools dict returns empty list."""
        backend_tools = tools_to_backend_format({})

        assert isinstance(backend_tools, list)
        assert len(backend_tools) == 0
