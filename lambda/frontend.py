from pathlib import Path


INDEX_HTML = Path(__file__).with_name('index.html').read_text(encoding='utf-8')


def lambda_handler(event, context):
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/html; charset=utf-8',
            'Cache-Control': 'no-store',
            'Content-Security-Policy': (
                "default-src 'self'; "
                "style-src 'unsafe-inline'; "
                "script-src 'unsafe-inline'; "
                "connect-src 'self'; "
                "img-src data:; "
                "base-uri 'none'; "
                "frame-ancestors 'none'; "
                "form-action 'self'"
            ),
            'Referrer-Policy': 'no-referrer',
            'X-Content-Type-Options': 'nosniff',
        },
        'body': INDEX_HTML,
    }
