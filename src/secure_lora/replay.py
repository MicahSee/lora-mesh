class ReplayProtection:
    def __init__(self):
        self.last_counter = {}

    def check_and_update(self, sender_id: int, counter: int) -> bool:
        last = self.last_counter.get(sender_id, -1)

        if counter <= last:
            return False

        self.last_counter[sender_id] = counter
        return True
