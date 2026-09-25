import json
import logging
import os
import re

import boto3
from botocore.exceptions import ClientError


logger = logging.getLogger()
logger.setLevel(logging.INFO)

SLUG_PATTERN = re.compile(r'^[A-Za-z0-9_-]{6,32}$')
_table = None


def get_table():
    global _table
    if _table is None:
        dynamodb = boto3.resource('dynamodb')
        _table = dynamodb.Table(os.environ.get('TABLE_NAME', 'url-shortener-table'))
    return _table


def json_response(status_code, payload):
    return {
        'statusCode': status_code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(payload),
    }


def lambda_handler(event, context):
    slug = (event.get('pathParameters') or {}).get('slug', '')
    if not SLUG_PATTERN.fullmatch(slug):
        return json_response(400, {'error': 'Invalid short URL'})

    try:
        response = get_table().get_item(Key={'slug': slug}, ConsistentRead=True)
    except ClientError:
        logger.exception('Failed to retrieve shortened URL')
        return json_response(500, {'error': 'Unable to retrieve URL'})

    item = response.get('Item')

    if item:
        return {
            'statusCode': 302,
            'headers': {
                'Location': item['url'],
                'Cache-Control': 'no-store',
            },
            'body': '',
        }

    return json_response(404, {'error': 'Short URL not found'})
