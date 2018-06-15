import json

import requests


class API(object):
    base_url = 'http://data.nhm.ac.uk/api/3'
    COLLECTIONS = '05ff2255-c38a-40c9-b657-4ccb55ab2feb'
    asset_url = 'http://www.nhm.ac.uk/services/media-store/asset/{0}/contents/preview'

    @classmethod
    def get_result(cls, response):
        j = response.json()
        if response.ok and j.get('success', False) and j.get('result', {}).get('total',
                                                                               0) > 0:
            return j.get('result', j)
        else:
            return None

    @classmethod
    def get_params(cls, filters, query=None, **params):
        if query is not None:
            params['q'] = query
        params['filters'] = json.dumps(filters)
        return params

    @classmethod
    def resource(cls, resource_id, offset=0, limit=100, records_only=True, query=None,
                 **filters):
        url = cls.base_url + '/action/datastore_search'
        params = API.get_params(filters, query, resource_id=resource_id, limit=limit)
        return ResultsIterator(url, offset, records_only, **params)

    @classmethod
    def assets(cls, resource_id, offset=0, limit=100, query=None, **filters):
        url = cls.base_url + '/action/datastore_search'
        filters['_has_multimedia'] = True
        params = API.get_params(filters, query, resource_id=resource_id, limit=limit)
        return AssetIterator(url, offset, True, **params)

    @classmethod
    def collections(cls, offset=0, limit=100, records_only=True, query=None, **filters):
        return cls.resource(cls.COLLECTIONS, offset, limit, records_only, query,
                            **filters)


class ResultsIterator(object):
    def __init__(self, url, offset=0, records_only=True, **params):
        self.url = url
        self.records_only = records_only
        self.offset = offset
        self.params = params

    def __iter__(self):
        return self

    def __next__(self):
        self.params['offset'] = self.offset
        r = requests.get(self.url, params=self.params)
        if not r.ok:
            raise StopIteration
        result = API.get_result(r)
        if result is None or (
                self.records_only and 'records' not in result) or self.offset >= \
                result.get(
                'total', 0):
            raise StopIteration
        else:
            self.offset += len(result['records'])
            if self.records_only:
                return result['records']
            return result


class AssetIterator(ResultsIterator):
    def __next__(self):
        records = super(AssetIterator, self).__next__()
        assets = []
        for record in records:
            media = json.loads(record.get('associatedMedia'))
            assets += media
        if len(assets) > 0:
            return assets
        else:
            return self.__next__()
