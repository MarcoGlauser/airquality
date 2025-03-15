import time


class Backoff:
    def __init__(self, initial_backoff=10, max_backoff=60, backoff_increment=10, counter_size=8):
        self.current_backoff = initial_backoff
        self.max_backoff = max_backoff
        self.backoff_increment = backoff_increment
        self.counter_size = counter_size
        self.counter = self.counter_size

    def backoff(self):
        if self.counter > 1:
            self.counter -= 1
            self._sleep()
        else:
            self._sleep()
            self.counter = self.counter_size
            self.current_backoff = min(self.current_backoff + self.backoff_increment, self.max_backoff)

    def _sleep(self):
        time.sleep(self.current_backoff)
