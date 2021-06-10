""" Creator
"""

import abc

class Coregister(abc.ABC):
    def __init__(self):
        pass

    @abc.abstractmethod
    def coregistration(self):
        pass

class Sentinel1Coregister(Coregister):
    # concrete creater
    def __init__(self):
        pass

    def coregistration(
        self,
        master,
        slave,
        aoi,
        dem,
        polarization,
        dry_run:bool=False,
        **kwargs,
    ):
        pass
