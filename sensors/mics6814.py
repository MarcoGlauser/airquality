from enviroplus import gas

from sensors.sensor import Sensor


class MICS6814(Sensor):
    def read_data(self):
        data = gas.read_all()
        return {
            'oxidising': data.oxidising,
            'reducing': data.reducing,
            'nh3': data.nh3
        }