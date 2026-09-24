import json
import logging
import os
import secrets
from urllib.parse import urlsplit

import boto3
from botocore.exceptions import ClientError


logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('TABLE_NAME', 'url-shortener-table'))

MAX_URL_LENGTH = 2048
MAX_SLUG_ATTEMPTS = 5


def json_response(status_code, payload):
    return {
        'statusCode': status_code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(payload),
    }


def is_valid_url(value):
    if not isinstance(value, str) or not value or len(value) > MAX_URL_LENGTH:
        return False

    if any(character.isspace() for character in value):
        return False

    try:
        parsed = urlsplit(value)
        return (
            parsed.scheme in {'http', 'https'}
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
        )
    except ValueError:
        return False


def create_slug(original_url):
    for _ in range(MAX_SLUG_ATTEMPTS):
        slug = secrets.token_urlsafe(6)
        try:
            table.put_item(
                Item={'slug': slug, 'url': original_url},
                ConditionExpression='attribute_not_exists(slug)',
            )
            return slug
        except ClientError as error:
            if error.response.get('Error', {}).get('Code') != 'ConditionalCheckFailedException':
                raise

    raise RuntimeError('Unable to generate a unique slug')


def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body') or '{}')
    except (json.JSONDecodeError, TypeError):
        return json_response(400, {'error': 'Request body must be valid JSON'})

    original_url = body.get('url') if isinstance(body, dict) else None
    if not is_valid_url(original_url):
        return json_response(400, {
            'error': 'url must be a valid http or https URL with no credentials'
        })

    try:
        slug = create_slug(original_url)
    except (ClientError, RuntimeError):
        logger.exception('Failed to create shortened URL')
        return json_response(500, {'error': 'Unable to shorten URL'})

    request_context = event.get('requestContext') or {}
    domain = request_context.get('domainName') or (event.get('headers') or {}).get('host')
    if not domain:
        logger.error('API Gateway domain was missing from the request')
        return json_response(500, {'error': 'Unable to build shortened URL'})

    return json_response(201, {'short_url': f'https://{domain}/{slug}'})
