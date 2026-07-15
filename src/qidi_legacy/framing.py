from __future__ import annotations

BLOCK_PAYLOAD_SIZE = 1280
BLOCK_TRAILER_SIZE = 6
BLOCK_MARKER = 0x83


def frame_file_block(payload: bytes, offset: int) -> bytes:
    """Frame one legacy QIDI upload block.

    Layout: payload + uint32 little-endian offset + XOR checksum + 0x83 marker.
    """
    if not payload:
        raise ValueError("payload must not be empty")
    if len(payload) > BLOCK_PAYLOAD_SIZE:
        raise ValueError(f"payload exceeds {BLOCK_PAYLOAD_SIZE} bytes")
    if not 0 <= offset <= 0xFFFFFFFF:
        raise ValueError("offset must fit in uint32")

    body = payload + offset.to_bytes(4, byteorder="little", signed=False)
    checksum = 0
    for value in body:
        checksum ^= value
    return body + bytes((checksum, BLOCK_MARKER))


def parse_file_block(datagram: bytes) -> tuple[bytes, int]:
    """Validate and decode a legacy QIDI upload block."""
    if len(datagram) <= BLOCK_TRAILER_SIZE:
        raise ValueError("datagram is too short")
    if datagram[-1] != BLOCK_MARKER:
        raise ValueError("invalid block marker")

    body = datagram[:-2]
    expected_checksum = datagram[-2]
    checksum = 0
    for value in body:
        checksum ^= value
    if checksum != expected_checksum:
        raise ValueError("invalid block checksum")

    payload = body[:-4]
    offset = int.from_bytes(body[-4:], byteorder="little", signed=False)
    return payload, offset
