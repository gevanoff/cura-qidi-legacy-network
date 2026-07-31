import pytest

from cura_plugin.QidiLegacyNetwork.communication_state import QidiCommunicationState


def test_active_state_allows_monitoring_and_upload() -> None:
    state = QidiCommunicationState()

    assert state.polling_allowed is True
    assert state.cura_upload_allowed is True
    assert state.state_text == "Active"


def test_upload_suspends_polling_until_finished() -> None:
    state = QidiCommunicationState()

    state.begin_upload()

    assert state.upload_active is True
    assert state.polling_allowed is False
    assert state.cura_upload_allowed is False
    assert state.state_text == "Upload has exclusive access"
    assert "all other Cura communication are paused" in state.notice_text

    state.finish_upload()

    assert state.upload_active is False
    assert state.polling_allowed is True


def test_manual_pause_blocks_cura_uploads_until_resumed() -> None:
    state = QidiCommunicationState()
    state.pause_for_external_access()

    assert state.manual_pause is True
    assert state.polling_allowed is False
    assert state.cura_upload_allowed is False
    assert state.state_text == "Paused for external access"

    with pytest.raises(RuntimeError, match="paused for an external client"):
        state.begin_upload()

    state.resume_after_external_access()
    state.begin_upload()
    assert state.upload_active is True


def test_manual_pause_requested_during_upload_persists_after_upload() -> None:
    state = QidiCommunicationState()
    state.begin_upload()
    state.pause_for_external_access()

    assert state.state_text == "Upload has exclusive access"

    state.finish_upload()

    assert state.manual_pause is True
    assert state.polling_allowed is False
    assert state.state_text == "Paused for external access"


def test_second_upload_cannot_start_concurrently() -> None:
    state = QidiCommunicationState()
    state.begin_upload()

    with pytest.raises(RuntimeError, match="already has exclusive"):
        state.begin_upload()
