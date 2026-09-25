import json
import os
import ssl
import uuid
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener, urlopen

import certifi
import pytest


API_URL = os.environ.get('API_URL', '').rstrip('/')
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
pytestmark = [
    pytest.mark.api,
    pytest.mark.skipif(not API_URL, reason='Set API_URL to run deployed API tests'),
]


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def post_json(path, payload):
    request = Request(
        f'{API_URL}{path}',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    return urlopen(request, timeout=10, context=SSL_CONTEXT)


def test_frontend_is_publicly_available():
    with urlopen(f'{API_URL}/', timeout=10, context=SSL_CONTEXT) as response:
        body = response.read().decode('utf-8')
        status = response.status
        content_type = response.headers.get_content_type()

    assert status == 200
    assert content_type == 'text/html'
    assert 'Create a short link' in body


def test_create_and_follow_short_url():
    destination = f'https://example.com/?api-test={uuid.uuid4().hex}'

    with post_json('/shorten', {'url': destination}) as response:
        payload = json.load(response)
        status = response.status

    short_url = payload['short_url']
    assert status == 201
    assert urlparse(short_url).netloc == urlparse(API_URL).netloc

    with pytest.raises(HTTPError) as redirect:
        build_opener(HTTPSHandler(context=SSL_CONTEXT), NoRedirect).open(
            short_url, timeout=10
        )

    assert redirect.value.code == 302
    assert redirect.value.headers['Location'] == destination


def test_invalid_url_is_rejected():
    with pytest.raises(HTTPError) as error:
        post_json('/shorten', {'url': 'javascript:alert(1)'})

    assert error.value.code == 400
    assert json.load(error.value) == {
        'error': 'url must be a valid http or https URL with no credentials'
    }


def test_unknown_slug_returns_404():
    slug = f'missing{uuid.uuid4().hex[:12]}'

    with pytest.raises(HTTPError) as error:
        urlopen(f'{API_URL}/{slug}', timeout=10, context=SSL_CONTEXT)

    assert error.value.code == 404
    assert json.load(error.value) == {'error': 'Short URL not found'}
