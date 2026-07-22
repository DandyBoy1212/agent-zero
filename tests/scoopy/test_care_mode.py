"""Max mode policy.

The whole reason Scoopy may switch to the expensive model without asking is
that he cannot leave it on. If turn scope ever stopped clearing, the design
would quietly become "the agent decides to spend five times as much, forever",
which is the thing nobody agreed to. These tests exist to keep that honest.
"""
import pytest

from care_mode import MAX_PRESET, current_mode, engage, release


class _Context:
    """Stands in for AgentContext. Only get_data/set_data are involved."""

    def __init__(self):
        self._data = {}

    def get_data(self, key):
        return self._data.get(key)

    def set_data(self, key, value):
        self._data[key] = value


@pytest.fixture
def ctx():
    return _Context()


def test_starts_on_the_everyday_model(ctx):
    assert current_mode(ctx) == "everyday"


def test_engaging_selects_the_max_preset_by_name(ctx):
    engage(ctx, scope="turn", reason="refund amount")
    assert current_mode(ctx) == "max"
    # By name, not by a copied model id: a preset edited in the UI has to take
    # effect without a code change.
    assert ctx.get_data("chat_model_override") == {"preset_name": MAX_PRESET}


def test_scoopys_own_escalation_lasts_one_turn(ctx):
    engage(ctx, scope="turn", reason="hard sum")
    assert release(ctx, only_if_turn_scoped=True) is True
    assert current_mode(ctx) == "everyday", "turn scope must not survive the turn"


def test_a_persons_choice_survives_the_turn(ctx):
    engage(ctx, scope="thread", reason="Liam pinned it")
    assert release(ctx, only_if_turn_scoped=True) is False
    assert current_mode(ctx) == "max", "a pinned thread must not be un-pinned by a turn ending"


def test_a_person_pinning_outranks_scoopy_escalating_inside_it(ctx):
    """The wider scope wins, not the most recent one. Otherwise Scoopy calling
    think_harder inside a pinned thread would downgrade the pin to one turn and
    silently undo a deliberate choice at the end of it."""
    engage(ctx, scope="thread", reason="pinned")
    engage(ctx, scope="turn", reason="scoopy escalates too")
    release(ctx, only_if_turn_scoped=True)
    assert current_mode(ctx) == "max"


def test_turning_it_off_clears_a_turn_scoped_escalation_too(ctx):
    """Switching it off means stop spending. Honouring only half of that would
    be a strange reading."""
    engage(ctx, scope="turn", reason="x")
    assert release(ctx) is True
    assert current_mode(ctx) == "everyday"


def test_engage_reports_whether_it_actually_changed(ctx):
    assert engage(ctx, scope="turn") is True
    assert engage(ctx, scope="turn") is False, "already on; caller should not announce a change"


def test_release_on_everyday_is_a_no_op(ctx):
    assert release(ctx) is False


def test_scope_must_be_one_of_two_values(ctx):
    with pytest.raises(ValueError):
        engage(ctx, scope="forever")


def test_the_two_tiers_are_actually_different_models():
    """Stepping up has to step somewhere.

    If the everyday model and the Max Power preset ever name the same model,
    think_harder still reports "switched to the high end model", Scoopy still
    believes it, and nothing changes. A no-op that announces success is worse
    than an error, so it is pinned here.

    Also checks the preset still carries a model at all: care_mode resolves it
    by name, and _resolve_override returns None for anything it cannot resolve,
    which silently leaves you on the cheap model.
    """
    import pathlib

    import yaml

    root = pathlib.Path(__file__).resolve().parents[2] / "plugins" / "_model_config"
    config = yaml.safe_load((root / "default_config.yaml").read_text(encoding="utf-8"))
    presets = yaml.safe_load((root / "default_presets.yaml").read_text(encoding="utf-8"))

    everyday = config["chat_model"]["name"]
    match = [p for p in presets if p.get("name") == MAX_PRESET]
    assert match, f"preset {MAX_PRESET!r} is gone; max mode resolves to None and does nothing"

    stepped_up = match[0].get("chat", {}).get("name")
    assert stepped_up, f"preset {MAX_PRESET!r} names no chat model"
    assert stepped_up != everyday, (
        f"max mode steps from {everyday} to {stepped_up}, which is nowhere"
    )


def test_an_unrelated_override_is_not_read_as_max(ctx):
    """Someone using /config to pick a different preset for their own reasons
    is not in max mode, and must not be reported as though they were."""
    ctx.set_data("chat_model_override", {"preset_name": "Balance"})
    assert current_mode(ctx) == "everyday"
