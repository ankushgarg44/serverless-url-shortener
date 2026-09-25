import json
from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError

import shorten_url


def api_event(body, domain='short.example.com'):
    event = {
        'body': body,
        'headers': {'host': domain} if domain else {},
        'requestContext': {},
    }
    return event


def client_error(code):
    return ClientError({'Error': {'Code': code, 'Message': code}}, 'PutItem')


@pytest.mark.parametrize('url', [
    'https://example.com',
    'http://example.com/path?query=value',
    'https://subdomain.example.com:8443/path',
])
def test_accepts_valid_http_urls(url):
    assert shorten_url.is_valid_url(url)


@pytest.mark.parametrize('url', [
    None,
    '',
    'example.com',
    'ftp://example.com',
    'https://user:password@example.com',
    'https://example.com/has space',
    'https://[invalid',
    'https://' + ('a' * 2048),
])
def test_rejects_invalid_urls(url):
    assert not shorten_url.is_valid_url(url)


def test_handler_creates_short_url(monkeypatch):
    table = Mock()
    monkeypatch.setattr(shorten_url, 'get_table', lambda: table)
    monkeypatch.setattr(shorten_url.secrets, 'token_urlsafe', lambda _: 'AbCd_123')

    response = shorten_url.lambda_handler(
        api_event(json.dumps({'url': 'https://example.com'})),
        None,
    )

    assert response['statusCode'] == 201
    assert json.loads(response['body']) == {
        'short_url': 'https://short.example.com/AbCd_123'
    }
    table.put_item.assert_called_once_with(
        Item={'slug': 'AbCd_123', 'url': 'https://example.com'},
        ConditionExpression='attribute_not_exists(slug)',
    )


def test_handler_rejects_malformed_json(monkeypatch):
    table = Mock()
    monkeypatch.setattr(shorten_url, 'get_table', lambda: table)

    response = shorten_url.lambda_handler(api_event('{not-json'), None)

    assert response['statusCode'] == 400
    assert json.loads(response['body'])['error'] == 'Request body must be valid JSON'
    table.put_item.assert_not_called()


def test_handler_rejects_invalid_url_without_writing(monkeypatch):
    table = Mock()
    monkeypatch.setattr(shorten_url, 'get_table', lambda: table)

    response = shorten_url.lambda_handler(
        api_event(json.dumps({'url': 'javascript:alert(1)'})),
        None,
    )

    assert response['statusCode'] == 400
    table.put_item.assert_not_called()


def test_handler_rejects_missing_domain_without_writing(monkeypatch):
    table = Mock()
    monkeypatch.setattr(shorten_url, 'get_table', lambda: table)

    response = shorten_url.lambda_handler(
        api_event(json.dumps({'url': 'https://example.com'}), domain=None),
        None,
    )

    assert response['statusCode'] == 500
    table.put_item.assert_not_called()


def test_create_slug_retries_a_collision(monkeypatch):
    table = Mock()
    table.put_item.side_effect = [
        client_error('ConditionalCheckFailedException'),
        None,
    ]
    slugs = iter(['collision', 'unique_1'])
    monkeypatch.setattr(shorten_url, 'get_table', lambda: table)
    monkeypatch.setattr(shorten_url.secrets, 'token_urlsafe', lambda _: next(slugs))

    slug = shorten_url.create_slug('https://example.com')

    assert slug == 'unique_1'
    assert table.put_item.call_count == 2


def test_handler_returns_500_for_dynamodb_error(monkeypatch):
    table = Mock()
    table.put_item.side_effect = client_error('AccessDeniedException')
    monkeypatch.setattr(shorten_url, 'get_table', lambda: table)

    response = shorten_url.lambda_handler(
        api_event(json.dumps({'url': 'https://example.com'})),
        None,
    )

    assert response['statusCode'] == 500
    assert json.loads(response['body']) == {'error': 'Unable to shorten URL'}
