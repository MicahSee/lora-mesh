import pytest
from dummy_network import DummyRadio, LoopbackNetwork

@pytest.fixture
def loopback_network():
    return LoopbackNetwork()

@pytest.fixture
def radio1(loopback_network):
    return DummyRadio(loopback_network)

@pytest.fixture
def radio2(loopback_network):
    return DummyRadio(loopback_network)

def test_radio1_to_radio2(radio1, radio2):
    test_data = b"Hello from radio1"

    # radio1 sends
    radio1.send(test_data)

    # radio2 receives
    received_data = radio2.receive()

    assert received_data == test_data, "Radio2 did not receive correct data"

    # radio1 should not receive its own message
    assert radio1.receive() is None, "Radio1 should not receive its own message"

def test_bidirectional(radio1, radio2):
    msg1 = b"Message 1"
    msg2 = b"Message 2"

    radio1.send(msg1)
    radio2.send(msg2)

    # Each radio receives the other's message
    assert radio2.receive() == msg1
    assert radio1.receive() == msg2
