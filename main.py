import os
import copy
import logging
import urllib.parse

import requests

log = logging.getLogger(__name__)


class Api:
    def __init__(self, base_uri, token):
        self.base_url = base_uri
        self.session = requests.Session()
        self.session.headers['Authorization'] = 'Bearer ' + token

    def get(self, uri):
        resp = self.session.get(urllib.parse.urljoin(self.base_url, uri))
        resp.raise_for_status()
        return resp.json()

    def post(self, uri, **kwargs):
        resp = self.session.post(urllib.parse.urljoin(self.base_url, uri), **kwargs)
        resp.raise_for_status()
        return resp.json()


api = Api(urllib.parse.urljoin(os.environ['GRAFANA_URL'], 'api/'), os.environ['GRAFANA_TOKEN'])


def main():
    logging.basicConfig()
    search_results = api.get('search')
    for dashboard_meta in search_results:
        if dashboard_meta['type'] == 'dash-db':
            try:
                patch_dashboard(dashboard_meta)
            except Exception:
                log.exception('Failed to patch dashboard %s', dashboard_meta['title'])


def patch_dashboard(dashboard_meta):
    uid = dashboard_meta['uid']
    dashboard = api.get(f'dashboards/uid/{uid}')['dashboard']
    original_dashboard = copy.deepcopy(dashboard)

    add_common_annotations(dashboard)

    if dashboard != original_dashboard:
        data = {
            'dashboard': dashboard,
            'message': 'add common annotations',
            'overwrite': False,
        }
        api.post('dashboards/db/', json=data)
        print(f'PATCHED {dashboard_meta["title"]}')


def add_common_annotations(dashboard):
    """
    Makes our global "a" annotation visible in all dashboard panels
    """
    annotation_srcs = dashboard['annotations']['list']
    annotation_src = next(src for src in annotation_srcs if src['datasource'] == '-- Grafana --')
    annotation_src['type'] = 'tags'
    annotation_src['matchAny'] = True
    if 'tags' not in annotation_src:
        annotation_src['tags'] = []
    if 'a' not in annotation_src['tags']:
        annotation_src['tags'].append('a')


if __name__ == '__main__':
    main()
