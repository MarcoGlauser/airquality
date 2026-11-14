"""End-to-end test of the built Docker image with emulated sensors.

Starts Mosquitto and the app image (arm64 by default, via QEMU), with the S8 and
PMS7003 on emulated serial ports and the BME280 / LTR559 on a fake I2C bus
(see harness/). Everything is checked through what lands on MQTT, like Home
Assistant would see it.

    AIRQUALITY_IMAGE=airquality:test uv run pytest tests/e2e -v
"""

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

IMAGE = os.environ.get("AIRQUALITY_IMAGE", "airquality:test")
PLATFORM = os.environ.get("AIRQUALITY_PLATFORM", "linux/arm64")
MOSQUITTO_IMAGE = "eclipse-mosquitto:2.0.20"
HARNESS = Path(__file__).parent / "harness"
PREFIX = "homeassistant"

SENSORS = ["BME280", "LTR559", "S8", "PMS7003"]
DISCOVERY = {
    f"{PREFIX}/sensor/BME280temperature/config",
    f"{PREFIX}/sensor/BME280humidity/config",
    f"{PREFIX}/sensor/BME280pressure/config",
    f"{PREFIX}/sensor/LTR559illuminance/config",
    f"{PREFIX}/sensor/S8carbon_dioxide/config",
    f"{PREFIX}/sensor/PMS7003pm1/config",
    f"{PREFIX}/sensor/PMS7003pm25/config",
    f"{PREFIX}/sensor/PMS7003pm10/config",
    f"{PREFIX}/button/S8/calibrate/config",
}
APP_AVAILABILITY = f"{PREFIX}/airquality/availability"

# generous: the app reads every ~10s and runs under QEMU in CI
TIMEOUT = 90


def docker(*args, check=True):
    result = subprocess.run(["docker", *args], capture_output=True, text=True)
    if check and result.returncode != 0:
        raise RuntimeError(f"docker {' '.join(args)} failed: {result.stderr}")
    return result.stdout


class Stack:
    def __init__(self, name, state_dir):
        self.name = name
        self.mqtt = f"{name}-mqtt"
        self.app = f"{name}-app"
        self.state_dir = state_dir

    def retained(self) -> dict:
        """Snapshot of all retained messages: everything the app publishes is retained."""
        out = docker("exec", self.mqtt, "mosquitto_sub", "-t", "#", "-v", "-W", "1", check=False)
        messages = {}
        for line in out.splitlines():
            topic, _, payload = line.partition(" ")
            messages[topic] = payload
        return messages

    def wait_for(self, description, predicate, timeout=TIMEOUT):
        deadline = time.monotonic() + timeout
        last = None
        while time.monotonic() < deadline:
            last = self.retained()
            try:
                if predicate(last):
                    return last
            except (KeyError, ValueError):
                pass
            time.sleep(1)
        raise AssertionError(f"timed out waiting for {description}; last retained: {json.dumps(last, indent=1)}")

    def state(self, messages, sensor):
        return json.loads(messages[f"{PREFIX}/sensor/{sensor}/state"])

    def set_control(self, **values):
        path = self.state_dir / "control.json"
        current = json.loads(path.read_text())
        current.update(values)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(current))
        tmp.replace(path)  # atomic, so the emulator never reads half a file

    def events(self):
        path = self.state_dir / "events.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

    def wait_for_event(self, description, predicate, timeout=TIMEOUT):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if any(predicate(e) for e in self.events()):
                return
            time.sleep(1)
        raise AssertionError(f"timed out waiting for emulator event: {description}")

    def logs(self):
        result = subprocess.run(["docker", "logs", self.app], capture_output=True, text=True)
        return result.stdout + result.stderr


