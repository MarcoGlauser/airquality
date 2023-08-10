import os


class Sensor:
    def __init__(self):
        self._home_assistant_prefix = f"{os.getenv('MQTT_TOPIC_PREFIX', 'homeassistant')}/sensor/{type(self).__name__}"

    def read_data(self):
        raise NotImplementedError

    def home_assistant_state_topic(self) -> str:
        return f"{self._home_assistant_prefix}/state"

    def home_assistant_auto_discovery(self) -> [str, dict]:
        raise NotImplementedError

    def _home_assistant_discovery_helper(self, sensor_type: str, unit: str) -> dict:
        identifier = f"{type(self).__name__}_{sensor_type}"
        return {
            "device_class": sensor_type.lower(),
            "name": sensor_type.title(),
            "state_topic": self.home_assistant_state_topic(),
            "unit_of_measurement": unit,
            "value_template": f"{{ value_json.{sensor_type}}}",
            "unique_id": identifier,
            "device": {"identifiers": [identifier], "name": type(self).__name__},
        }
