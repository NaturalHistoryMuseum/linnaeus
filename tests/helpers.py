import os
from types import SimpleNamespace
import json

_local_root = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data/')

local = SimpleNamespace(root=_local_root, image=_local_root + 'img.jpg')

urls = SimpleNamespace(portal_image='http://www.nhm.ac.uk/services/media-store/asset'
                                    '/3f77768aaffdbc58eb5bfa2ef9cafe1f58a773de/contents'
                                    '/preview',
                       random_image='http://placekitten.com/g/200/300')

serialised = SimpleNamespace(ref='{"1|1":[255,255,255]}',
                             comp='{"specimens/assetid.jpg":[255,255,255]}',
                             sol='{"1|1":{"path":"specimens/assetid.jpg","target":[0, 0, 0]}}',
                             invalid='{"0|0|0":[300,300,300]}')

with open(_local_root + 'portal-response.json', 'r') as f:
    _portal = f.read()

responses = SimpleNamespace(portal=_portal)
