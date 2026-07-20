from langchain.agents import create_agent

from realthor.config import load_prompt, make_chat_model
from realthor.tools import make_tools


def build_agent(cfg: dict, checkpointer=None):
    """Build the reduced demo agent. Accepts any checkpointer (InMemorySaver or SqliteSaver)."""
    model = make_chat_model(cfg)
    system_prompt = load_prompt(cfg["paths"]["prompt"])
    return create_agent(
        model=model,
        tools=make_tools(cfg),
        system_prompt=system_prompt,
        checkpointer=checkpointer,
    )
