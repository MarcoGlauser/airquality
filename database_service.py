import os
import time

from dotenv import load_dotenv
from influxdb import InfluxDBClient
from influxdb import SeriesHelper

load_dotenv()

host = os.getenv("INFLUXDB_HOST")
port = 8086
user = os.getenv("INFLUXDB_USERNAME")
password = os.getenv("INFLUXDB_PASSWORD")
dbname = os.getenv("INFLUXDB_DB")

myclient = InfluxDBClient(host, port, user, password, dbname)


def connect_to_database():
    connected = False

    while not connected:
        try:
            myclient.ping()
            connected = True
            print('Connection to Influxdb successful!')
        except Exception:
            print('Connection to Influxdb failed. Sleeping 1 Second')
            time.sleep(1)


class BaseMeta:
    client = myclient
    tags = []

    # Defines the number of data points to store prior to writing
    # on the wire.
    bulk_size = 1

    # autocommit must be set to True when using bulk_size
    autocommit = True


class BME280Helper(SeriesHelper):

    class Meta(BaseMeta):
        series_name = 'bme280'

        fields = ['temperature', 'humidity', 'pressure']


class LTR559Helper(SeriesHelper):
    class Meta(BaseMeta):
        series_name = 'ltr559'

        fields = ['illuminance']


class S8Helper(SeriesHelper):
    class Meta(BaseMeta):
        series_name = 's8'

        fields = ['co2']

class MICS6814Helper(SeriesHelper):
    class Meta(BaseMeta):
        series_name = 'mics6814'

        fields = ['oxidising', 'reducing' ,'nh3']

class PMS7003Helper(SeriesHelper):
    class Meta(BaseMeta):
        series_name = 'pms7003'

        fields = ['pm1_0', 'pm2_5', 'pm10']