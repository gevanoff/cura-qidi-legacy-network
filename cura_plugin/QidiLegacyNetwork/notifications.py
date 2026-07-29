from __future__ import annotations

import logging
import sys

_LOGGER = logging.getLogger(__name__)


def _play_windows_sound(*, success: bool) -> bool:
    if sys.platform != "win32":
        return False

    try:
        import winsound

        alias = "SystemAsterisk" if success else "SystemHand"
        try:
            winsound.PlaySound(
                alias,
                winsound.SND_ALIAS | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
            )
        except RuntimeError:
            fallback = winsound.MB_ICONASTERISK if success else winsound.MB_ICONHAND
            winsound.MessageBeep(fallback)
        return True
    except Exception as exc:
        _LOGGER.debug("Windows notification sound was unavailable: %s", exc)
        return False


def _play_qt_fallback() -> None:
    try:
        from PyQt6.QtWidgets import QApplication

        QApplication.beep()
    except Exception as exc:
        _LOGGER.debug("Qt notification sound was unavailable: %s", exc)


def _request_failure_attention() -> None:
    try:
        from PyQt6.QtGui import QGuiApplication

        application = QGuiApplication.instance()
        if application is None:
            return

        window = application.focusWindow()
        if window is None:
            window = next(
                (candidate for candidate in application.topLevelWindows() if candidate.isVisible()),
                None,
            )
        if window is not None:
            application.alert(window, 0)
    except Exception as exc:
        _LOGGER.debug("Taskbar attention request was unavailable: %s", exc)


def notify_upload_result(*, success: bool) -> None:
    """Play a distinct native completion sound and draw attention to failures.

    Windows uses the user's configured Information/Asterisk sound for success and
    Critical Stop/Hand sound for failure. Other platforms fall back to Qt's normal
    application beep. Failures also request persistent taskbar/dock attention.
    """

    if not _play_windows_sound(success=success):
        _play_qt_fallback()
    if not success:
        _request_failure_attention()
