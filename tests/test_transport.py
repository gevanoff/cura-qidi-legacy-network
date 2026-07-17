from qidi_legacy.transport import UdpTransport


def test_udp_transport_connects_ephemeral_port_before_receive() -> None:
    with UdpTransport("127.0.0.1") as transport:
        local_host, local_port = transport.local_endpoint
        remote_host, remote_port = transport._socket.getpeername()

        assert local_host == "127.0.0.1"
        assert local_port > 0
        assert remote_host == "127.0.0.1"
        assert remote_port == 3000
        transport.discard_pending()
