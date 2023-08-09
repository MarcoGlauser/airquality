import os

import paho.mqtt.client as mqtt


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("connected OK")
    else:
        print("Bad connection Returned code=", rc)


def on_publish(client, userdata, mid):
    print("mid: " + str(mid))


def get_serial_number():
    with open("/proc/cpuinfo", "r") as f:
        for line in f:
            if line[0:6] == "Serial":
                return line.split(":")[1].strip()


def setup_mqtt() -> mqtt.Client:
    device_serial_number = get_serial_number()
    device_id = "raspi-" + device_serial_number
    mqtt_client = mqtt.Client(client_id=device_id)

    mqtt_client.on_connect = on_connect
    mqtt_client.on_publish = on_publish

    mqtt_client.connect(
        os.getenv("MQTT_BROKER", "mosquitto"), port=int(os.getenv("MQTT_PORT", "1883"))
    )

    return mqtt_client
