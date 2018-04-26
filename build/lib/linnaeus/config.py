import os

import yaml


class Config(object):
    def __init__(self):
        path = os.path.join(os.getcwd(), '.config')
        if os.path.exists(path) and os.path.isfile(path):
            with open(path, 'r') as f:
                config_dict = yaml.safe_load(f)
        else:
            config_dict = {}
        self.pixel_width = config_dict.get('pixel_width', 50)
        self.pixel_height = config_dict.get('pixel_height', 50)
        self.pixel_size = (self.pixel_width, self.pixel_height)
        self.max_ref_side = config_dict.get('max_ref_side', 100)
        self.saturation_threshold = config_dict.get('saturation_threshold', 50)


constants = Config()
