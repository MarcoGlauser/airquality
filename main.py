import json
import os
import sys
from datetime import datetime

from serial import SerialException

from backoff import Backoff
from mqtt import setup_mqtt
from sensors.bme280_sensor import BME280
from sensors.ltr559 import LTR559
from sensors.pms7003 import PMS7003
from sensors.s8 import S8

sensors = [
    BME280(),
    LTR559(),
    S8(),
    PMS7003(),
]

sensor_backoff = Backoff(initial_backoff=60, max_backoff=180, backoff_increment=60)
LTR559().read_data()
PMS7003().read_data()


def loop():
    mqtt_client = setup_mqtt()
    mqtt_client.loop_start()
    try:
        while True:
            for sensor in sensors:
                try:
                    mqtt_client.publish(
                        f"{os.getenv('MQTT_TOPIC_PREFIX', 'homeassistant')}/{type(sensor).__name__}",
                        payload=json.dumps(sensor.read_data()),
                        retain=True,
                    )
                    print(f"[{datetime.utcnow()}] - reading {type(sensor).__name__}")

                except SerialException as e:
                    print(e)
                    print(
                        f"[{datetime.utcnow()}] - Failed reading {type(sensor).__name__}. SKIPPED!"
                    )
            print("backoff")
            sensor_backoff.backoff()
            print("")
    except KeyboardInterrupt:
        sys.exit(0)
    finally:
        mqtt_client.loop_stop()


if __name__ == "__main__":
    loop()
