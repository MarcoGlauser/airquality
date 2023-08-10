from enviroplus import gas

from sensors.sensor import Sensor


class MICS6814(Sensor):
    def read_data(self):
        data = gas.read_all()
        return {"oxidising": data.oxidising, "reducing": data.reducing, "nh3": data.nh3}

    def home_assistant_auto_discovery(self) -> [str, dict]:
        return [
            (
                f"{self.home_assistant_prefix()}oxidising/config",
                self._home_assistant_discovery_helper("oxidising", "kOhm"),
            ),
            (
                f"{self.home_assistant_prefix()}reducing/config",
                self._home_assistant_discovery_helper("reducing", "kOhm"),
            ),
            (
                f"{self.home_assistant_prefix()}nh3/config",
                self._home_assistant_discovery_helper("nh3", "kOhm"),
            ),
        ]
