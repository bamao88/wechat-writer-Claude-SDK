"""Tool registration and management for hub-spoke architecture."""
from typing import Dict, Any, List
from src.config.settings import Config
from src.tools.notebooklm import NotebookLMTool
from src.tools.web_search import WebSearchTool


def create_tools(config: Config) -> Dict[str, Any]:
    """Create all available tools for the agent system.

    Args:
        config: Application configuration

    Returns:
        Dictionary mapping tool names to tool instances
    """
    tools = {}

    # Add NotebookLM tool (private domain research)
    try:
        notebooklm_tool = NotebookLMTool(config)
        tools[notebooklm_tool.name] = notebooklm_tool
    except Exception as e:
        # NotebookLM is optional, skip if unavailable
        pass

    # Add Web Search tool (public research)
    try:
        web_tool = WebSearchTool(config)
        tools[web_tool.name] = web_tool
    except Exception as e:
        # Web search is optional, skip if unavailable
        pass

    return tools


def tools_to_backend_format(tools: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert tools to LLM backend format.

    Args:
        tools: Dictionary of tool instances

    Returns:
        List of tool definitions in backend format (for Anthropic/OpenAI)
    """
    backend_tools = []

    for tool_name, tool in tools.items():
        # Each tool should have name, description, input_schema
        tool_def = {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.input_schema
        }
        backend_tools.append(tool_def)

    return backend_tools
