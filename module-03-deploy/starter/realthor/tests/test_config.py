"""Unit tests for realthor.config utilities."""

import pathlib
import pandas as pd
import pytest
from realthor.config import load_config, load_prompt, resolve_paths, build_context


CONFIG_PATH = str(pathlib.Path(__file__).parent.parent / "config.yaml")


def test_load_config_returns_dict():
    cfg = load_config(CONFIG_PATH)
    assert isinstance(cfg, dict)
    assert "model" in cfg
    assert "paths" in cfg


def test_resolve_paths_makes_absolute():
    cfg = load_config(CONFIG_PATH)
    cfg = resolve_paths(cfg, CONFIG_PATH)
    for key, val in cfg["paths"].items():
        assert pathlib.Path(val).is_absolute(), f"Path '{key}' is not absolute: {val}"


def test_load_prompt_returns_string():
    cfg = resolve_paths(load_config(CONFIG_PATH), CONFIG_PATH)
    prompt = load_prompt(cfg["paths"]["prompt"])
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_build_context_valid_segment():
    cfg = resolve_paths(load_config(CONFIG_PATH), CONFIG_PATH)
    demand = pd.read_csv(cfg["paths"]["demand_data"])
    supply = pd.read_csv(cfg["paths"]["supply_data"])
    ctx = build_context(demand, supply, "west", "apartment", 2)
    assert "west" in ctx
    assert "demand" in ctx.lower()
    assert "supply" in ctx.lower()


def test_build_context_invalid_segment():
    cfg = resolve_paths(load_config(CONFIG_PATH), CONFIG_PATH)
    demand = pd.read_csv(cfg["paths"]["demand_data"])
    supply = pd.read_csv(cfg["paths"]["supply_data"])
    ctx = build_context(demand, supply, "west", "apartment", 99)
    assert "No data available" in ctx
