import pytest

from qidi_legacy.framing import BLOCK_PAYLOAD_SIZE, frame_file_block, parse_file_block


def test_block_round_trip() -> None:
    payload = bytes(range(256)) * 5
    framed = frame_file_block(payload, 0x12345678)
    decoded, offset = parse_file_block(framed)
    assert decoded == payload
    assert offset == 0x12345678
    assert framed[-1] == 0x83
    assert framed[-6:-2] == b"xV4\x12"


def test_checksum_rejects_corruption() -> None:
    framed = bytearray(frame_file_block(b"G1 X10", 0))
    framed[0] ^= 1
    with pytest.raises(ValueError, match="checksum"):
        parse_file_block(bytes(framed))


def test_payload_limit() -> None:
    with pytest.raises(ValueError, match="exceeds"):
        frame_file_block(b"x" * (BLOCK_PAYLOAD_SIZE + 1), 0)
