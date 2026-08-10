import pandas as pd
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

from realthor.config import load_config, load_prompt, make_chat_model, resolve_paths
from realthor.tools import make_tools

load_dotenv()


def build_agent(config_path: str = "config.yaml"):
    cfg = resolve_paths(load_config(config_path), config_path)
    model = make_chat_model(cfg)
    system_prompt = load_prompt(cfg["paths"]["prompt"])
    demand = pd.read_csv(cfg["paths"]["demand_data"])
    supply = pd.read_csv(cfg["paths"]["supply_data"])
    tools = make_tools(demand, supply)
    return create_agent(model=model, tools=tools, system_prompt=system_prompt)


if __name__ == "__main__":
    print("Loading agent...")
    agent = build_agent()
    print("Analyzing...")
    result = agent.invoke({
        "messages": [HumanMessage("What's the listing priority for 2-bedroom apartments in the west region?")]
    })
    print(result["messages"][-1].content)
