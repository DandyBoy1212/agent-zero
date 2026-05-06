"""Inject the scoopy plugin's helpers directory onto sys.path so tests can
import its modules without requiring the plugin to be a Python package
(Agent Zero plugins are discovered by `plugin.yaml`, not by `__init__.py`).
"""
import sys
import pathlib

_HELPERS = pathlib.Path(__file__).resolve().parents[2] / "plugins" / "scoopy" / "helpers"
if str(_HELPERS) not in sys.path:
    sys.path.insert(0, str(_HELPERS))
