from __future__ import annotations


class QidiCommunicationState:
    """Track when Cura must remain silent on the legacy QIDI UDP interface.

    The printer cannot safely process status polling or other commands while a file upload is
    active. A manual pause also lets the user grant exclusive access to QIDI Print, the CLI, or
    another external client. This class contains no Qt dependencies so its transition rules can
    be tested directly.
    """

    def __init__(self) -> None:
        self._manual_pause = False
        self._upload_active = False

    @property
    def manual_pause(self) -> bool:
        return self._manual_pause

    @property
    def upload_active(self) -> bool:
        return self._upload_active

    @property
    def polling_allowed(self) -> bool:
        return not self._manual_pause and not self._upload_active

    @property
    def cura_upload_allowed(self) -> bool:
        return not self._manual_pause and not self._upload_active

    @property
    def state_text(self) -> str:
        if self._upload_active:
            return "Upload has exclusive access"
        if self._manual_pause:
            return "Paused for external access"
        return "Active"

    @property
    def notice_text(self) -> str:
        if self._upload_active:
            return (
                "Monitoring and all other Cura communication are paused until the upload "
                "finishes. Do not use QIDI Print, qidi-legacy, or another client concurrently."
            )
        if self._manual_pause:
            return (
                "Cura communication is paused. Wait for any in-flight status request to finish "
                "before using QIDI Print, qidi-legacy, or another external client."
            )
        return (
            "The legacy QIDI interface requires exclusive access. Pause Cura communication "
            "before using QIDI Print, qidi-legacy, or another client."
        )

    def pause_for_external_access(self) -> None:
        self._manual_pause = True

    def resume_after_external_access(self) -> None:
        self._manual_pause = False

    def begin_upload(self) -> None:
        if self._manual_pause:
            raise RuntimeError(
                "Cura QIDI communication is paused for an external client. Resume communication "
                "before starting a Cura upload."
            )
        if self._upload_active:
            raise RuntimeError("A QIDI upload already has exclusive communication access.")
        self._upload_active = True

    def finish_upload(self) -> None:
        self._upload_active = False
