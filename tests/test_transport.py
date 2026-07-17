from qidi_legacy.transport import UdpTransport


def test_udp_transport_binds_ephemeral_port_before_receive() -> None:
    with UdpTransport("127.0.0.1") as transport:
        local_host, local_port = transport._socket.getsockname()

        assert local_host in {"0.0.0.0", "127.0.0.1"}
        assert local_port > 0
        transport.discard_pending()
