import os
import re
import sys
import time
from concurrent import futures
from io import BytesIO

import requests
from PIL import Image

from .api import API
from .format import Formatter


class Downloader(object):
    asset_rgx = re.compile(
        r'http://www\.nhm\.ac\.uk/services/media-store/asset/(\w+)/contents/.+')

    def __init__(self, folder):
        self.folder = folder

    @staticmethod
    def get(asset_data):
        url = asset_data.get('identifier')
        r = requests.get(url, timeout=10)
        img = Image.open(BytesIO(r.content))
        time.sleep(0.5)
        return img

    def save(self, img, asset_data):
        asset_id = asset_data.get('assetID', 'unknown')
        mime = asset_data.get('mime', 'jpg')
        img.save(f'{self.folder}/{asset_id}.{mime}')

    @staticmethod
    def format(img, detect=True):
        if img.mode == 'RGB':
            if detect:
                img = Formatter.detect(img)
            img = Formatter.rotate(img)
            img = Formatter.resize(img)
            return img
        else:
            return None

    @staticmethod
    def search(query=None, **params):
        assets = []
        for page in API.assets(API.COLLECTIONS, 0, 100, query, **params):
            if len(page) > 0:
                for media in page:
                    assets.append(media)
            else:
                continue
        return assets

    def _download_one(self, asset_data, detect):
        img = self.get(asset_data)
        img = self.format(img, detect)
        if img is not None:
            self.save(img, asset_data)
            self._progress(f'{asset_data.get("assetID")}')

    def _progress(self, txt):
        print(txt, end='\r')
        sys.stdout.flush()

    def download(self, assets, detect=True, redownload=False):
        if not redownload:
            downloaded = [i.split('.')[0] for i in os.listdir(self.folder)]
            assets = [a for a in assets if a.get('assetID') not in downloaded]
        workers = 20
        total = len(assets)
        print(total)
        with futures.ThreadPoolExecutor(workers) as executor:
            executor.map(lambda x: self._download_one(x, detect), assets)
