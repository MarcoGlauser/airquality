import plantower
from plantower import Plantower

from sensors.sensor import Sensor


class PMS7003(Sensor):
    def __init__(self):
        self.sensor = Plantower("/dev/ttyAMA0")
        self.sensor.mode_change(plantower.PMS_ACTIVE_MODE)

    def read_data(self):
        data = self.sensor.read()
        print({"pm1_0": data.pm10_std, "pm2_5": data.pm25_std, "pm10": data.pm100_std})
        return {"pm1_0": data.pm10_std, "pm2_5": data.pm25_std, "pm10": data.pm100_std}

    def home_assistant_auto_discovery(self) -> [str, dict]:
        return [
            (
                f"{self.home_assistant_prefix()}pm1_0/config",
                self._home_assistant_discovery_helper("pm1_0", "ug/m3"),
            ),
            (
                f"{self.home_assistant_prefix()}pm2_5/config",
                self._home_assistant_discovery_helper("pm2_5", "ug/m3"),
            ),
            (
                f"{self.home_assistant_prefix()}pm10/config",
                self._home_assistant_discovery_helper("pm10", "ug/m3"),
            ),
        ]
