"""
Program specific Option states (description changes with a program as parentUID).

Replays messages of a Siemens HB774G1B1 oven: it describes Options inside single
programs, e.g. PyrolysisLevel as not available in a pizza favorite. Such states
apply only while that program is selected or active; favorites never restrict.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest
from homeconnect_websocket.entities import DeviceDescription

if TYPE_CHECKING:
    from homeconnect_websocket import HomeAppliance
    from homeconnect_websocket.testutils import MockApplianceType

LEVEL = 5122
PYROLYSIS_LEVEL = 5129
SETPOINT = 5120
DURATION = 548
PYROLYSIS = 9217
GOOSE_LEGS = 12305
SELECTED = 257
ACTIVE = 256
FAVORITES = [32828 + 5 * i for i in range(10)]  # Favorite.001 .. Favorite.010
FAVORITE_001, FAVORITE_002 = FAVORITES[0], FAVORITES[1]
OPTION_LIST = 262  # optionList node, not a program

OPTIONS = [LEVEL, PYROLYSIS_LEVEL, SETPOINT, DURATION]

DESCRIPTION = DeviceDescription(
    info={"brand": "SIEMENS", "type": "Oven", "vib": "HB774G1B1"},
    option=[
        {
            "uid": LEVEL,
            "name": "Cooking.Oven.Option.Level",
            "access": "readwrite",
            "available": True,
            "min": "1",
            "max": "3",
            "protocolType": "Integer",
            "enumeration": {"1": "Level01", "2": "Level02", "3": "Level03"},
        },
        {
            "uid": PYROLYSIS_LEVEL,
            "name": "Cooking.Oven.Option.PyrolysisLevel",
            "access": "readwrite",
            "available": True,
            "min": "1",
            "max": "2",
            "protocolType": "Integer",
            "enumeration": {"1": "Level01", "2": "Level02"},
        },
        {
            "uid": SETPOINT,
            "name": "Cooking.Oven.Option.SetpointTemperature",
            "access": "readwrite",
            "available": True,
            "min": "30",
            "max": "300",
            "protocolType": "Float",
        },
        {
            "uid": DURATION,
            "name": "BSH.Common.Option.Duration",
            "access": "readwrite",
            "available": True,
            "min": "1",
            "max": "266400",
            "protocolType": "Integer",
        },
    ],
    program=[
        {
            "uid": PYROLYSIS,
            "name": "Cooking.Oven.Program.Cleaning.Pyrolysis",
            "options": [{"refUID": DURATION}, {"refUID": PYROLYSIS_LEVEL}],
        },
        {
            "uid": GOOSE_LEGS,
            "name": "Cooking.Oven.Program.Dish.Automatic.Conv.GooseLegs",
            "options": [{"refUID": DURATION}],
        },
        *(
            {
                "uid": uid,
                "name": f"BSH.Common.Program.Favorite.{i + 1:03d}",
                "options": [{"refUID": option} for option in OPTIONS],
            }
            for i, uid in enumerate(FAVORITES)
        ),
    ],
    activeProgram={
        "uid": ACTIVE,
        "name": "BSH.Common.Root.ActiveProgram",
        "access": "readwrite",
    },
    selectedProgram={
        "uid": SELECTED,
        "name": "BSH.Common.Root.SelectedProgram",
        "access": "readwrite",
    },
)


def favorite_changes(favorite: int) -> list[dict]:
    """Return the changes the oven sends for a pizza favorite."""
    return [
        {"uid": PYROLYSIS_LEVEL, "parentUID": favorite, "available": False},
        {"uid": LEVEL, "parentUID": favorite, "available": False},
        {"uid": SETPOINT, "parentUID": favorite, "max": 275},
        {"uid": DURATION, "parentUID": favorite, "max": 86400},
    ]


def select(program: int) -> list[dict]:
    """Return the value update selecting program."""
    return [{"uid": SELECTED, "value": program}]


async def appliance_with_snapshot(
    mock_homeconnect_appliance: MockApplianceType, changes: list[dict]
) -> HomeAppliance:
    """Return an appliance after a snapshot with changes, nothing selected."""
    appliance = await mock_homeconnect_appliance(description=DESCRIPTION)
    await appliance._update_entities(changes, snapshot=True)
    await appliance._update_entities(
        [{"uid": ACTIVE, "value": 0}, {"uid": SELECTED, "value": 0}]
    )
    return appliance


def available(appliance: HomeAppliance, uid: int) -> bool | None:
    """Return the availability of the Option uid."""
    return appliance.entities_uid[uid].available


@pytest.mark.asyncio
async def test_favorite_state_in_snapshot_does_not_hide_options(
    mock_homeconnect_appliance: MockApplianceType,
) -> None:
    """Favorite 001 states in the snapshot, nothing selected: usable."""
    appliance = await appliance_with_snapshot(
        mock_homeconnect_appliance, favorite_changes(FAVORITE_001)
    )
    assert available(appliance, LEVEL) is True
    assert available(appliance, PYROLYSIS_LEVEL) is True
    assert appliance.entities_uid[SETPOINT].max == 300
    assert appliance.entities_uid[DURATION].max == 266400


@pytest.mark.asyncio
async def test_pyrolysis_after_favorite_snapshot_is_settable(
    mock_homeconnect_appliance: MockApplianceType,
) -> None:
    """Pyrolysis after the favorite snapshot: level available."""
    appliance = await appliance_with_snapshot(
        mock_homeconnect_appliance, favorite_changes(FAVORITE_001)
    )
    await appliance._update_entities(select(PYROLYSIS))
    await appliance._update_entities(
        [{"uid": DURATION, "parentUID": PYROLYSIS, "max": 86340}]
    )
    await appliance._update_entities([{"uid": PYROLYSIS_LEVEL, "value": 2}])
    assert available(appliance, PYROLYSIS_LEVEL) is True
    assert appliance.entities_uid[PYROLYSIS_LEVEL].value_raw == 2
    assert appliance.entities_uid[DURATION].max == 86340

    # Deselect: the oven reverts its Pyrolysis state
    await appliance._update_entities(
        [{"uid": DURATION, "parentUID": PYROLYSIS, "max": 266400}]
    )
    await appliance._update_entities(select(0))
    assert appliance.entities_uid[DURATION].max == 266400


@pytest.mark.asyncio
async def test_selected_favorite_keeps_options_available(
    mock_homeconnect_appliance: MockApplianceType,
) -> None:
    """A selected favorite keeps Level and PyrolysisLevel available."""
    appliance = await appliance_with_snapshot(mock_homeconnect_appliance, [])
    await appliance._update_entities(select(FAVORITE_001))
    await appliance._update_entities(favorite_changes(FAVORITE_001))
    assert available(appliance, LEVEL) is True
    assert available(appliance, PYROLYSIS_LEVEL) is True
    assert appliance.entities_uid[SETPOINT].max == 300

    await appliance._update_entities(select(GOOSE_LEGS))
    await appliance._update_entities(
        [{"uid": DURATION, "parentUID": GOOSE_LEGS, "max": 86340}]
    )
    assert available(appliance, LEVEL) is True
    assert available(appliance, PYROLYSIS_LEVEL) is True
    assert appliance.entities_uid[SETPOINT].max == 300
    assert appliance.entities_uid[DURATION].max == 86340

    # Favorite 002: own states, GooseLegs state reverted
    await appliance._update_entities(select(FAVORITE_002))
    await appliance._update_entities(
        [
            *favorite_changes(FAVORITE_002),
            {"uid": DURATION, "parentUID": GOOSE_LEGS, "max": 266400},
        ]
    )
    assert available(appliance, PYROLYSIS_LEVEL) is True
    assert appliance.entities_uid[DURATION].max == 266400


@pytest.mark.asyncio
async def test_reload_while_pyrolysis_selected_with_both_favorites_in_snapshot(
    mock_homeconnect_appliance: MockApplianceType,
) -> None:
    """Reload, Pyrolysis selected, snapshot with favorites 001/002."""
    appliance = await mock_homeconnect_appliance(description=DESCRIPTION)
    await appliance._update_entities(
        favorite_changes(FAVORITE_001) + favorite_changes(FAVORITE_002), snapshot=True
    )
    await appliance._update_entities(
        [
            {"uid": ACTIVE, "value": 0},
            *select(PYROLYSIS),
            {"uid": PYROLYSIS_LEVEL, "value": 2},
        ]
    )
    assert available(appliance, PYROLYSIS_LEVEL) is True
    assert appliance.entities_uid[PYROLYSIS_LEVEL].value_raw == 2


@pytest.mark.asyncio
async def test_new_snapshot_drops_program_states_not_listed_anymore(
    mock_homeconnect_appliance: MockApplianceType,
) -> None:
    """A new snapshot drops program states not listed anymore."""
    appliance = await appliance_with_snapshot(
        mock_homeconnect_appliance,
        [{"uid": DURATION, "parentUID": PYROLYSIS, "max": 86340}],
    )
    await appliance._update_entities(select(PYROLYSIS))
    assert appliance.entities_uid[DURATION].max == 86340

    await appliance._update_entities([], snapshot=True)
    assert appliance.entities_uid[DURATION].max == 266400


@pytest.mark.asyncio
async def test_init_treats_all_description_changes_as_snapshot(
    mock_homeconnect_appliance: MockApplianceType,
) -> None:
    """_init() replaces program states with the reconnect snapshot."""
    appliance = await appliance_with_snapshot(
        mock_homeconnect_appliance, favorite_changes(FAVORITE_001)
    )
    await appliance._update_entities(select(FAVORITE_001))
    appliance.session.send_sync = AsyncMock(
        side_effect=[
            SimpleNamespace(data=[]),
            SimpleNamespace(data=select(FAVORITE_001)),
        ]
    )
    await appliance._init()
    assert available(appliance, PYROLYSIS_LEVEL) is True


@pytest.mark.asyncio
@pytest.mark.parametrize("favorite", FAVORITES)
async def test_every_favorite_slot_never_restricts(
    mock_homeconnect_appliance: MockApplianceType, favorite: int
) -> None:
    """All 10 favorite slots, also unseen ones, all listed in one snapshot."""
    snapshot = [change for uid in FAVORITES for change in favorite_changes(uid)]
    appliance = await appliance_with_snapshot(mock_homeconnect_appliance, snapshot)
    assert available(appliance, PYROLYSIS_LEVEL) is True

    await appliance._update_entities(select(favorite))
    assert available(appliance, PYROLYSIS_LEVEL) is True
    assert available(appliance, LEVEL) is True
    assert appliance.entities_uid[SETPOINT].max == 300

    await appliance._update_entities(select(PYROLYSIS))
    assert available(appliance, PYROLYSIS_LEVEL) is True
    assert available(appliance, LEVEL) is True


@pytest.mark.asyncio
async def test_active_program_takes_precedence(
    mock_homeconnect_appliance: MockApplianceType,
) -> None:
    """The active program's states win over the selected program."""
    appliance = await appliance_with_snapshot(
        mock_homeconnect_appliance,
        [{"uid": DURATION, "parentUID": PYROLYSIS, "max": 86340}],
    )
    await appliance._update_entities(
        [{"uid": ACTIVE, "value": PYROLYSIS}, *select(GOOSE_LEGS)]
    )
    assert appliance.entities_uid[DURATION].max == 86340
    await appliance._update_entities([{"uid": ACTIVE, "value": 0}])
    assert appliance.entities_uid[DURATION].max == 266400


