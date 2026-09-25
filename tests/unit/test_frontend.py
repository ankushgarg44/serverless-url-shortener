import frontend


def test_frontend_returns_demo_page():
    response = frontend.lambda_handler({}, None)

    assert response['statusCode'] == 200
    assert response['headers']['Content-Type'] == 'text/html; charset=utf-8'
    assert response['headers']['X-Content-Type-Options'] == 'nosniff'
    assert "frame-ancestors 'none'" in response['headers']['Content-Security-Policy']
    assert 'Create a short link' in response['body']
