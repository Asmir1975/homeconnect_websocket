from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest
from homeconnect_websocket.entities import DeviceDescription, EntityDescription
from homeconnect_websocket.errors import DisconnectedError
from homeconnect_websocket.session import ConnectionState

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


NO_PROGRAM_ROOT_DESCRIPTION = DeviceDescription(
    program=[
        EntityDescription(uid=500, name="Test.Program1"),
    ],
)


@pytest.mark.asyncio
async def test_active_program_without_root_returns_none(
    mock_homeconnect_appliance: MockApplianceType,
) -> None:
    """Test active_program returns None when the appliance has no root entity."""
    appliance = await mock_homeconnect_appliance(
        description=NO_PROGRAM_ROOT_DESCRIPTION
    )

    assert appliance.active_program is None


@pytest.mark.asyncio
async def test_selected_program_without_root_returns_none(
    mock_homeconnect_appliance: MockApplianceType,
) -> None:
    """Test selected_program returns None when the appliance has no root entity."""
    appliance = await mock_homeconnect_appliance(
        description=NO_PROGRAM_ROOT_DESCRIPTION
    )

    assert appliance.selected_program is None


@pytest.mark.asyncio
async def test_init_disconnected_during_send_sync_is_not_logged_as_error(
    mock_homeconnect_appliance: MockApplianceType,
) -> None:
    """An expected disconnect while _init() is waiting must not log an error."""
    appliance = await mock_homeconnect_appliance(description=DESCRIPTION)
    appliance.session.send_sync.side_effect = DisconnectedError

    await appliance._init()

    appliance._logger.exception.assert_not_called()
    appliance._logger.debug.assert_called_once()


@pytest.mark.asyncio
async def test_init_real_timeout_is_still_logged_as_error(
    mock_homeconnect_appliance: MockApplianceType,
) -> None:
    """A genuine init failure on a still-connected session stays visible."""
    appliance = await mock_homeconnect_appliance(description=DESCRIPTION)
    appliance.session.send_sync.side_effect = TimeoutError

    await appliance._init()

    appliance._logger.exception.assert_called_once()


@pytest.mark.asyncio
async def test_init_retries_once_after_timeout(
    mock_homeconnect_appliance: MockApplianceType,
) -> None:
    """A timed out init request is sent once more on a still-connected session."""
    appliance = await mock_homeconnect_appliance(description=DESCRIPTION)
    appliance.session.send_sync.side_effect = [
        TimeoutError,
        SimpleNamespace(data=[]),
        SimpleNamespace(data=[]),
    ]

    await appliance._init()

    assert appliance.session.send_sync.await_count == 3
    appliance._logger.exception.assert_not_called()


@pytest.mark.asyncio
async def test_connection_callback_skips_stale_connected_after_aborted_init(
    mock_homeconnect_appliance: MockApplianceType,
) -> None:
    """A CONNECTED event must not reach the callback if close() won the race."""
    appliance = await mock_homeconnect_appliance(description=DESCRIPTION)
    appliance.session.send_sync.side_effect = DisconnectedError
    appliance.session.connected = False
    ext_callback = AsyncMock()
    appliance._ext_connection_state_callback = ext_callback

    await appliance._connection_callback(ConnectionState.CONNECTED)

    ext_callback.assert_not_called()


@pytest.mark.asyncio
async def test_connection_callback_forwards_connected_when_session_still_connected(
    mock_homeconnect_appliance: MockApplianceType,
) -> None:
    """A successful init still forwards CONNECTED to the external callback."""
    appliance = await mock_homeconnect_appliance(description=DESCRIPTION)
    appliance.session.send_sync.return_value.data = []
    appliance.session.connected = True
    ext_callback = AsyncMock()
    appliance._ext_connection_state_callback = ext_callback

    await appliance._connection_callback(ConnectionState.CONNECTED)

    ext_callback.assert_called_once_with(ConnectionState.CONNECTED)
