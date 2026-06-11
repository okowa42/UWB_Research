import numpy as np

from simulation import measurements, station

class Scenario:
    def __init__(self, name = "New"):
        self._name = str(name)
        self._measurements = measurements.Measurements()
        self._stations = []
        self._sigma = 0.0
        self._tag_truth = station.Anchor([0.0, 0.0, 0.0], 'TAG_TRUTH')

    def anchor_positions(self):
        return np.array([anchor.position() for anchor in self.get_anchor_list()])

    def tag_positions(self):
        return np.array([tag.position() for tag in self.get_tag_list()])

    def get_station_by_name(self, name):
        for s in self.stations:
            if str(s.name) == str(name):
                return s
        new_station = station.Tag(self, name)
        self.stations.append(new_station)
        return new_station

    def get_tag_list(self):
        return [s for s in self.stations if isinstance(s, station.Tag)]

    def get_anchor_list(self):
        return [s for s in self.stations if isinstance(s, station.Anchor)]

    def generate_measurements(self, tag_estimate, tag_truth):
        """Synthesize distance measurements between every anchor and tag_truth,
        adding gaussian noise (stddev=sigma), and register them for tag_estimate.
        """
        for anchor in self.get_anchor_list():
            # TODO this ignores the TAG_TRUTH as an Anchor. Make sure it is never used for positioning or GDOP calculation
            if np.array_equal(anchor.position(), tag_truth.position()):
                continue
            distance = np.random.normal(anchor.distance_to(tag_truth) + self.sigma, self.sigma)
            self.measurements.update_relation(frozenset([anchor, tag_estimate]), distance)

    def start_streaming(self, url):
        # TODO implement streaming
        pass

    def stop_streaming(self):
        #TODO implement streaming
        pass

    def remove_station(self, station):
        if station in self.stations:
            self.measurements.remove_station(station)
            self.stations.remove(station)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = str(value)

    @property
    def measurements(self):
        return self._measurements

    @measurements.setter
    def measurements(self, value):
        self._measurements = value

    @property
    def stations(self):
        return self._stations

    @stations.setter
    def stations(self, value):
        self._stations = list(value)

    @property
    def sigma(self):
        return self._sigma

    @sigma.setter
    def sigma(self, value):
        self._sigma = float(value)

    @property
    def streamer(self):
        return self._streamer

    @streamer.setter
    def streamer(self, value):
        self._streamer = value

    @property
    def tag_truth(self):
        return self._tag_truth

    @tag_truth.setter
    def tag_truth(self, value):
        self._tag_truth = value
