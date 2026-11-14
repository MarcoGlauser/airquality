import os

import paho.mqtt.client as mqtt

from sensors.sensor import APP_AVAILABILITY_TOPIC


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("connected OK")
        client.publish(APP_AVAILABILITY_TOPIC, "online", retain=True)
        # (re)subscribe on every connect so commands keep working after a reconnect
        for topic in userdata["command_handlers"]:
            client.subscribe(topic)
    else:
        print("Bad connection Returned code=", rc)


def on_publish(client, userdata, mid):
    print("mid: " + str(mid))


def get_serial_number():
    with open("/proc/cpuinfo", "r") as f:
        for line in f:
            if line[0:6] == "Serial":
                return line.split(":")[1].strip()


def setup_mqtt(command_handlers: dict | None = None) -> mqtt.Client:
    command_handlers = command_handlers or {}
    device_serial_number = get_serial_number()
    device_id = "raspi-" + device_serial_number
    mqtt_client = mqtt.Client(
        client_id=device_id, userdata={"command_handlers": command_handlers}
    )
    # broker marks the whole app offline if we drop off without saying goodbye
    mqtt_client.will_set(APP_AVAILABILITY_TOPIC, "offline", retain=True)
    for topic, handler in command_handlers.items():
        mqtt_client.message_callback_add(topic, handler)

    mqtt_client.on_connect = on_connect
    mqtt_client.on_publish = on_publish

    mqtt_client.connect(
        os.getenv("MQTT_BROKER", "mosquitto"), port=int(os.getenv("MQTT_PORT", "1883"))
    )

    return mqtt_client