@pytest.mark.asyncio
async def test_non_program_parent_still_applies_to_the_option(
    mock_homeconnect_appliance: MockApplianceType,
) -> None:
    """A change under a structure node (optionList) or without parent stays global."""
    appliance = await appliance_with_snapshot(mock_homeconnect_appliance, [])
    await appliance._update_entities(
        [{"uid": PYROLYSIS_LEVEL, "parentUID": OPTION_LIST, "available": False}]
    )
    assert available(appliance, PYROLYSIS_LEVEL) is False
    await appliance._update_entities(select(PYROLYSIS))
    assert available(appliance, PYROLYSIS_LEVEL) is False
    await appliance._update_entities(
        [{"uid": PYROLYSIS_LEVEL, "available": True, "access": "READWRITE"}]
    )
    assert available(appliance, PYROLYSIS_LEVEL) is True


@pytest.mark.asyncio
async def test_program_parent_default_is_not_a_value(
    mock_homeconnect_appliance: MockApplianceType,
) -> None:
    """A dishwasher sends only 'default' under a favorite; the value is kept."""
    appliance = await appliance_with_snapshot(mock_homeconnect_appliance, [])
    await appliance._update_entities([{"uid": PYROLYSIS_LEVEL, "value": 1}])
    await appliance._update_entities(
        [{"uid": PYROLYSIS_LEVEL, "parentUID": FAVORITE_001, "default": 2}]
    )
    assert appliance.entities_uid[PYROLYSIS_LEVEL].value_raw == 1


@pytest.mark.asyncio
async def test_context_change_runs_option_callbacks(
    mock_homeconnect_appliance: MockApplianceType,
) -> None:
    """Integrations are told when an Option's availability changes with the program."""
    appliance = await appliance_with_snapshot(
        mock_homeconnect_appliance,
        [{"uid": DURATION, "parentUID": PYROLYSIS, "max": 86340}],
    )
    callback = AsyncMock()
    appliance.entities_uid[DURATION].register_callback(callback)
    await appliance._update_entities(select(PYROLYSIS))
    await appliance.callback_manager._task_manager.block_till_done()
    assert callback.await_count >= 1
