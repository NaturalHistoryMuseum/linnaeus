import math

import click
import logging
import os
import re
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
        self.pixel_size = config_dict.get('pixel_size', 50)
        self.size = Size(self.pixel_size,
                         **{k: v for k, v in config_dict.items() if k in Size.keys})
        self.saturation_threshold = config_dict.get('saturation_threshold', 100)
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
            'pixel_size': self.pixel_size,
            'saturation_threshold': self.saturation_threshold,
            'log_level': self._log_level,
            'dominant_colour_method': self.dominant_colour_method
            }
        config_dict.update(self.size.dump())
        with open(path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False)


class Size(object):
    # valid specifiers
    keys = ['area', 'width', 'height']

    def __init__(self, pixel_size, **kwargs):
        self._area = kwargs.get('area', None)
        self._width = kwargs.get('width', None)
        self._height = kwargs.get('height', None)
        self._ps = pixel_size
        if all([x is None for x in [self._area, self._width, self._height]]):
            self._area = '8000c'

    def __str__(self):
        if self._area is not None:
            return 'a' + self._area
        if self._width is not None:
            return 'w' + self._width
        if self._height is not None:
            return 'h' + self._height

    def dump(self):
        return {k: v for k, v in {
            'area': self._area,
            'width': self._width,
            'height': self._height,
            }.items() if v is not None}

    def dimensions(self, image_width, image_height):
        unit_rgx = re.compile('(c|px)$')
        w = image_width
        h = image_height
        if self._width is not None:
            val, unit = unit_rgx.split(self._width)[:2]
            val = int(int(val) / (self._ps if unit == 'px' else 1))
            new_w = val if val < w else w
            h = int(h * (new_w / w))
            w = new_w
        if self._height is not None:
            val, unit = unit_rgx.split(self._height)[:2]
            val = int(int(val) / (self._ps if unit == 'px' else 1))
            new_h = val if val < h else h
            w = int(w * (new_h / h))
            h = new_h
        if self._area is not None:
            val, unit = unit_rgx.split(self._area)[:2]
            val = int(int(val) / (self._ps ** 2 if unit == 'px' else 1))
            a = w * h
            new_a = val if val < a else a
            adjust = math.sqrt(new_a / a)
            w = int(w * adjust)
            h = int(h * adjust)
        return w, h


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
    def __init__(self, use_click=False):
        self._click = use_click

    @property
    def _msg(self):
        return f'time taken: {dt.now() - self.start}'

    def echo(self, msg):
        if self._click:
            click.echo(msg)
        else:
            logger.debug(msg)

    def done(self):
        self.echo(self._msg)

    def __enter__(self):
        self.start = dt.now()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.done()


class ProgressLogger(TimeLogger):
    def __init__(self, total, n_reports, max_seconds=60, use_click=False):
        super(ProgressLogger, self).__init__(use_click)
        self.total = total
        self.current = 0
        self.interval = int(total / n_reports) if total > n_reports else 1
        self.max_seconds = max_seconds

    def next(self):
        self.current += 1
        if self.current % self.interval == 0:
            avg = (dt.now() - self.start).total_seconds() / self.current
            rate = round(1 / avg, 1)
            etr = timedelta(seconds=avg * (self.total - self.current))
            self.echo(f'rate: {rate}/s, estimated time remaining: {etr}')

    @property
    def _msg(self):
        return f'processed {self.current}/{self.total} items in {dt.now() - self.start}'
