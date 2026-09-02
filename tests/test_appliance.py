from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from homeconnect_websocket.entities import DeviceDescription, EntityDescription

if TYPE_CHECKING:
    from homeconnect_websocket.testutils import MockApplianceType

DESCRIPTION = DeviceDescription(
    program=[
        EntityDescription(uid=500, name="Test.Program1"),
    ],
    activeProgram=EntityDescription(uid=700, name="Test.ActiveProgram"),
    selectedProgram=EntityDescription(uid=600, name="Test.SelectedProgram"),
)


@pytest.mark.asyncio
async def test_active_program_unknown_uid_returns_none(
    mock_homeconnect_appliance: MockApplianceType,
) -> None:
    """Test active_program returns None instead of raising for an unknown UID."""
    appliance = await mock_homeconnect_appliance(description=DESCRIPTION)
    await appliance.entities["Test.ActiveProgram"].update({"value": 8213})

    assert appliance.active_program is None
    appliance._logger.debug.assert_called_once_with(
        "Active program UID %s not found in device description", 8213
    )


@pytest.mark.asyncio
async def test_active_program_known_uid(
    mock_homeconnect_appliance: MockApplianceType,
) -> None:
    """Test active_program still resolves a known UID."""
    appliance = await mock_homeconnect_appliance(description=DESCRIPTION)
    await appliance.entities["Test.ActiveProgram"].update({"value": 500})

    assert appliance.active_program is appliance.entities_uid[500]


@pytest.mark.asyncio
async def test_selected_program_unknown_uid_returns_none(
    mock_homeconnect_appliance: MockApplianceType,
) -> None:
    """Test selected_program returns None instead of raising for an unknown UID."""
    appliance = await mock_homeconnect_appliance(description=DESCRIPTION)
    await appliance.entities["Test.SelectedProgram"].update({"value": 8213})

    assert appliance.selected_program is None
    appliance._logger.debug.assert_called_once_with(
        "Selected program UID %s not found in device description", 8213
    )


@pytest.mark.asyncio
async def test_selected_program_known_uid(
    mock_homeconnect_appliance: MockApplianceType,
) -> None:
    """Test selected_program still resolves a known UID."""
    appliance = await mock_homeconnect_appliance(description=DESCRIPTION)
    await appliance.entities["Test.SelectedProgram"].update({"value": 500})

    assert appliance.selected_program is appliance.entities_uid[500]