@pytest.fixture(scope="module")
def stack(tmp_path_factory):
    name = f"aq-e2e-{os.getpid()}"
    state_dir = tmp_path_factory.mktemp("harness-state")
    state_dir.chmod(0o777)
    (state_dir / "control.json").write_text(json.dumps({"co2": 600, "pms": True}))
    s = Stack(name, state_dir)

    docker("network", "create", name)
    try:
        docker("run", "-d", "--name", s.mqtt, "--network", name,
               MOSQUITTO_IMAGE, "mosquitto", "-c", "/mosquitto-no-auth.conf")
        docker("run", "-d", "--name", s.app, "--network", name, "--platform", PLATFORM,
               "-e", f"MQTT_BROKER={s.mqtt}", "-e", "PYTHONUNBUFFERED=1",
               "-e", "PYTHONPATH=/harness/fakes",
               "-v", f"{HARNESS}:/harness:ro", "-v", f"{state_dir}:/harness-state",
               IMAGE, "python", "/harness/entrypoint.py")
        yield s
    finally:
        print(f"\n----- app logs -----\n{s.logs()}")
        docker("rm", "-f", s.app, s.mqtt, check=False)
        docker("network", "rm", name, check=False)


def test_publishes_discovery_with_availability(stack):
    messages = stack.wait_for("all discovery configs", lambda m: DISCOVERY <= m.keys())
    for topic in DISCOVERY:
        config = json.loads(messages[topic])
        assert config["availability_mode"] == "all", topic
        assert {a["topic"] for a in config["availability"]} >= {APP_AVAILABILITY}, topic


def test_publishes_sensor_values(stack):
    def all_states(m):
        return all(f"{PREFIX}/sensor/{s}/state" in m for s in SENSORS)

    messages = stack.wait_for("a state from every sensor", all_states)
    bme = stack.state(messages, "BME280")
    assert bme["temperature"] == pytest.approx(25.08, abs=0.01)
    assert bme["pressure"] == pytest.approx(1006.53, abs=0.01)
    assert 0 < bme["humidity"] < 100
    assert stack.state(messages, "LTR559")["illuminance"] == pytest.approx(997.74, abs=0.01)
    assert stack.state(messages, "S8") == {"carbon_dioxide": 600}
    assert stack.state(messages, "PMS7003") == {"pm1": 5, "pm25": 12, "pm10": 20}


def test_everything_available(stack):
    stack.wait_for("app and all sensors online", lambda m: m[APP_AVAILABILITY] == "online" and all(
        m[f"{PREFIX}/sensor/{s}/availability"] == "online" for s in SENSORS))


def test_s8_abc_period_is_checked_but_not_rewritten(stack):
    stack.wait_for_event("ABC period read", lambda e: e["event"] == "read_holding" and e["register"] == 0x1F)
    assert not [e for e in stack.events() if e["event"] == "write_holding" and e["register"] == 0x1F]


def test_negative_co2_is_published_not_hidden(stack):
    stack.set_control(co2=-536)  # what a drifted baseline reports (0xFDE8, used to show as 65000)
    try:
        stack.wait_for("negative CO2 published", lambda m: stack.state(m, "S8")["carbon_dioxide"] == -536)
        assert stack.retained()[f"{PREFIX}/sensor/S8/availability"] == "online"
    finally:
        stack.set_control(co2=600)
    stack.wait_for("CO2 back to normal", lambda m: stack.state(m, "S8")["carbon_dioxide"] == 600)


def test_calibrate_button_runs_background_calibration(stack):
    docker("exec", stack.mqtt, "mosquitto_pub", "-t", f"{PREFIX}/sensor/S8/calibrate", "-m", "PRESS")
    stack.wait_for_event("background calibration", lambda e: e["event"] == "background_calibration")
    deadline = time.monotonic() + 30
    while "calibration finished" not in stack.logs():
        assert time.monotonic() < deadline, "app never confirmed the calibration"
        time.sleep(1)
    assert "not acknowledged" not in stack.logs()


def test_failing_sensor_goes_unavailable_and_recovers(stack):
    topic = f"{PREFIX}/sensor/PMS7003/availability"
    stack.set_control(pms=False)
    try:
        stack.wait_for("PMS7003 offline", lambda m: m[topic] == "offline")
        assert stack.retained()[f"{PREFIX}/sensor/S8/availability"] == "online"
    finally:
        stack.set_control(pms=True)
    stack.wait_for("PMS7003 back online", lambda m: m[topic] == "online")


def test_killed_app_goes_unavailable(stack):
    docker("kill", stack.app)
    stack.wait_for("app offline via last will", lambda m: m[APP_AVAILABILITY] == "offline", timeout=30)
