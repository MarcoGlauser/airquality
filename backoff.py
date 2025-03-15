import time
from dataclasses import dataclass


@dataclass
class Backoff:

    initial_backoff: int = 10
    backoff_increment: int = 10
    max_backoff: int = 60
    counter_size:int = 8

    _current_backoff: int = 0
    _counter: int = 0

    def __post_init__(self):
        self._counter = self.counter_size
        self._current_backoff = self.initial_backoff

    def backoff(self):
        if self._counter > 1:
            self._counter -= 1
            self._sleep()
        else:
            self._sleep()
            self._counter = self.counter_size
            self._current_backoff = min(self._current_backoff + self.backoff_increment, self.max_backoff)

    def _sleep(self):
        print(f"Sleeping for {self._current_backoff} seconds")
        time.sleep(self._current_backoff)
