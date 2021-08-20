import urllib.parse as urlparse
from urllib.parse import urlencode


def merge_params(url, params):
    url_parts = list(urlparse.urlparse(url))
    query = dict(urlparse.parse_qsl(url_parts[4]))
    query.update(params)
    url_parts[4] = urlencode(query)
    return urlparse.urlunparse(url_parts)


def parse_params(authorization_response):
    parsed = urlparse.urlparse(authorization_response)
    simple_dict = {}
    for k, v in urlparse.parse_qs(parsed.query).items():
        simple_dict[k] = v[0]
    return simple_dict
