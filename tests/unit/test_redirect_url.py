import json
from unittest.mock import Mock

from botocore.exceptions import ClientError

import redirect_url


def redirect_event(slug):
    return {'pathParameters': {'slug': slug}}


def test_redirects_existing_slug(monkeypatch):
    table = Mock()
    table.get_item.return_value = {'Item': {'url': 'https://example.com'}}
    monkeypatch.setattr(redirect_url, 'get_table', lambda: table)

    response = redirect_url.lambda_handler(redirect_event('AbCd_123'), None)

    assert response['statusCode'] == 302
    assert response['headers']['Location'] == 'https://example.com'
    assert response['headers']['Cache-Control'] == 'no-store'
    table.get_item.assert_called_once_with(
        Key={'slug': 'AbCd_123'},
        ConsistentRead=True,
    )


def test_returns_404_for_unknown_slug(monkeypatch):
    table = Mock()
    table.get_item.return_value = {}
    monkeypatch.setattr(redirect_url, 'get_table', lambda: table)

    response = redirect_url.lambda_handler(redirect_event('missing1'), None)

    assert response['statusCode'] == 404
    assert json.loads(response['body']) == {'error': 'Short URL not found'}


def test_rejects_invalid_slug_without_reading(monkeypatch):
    table = Mock()
    monkeypatch.setattr(redirect_url, 'get_table', lambda: table)

    response = redirect_url.lambda_handler(redirect_event('../bad'), None)

    assert response['statusCode'] == 400
    table.get_item.assert_not_called()


def test_returns_500_for_dynamodb_error(monkeypatch):
    table = Mock()
    table.get_item.side_effect = ClientError(
        {'Error': {'Code': 'InternalServerError', 'Message': 'failed'}},
        'GetItem',
    )
    monkeypatch.setattr(redirect_url, 'get_table', lambda: table)

    response = redirect_url.lambda_handler(redirect_event('AbCd_123'), None)

    assert response['statusCode'] == 500
    assert json.loads(response['body']) == {'error': 'Unable to retrieve URL'}
