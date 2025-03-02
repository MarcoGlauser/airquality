from ltr559 import LTR559
from sensors.sensor import Sensor

ltr559 = LTR559()


class LTR559(Sensor):
    def __init__(self):
        ltr559.get_lux()

    def read_data(self):
        return {"illuminance": float(ltr559.get_lux())}

    def home_assistant_auto_discovery(self) -> [str, dict]:
        return [
            (
                f"{self.home_assistant_prefix()}illuminance/config",
                self._home_assistant_discovery_helper("illuminance", "lx"),
            )
        ]
