import logging
import os
from datetime import datetime as dt, timedelta

import yaml


class Config(object):
    def __init__(self):
        path = os.path.join(os.getcwd(), '.config')
        if os.path.exists(path) and os.path.isfile(path):
            with open(path, 'r') as f:
                config_dict = yaml.safe_load(f)
        else:
            config_dict = {}
        self.max_components = config_dict.get('max_components', 100000)
        self.pixel_width = config_dict.get('pixel_width', 50)
        self.pixel_height = config_dict.get('pixel_height', 50)
        self.pixel_size = (self.pixel_width, self.pixel_height)
        self.max_ref_side = config_dict.get('max_ref_side', 100)
        self.saturation_threshold = config_dict.get('saturation_threshold', 50)
        self.log_level = logging.getLevelName(
            config_dict.get('log_level', 'DEBUG').upper())


constants = Config()

logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(constants.log_level)


class ProgressLogger(object):
    def __init__(self, total, n_reports, max_seconds=60):
        self.total = total
        self.current = 0
        self.interval = int(total / n_reports)
        self.max_seconds = max_seconds

    def __enter__(self):
        self.start = dt.now()
        return self

    def next(self):
        self.current += 1
        if self.current % self.interval == 0:
            avg = (dt.now() - self.start).total_seconds() / self.current
            rate = round(1 / avg, 1)
            etr = timedelta(seconds=avg * (self.total - self.current))
            logger.debug(f'rate: {rate}/s, estimated time remaining: {etr}')

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.debug(f'processed {self.current} items in {dt.now() - self.start}')
