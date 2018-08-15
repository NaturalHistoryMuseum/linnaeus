import logging
import os
import yaml
from datetime import datetime as dt, timedelta


class Config(object):
    def __init__(self):
        path = os.path.join(os.getcwd(), '.config')
        if os.path.exists(path) and os.path.isfile(path):
            with open(path, 'r') as f:
                config_dict = yaml.safe_load(f)
        else:
            config_dict = {}
        self.max_components = config_dict.get('max_components', 80000)
        self.pixel_width = config_dict.get('pixel_width', 50)
        self.pixel_height = config_dict.get('pixel_height', 50)
        self.pixel_size = (self.pixel_width, self.pixel_height)
        self.max_ref_size = config_dict.get('max_ref_size', 8000)
        self.saturation_threshold = config_dict.get('saturation_threshold', 50)
        self._log_level = config_dict.get('log_level', 'DEBUG').upper()
        self.dominant_colour_method = config_dict.get('dominant_colour_method',
                                                      'average')

    @property
    def log_level(self):
        return logging.getLevelName(self._log_level)

    @log_level.setter
    def log_level(self, level: str):
        self._log_level = level.upper()

    def dump(self, path):
        config_dict = {
            'max_components': self.max_components,
            'pixel_width': self.pixel_width,
            'pixel_height': self.pixel_height,
            'max_ref_size': self.max_ref_size,
            'saturation_threshold': self.saturation_threshold,
            'log_level': self._log_level,
            'dominant_colour_method': self.dominant_colour_method
            }
        with open(path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False)


constants = Config()

logger = logging.getLogger('linnaeus')
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(constants.log_level)


def silence():
    logger.setLevel(logging.getLevelName('FATAL'))


class TimeLogger(object):
    def done(self):
        logger.debug(f'time taken: {dt.now() - self.start}')

    def __enter__(self):
        self.start = dt.now()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.done()


class ProgressLogger(TimeLogger):
    def __init__(self, total, n_reports, max_seconds=60):
        self.total = total
        self.current = 0
        self.interval = int(total / n_reports)
        self.max_seconds = max_seconds

    def next(self):
        self.current += 1
        if self.current % self.interval == 0:
            avg = (dt.now() - self.start).total_seconds() / self.current
            rate = round(1 / avg, 1)
            etr = timedelta(seconds=avg * (self.total - self.current))
            logger.debug(f'rate: {rate}/s, estimated time remaining: {etr}')

    def done(self):
        logger.debug(f'processed {self.current} items in {dt.now() - self.start}')
