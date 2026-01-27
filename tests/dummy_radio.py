from secure_lora.radio import RadioInterface

import sys
import time
import msvcrt
from multiprocessing.managers import BaseManager

class NetworkManager(BaseManager):
    pass

# Register the name so the manager knows what to look for
NetworkManager.register('get_network')

class DummyRadio:
    def __init__(self, node_id):
        self.node_id = node_id
        self.manager = NetworkManager(address=('127.0.0.1', 5000), authkey=b'radio_secret')
        self.manager.connect()
        self.network = self.manager.get_network()
        
        # Register ourselves
        self.network.register_node(self.node_id)
        
        self.last_seen_id = -1
        self.incoming_buffer = []

    def send(self, data: bytes):
        self.network.send(self.node_id, data)

    def receive(self) -> bytes | None:
        new_messages = self.network.get_updates(self.node_id, self.last_seen_id)
        for msg in new_messages:
            self.incoming_buffer.append(msg['data'])
            self.last_seen_id = max(self.last_seen_id, msg['id'])

        if self.incoming_buffer:
            return self.incoming_buffer.pop(0)
        return None
    
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python dummy_radio.py <node_id>")
        sys.exit(1)

    node_id = sys.argv[1]
    radio = DummyRadio(node_id)

    print(f"DummyRadio {node_id} is running. Type messages to send.")

    try:
        while True:
            prompt = "Enter message to send: "
            print(prompt, end='', flush=True)

            current_input = ""

            while True:
                # Check for incoming messages
                incoming = radio.receive()
                if incoming:
                    # Clear current line
                    print('\r' + ' ' * (len(prompt) + len(current_input)) + '\r', end='', flush=True)

                    # Display received message
                    print(f"[Received]: {incoming.decode('utf-8')}")

                    # Redisplay prompt and current input
                    print(prompt + current_input, end='', flush=True)

                # Check for keyboard input
                if msvcrt.kbhit():
                    char = msvcrt.getwch()

                    if char == '\r':  # Enter key
                        print()  # New line
                        if current_input:
                            radio.send(current_input.encode('utf-8'))
                            print(f"[Sent]: {current_input}")
                        break
                    elif char == '\b':  # Backspace
                        if current_input:
                            current_input = current_input[:-1]
                            print('\b \b', end='', flush=True)
                    elif char == '\x03':  # Ctrl+C
                        raise KeyboardInterrupt
                    elif char in ('\x00', '\xe0'):  # Special keys (arrows, etc.)
                        msvcrt.getwch()  # Consume the second byte
                    else:
                        current_input += char
                        print(char, end='', flush=True)

                time.sleep(0.01)  # Small delay to avoid busy waiting

    except KeyboardInterrupt:
        print("\nExiting DummyRadio.")