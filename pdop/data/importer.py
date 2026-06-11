"""
Import module for PDOP application.
Handles loading 3D scenario configurations from workspace JSON files.
Pure data processing - no UI components.
"""

import os
from typing import List, Optional, Tuple
import logging

from data.import_scenario import load_scenario_from_json

_LOG = logging.getLogger(__name__)


def get_available_scenarios(workspace_dir: str = "workspace") -> Tuple[List[str], Optional[str]]:
    """
    Get list of available scenarios from the workspace directory.

    A scenario is any subdirectory of workspace_dir containing a scenario.json file.

    Args:
        workspace_dir: Directory containing scenario subdirectories

    Returns:
        Tuple of (scenario_list, error_message)
    """
    if not os.path.isdir(workspace_dir):
        return [], f"Workspace directory '{workspace_dir}' not found."

    scenarios = [
        name for name in os.listdir(workspace_dir)
        if os.path.isfile(os.path.join(workspace_dir, name, "scenario.json"))
    ]

    if not scenarios:
        return [], f"No scenario.json files found in '{workspace_dir}'."

    return sorted(scenarios), None


def import_scenario(scenario_name: str, workspace_dir: str = "workspace") -> Tuple[bool, str, Optional[object]]:
    """
    Create a new Scenario instance, populate it from workspace/<scenario_name>/scenario.json,
    and synthesize measurements for each tag against the scenario's tag_truth.

    Returns: (success: bool, message: str, scenario: Scenario|None)
    """
    from simulation.scenario import Scenario as ScenarioClass

    new_scenario = ScenarioClass(name=scenario_name)
    if not load_scenario_from_json(new_scenario, scenario_name, workspace_dir):
        return False, f"Failed to load scenario configuration for '{scenario_name}'", None

    if new_scenario.tag_truth is not None:
        for tag in new_scenario.get_tag_list():
            new_scenario.generate_measurements(tag, new_scenario.tag_truth)

    return True, f"Successfully imported scenario '{scenario_name}'.", new_scenario


def validate_scenario_for_import(scenario_obj) -> Tuple[bool, str]:
    """
    Validate that a scenario object is ready for import.
    """
    try:
        _ = scenario_obj.get_anchor_list()
        _ = scenario_obj.get_tag_list()
    except Exception:
        return False, "Scenario object does not implement required station accessors"

    return True, ""
