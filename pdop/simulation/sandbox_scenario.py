from .scenario import Scenario
from simulation import station


class SandboxScenario(Scenario):

    def __init__(self, name="Sandbox"):
        super().__init__(name)

        self.stations = [
            station.Anchor([0.0, 0.0, 0.0], 'Anchor A'),
            station.Anchor([10.0, 0.0, 0.0], 'Anchor B'),
            station.Anchor([5.0, 8.66, 0.0], 'Anchor C'),
            station.Anchor([5.0, 2.89, 6.0], 'Anchor D'),
            station.Tag(self, 'SANDBOX_TAG')
        ]

        self.tag_truth = station.Anchor([5.0, 4.0, 1.0], 'TAG_TRUTH')

        for tag in self.get_tag_list():
            self.generate_measurements(tag, self.tag_truth)
