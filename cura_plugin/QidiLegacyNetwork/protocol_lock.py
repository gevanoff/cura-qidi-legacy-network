from threading import Lock

# The legacy printer protocol has no request IDs and returns plain, unsequenced UDP
# acknowledgements. Serialize all plugin traffic so status polling cannot interleave with a
# sustained file upload on another socket.
QIDI_PROTOCOL_LOCK = Lock()
