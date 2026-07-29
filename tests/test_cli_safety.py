import pytest

from qidi_legacy.cli import build_parser, run
from qidi_legacy.exceptions import QidiUploadError


def test_upload_start_is_rejected_before_network_access() -> None:
    args = build_parser().parse_args(
        ["upload", "10.10.22.196", "example.gcode", "--start"]
    )

    with pytest.raises(QidiUploadError, match="automatic network print start is disabled"):
        run(args)
