import sys
from datetime import datetime

from backoff import Backoff
from database_service import BME280Helper, LTR559Helper, connect_to_database, S8Helper, MICS6814Helper, PMS7003Helper
from sensors.bme280 import BME280
from sensors.ltr559 import LTR559
from sensors.mics6814 import MICS6814
from sensors.pms7003 import PMS7003
from sensors.s8 import S8

sensors = [
    (BME280(), BME280Helper),
    (LTR559(), LTR559Helper),
    (S8(), S8Helper),
    (MICS6814(), MICS6814Helper),
    (PMS7003(), PMS7003Helper)
]

sensor_backoff = Backoff(initial_backoff=60, max_backoff=180, backoff_increment=60)
LTR559().read_data()
connect_to_database()


def loop():
    try:
        while True:
            for sensor in sensors:
                sensor[1](**sensor[0].read_data())

                print(f'[{datetime.utcnow()}] - reading {type(sensor[0]).__name__}')
            sensor_backoff.backoff()
            print('')
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == '__main__':
    loop()
