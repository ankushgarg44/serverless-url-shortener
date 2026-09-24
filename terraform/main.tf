locals {
  shorten_function_name  = "${var.project_name}-shorten"
  redirect_function_name = "${var.project_name}-redirect"
  frontend_function_name = "${var.project_name}-frontend"

  lambda_assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_dynamodb_table" "shortener" {
  name         = var.shortener_table
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "slug"

  attribute {
    name = "slug"
    type = "S"
  }
}

resource "aws_iam_role" "shorten_lambda" {
  name               = "${var.project_name}-shorten"
  assume_role_policy = local.lambda_assume_role_policy
}

resource "aws_iam_role" "redirect_lambda" {
  name               = "${var.project_name}-redirect"
  assume_role_policy = local.lambda_assume_role_policy
}

resource "aws_iam_role" "frontend_lambda" {
  name               = "${var.project_name}-frontend"
  assume_role_policy = local.lambda_assume_role_policy
}

resource "aws_iam_role_policy" "shorten_dynamodb" {
  name = "write-short-url"
  role = aws_iam_role.shorten_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["dynamodb:PutItem"]
      Resource = aws_dynamodb_table.shortener.arn
    }]
  })
}

resource "aws_iam_role_policy" "redirect_dynamodb" {
  name = "read-short-url"
  role = aws_iam_role.redirect_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["dynamodb:GetItem"]
      Resource = aws_dynamodb_table.shortener.arn
    }]
  })
}

resource "aws_iam_role_policy_attachment" "shorten_logging" {
  role       = aws_iam_role.shorten_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "redirect_logging" {
  role       = aws_iam_role.redirect_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "frontend_logging" {
  role       = aws_iam_role.frontend_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "shorten" {
  function_name    = local.shorten_function_name
  runtime          = "python3.13"
  handler          = "shorten_url.lambda_handler"
  role             = aws_iam_role.shorten_lambda.arn
  filename         = "${path.module}/../lambda/shorten_url.zip"
  source_code_hash = filebase64sha256("${path.module}/../lambda/shorten_url.zip")
  memory_size      = 128
  timeout          = 5

  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.shortener.name
    }
  }

  depends_on = [
    aws_iam_role_policy.shorten_dynamodb,
    aws_iam_role_policy_attachment.shorten_logging,
  ]
}

resource "aws_lambda_function" "redirect" {
  function_name    = local.redirect_function_name
  runtime          = "python3.13"
  handler          = "redirect_url.lambda_handler"
  role             = aws_iam_role.redirect_lambda.arn
  filename         = "${path.module}/../lambda/redirect_url.zip"
  source_code_hash = filebase64sha256("${path.module}/../lambda/redirect_url.zip")
  memory_size      = 128
  timeout          = 5

  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.shortener.name
    }
  }

  depends_on = [
    aws_iam_role_policy.redirect_dynamodb,
    aws_iam_role_policy_attachment.redirect_logging,
  ]
}

resource "aws_lambda_function" "frontend" {
  function_name    = local.frontend_function_name
  runtime          = "python3.13"
  handler          = "frontend.lambda_handler"
  role             = aws_iam_role.frontend_lambda.arn
  filename         = "${path.module}/../lambda/frontend.zip"
  source_code_hash = filebase64sha256("${path.module}/../lambda/frontend.zip")
  memory_size      = 128
  timeout          = 5

  depends_on = [aws_iam_role_policy_attachment.frontend_logging]
}

resource "aws_cloudwatch_log_group" "shorten" {
  name              = "/aws/lambda/${local.shorten_function_name}"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "redirect" {
  name              = "/aws/lambda/${local.redirect_function_name}"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "frontend" {
  name              = "/aws/lambda/${local.frontend_function_name}"
  retention_in_days = 14
}

resource "aws_apigatewayv2_api" "http_api" {
  name          = "${var.project_name}-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_headers = ["content-type"]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_origins = ["*"]
    max_age       = 3600
  }
}

resource "aws_apigatewayv2_integration" "shorten" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.shorten.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "redirect" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.redirect.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "frontend" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.frontend.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "shorten" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /shorten"
  target    = "integrations/${aws_apigatewayv2_integration.shorten.id}"
}

resource "aws_apigatewayv2_route" "redirect" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /{slug}"
  target    = "integrations/${aws_apigatewayv2_integration.redirect.id}"
}

resource "aws_apigatewayv2_route" "frontend" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /"
  target    = "integrations/${aws_apigatewayv2_integration.frontend.id}"
}

resource "aws_lambda_permission" "apigw_shorten" {
  statement_id  = "AllowAPIGatewayShorten"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.shorten.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/POST/shorten"
}

resource "aws_lambda_permission" "apigw_redirect" {
  statement_id  = "AllowAPIGatewayRedirect"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.redirect.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/GET/*"
}

resource "aws_lambda_permission" "apigw_frontend" {
  statement_id  = "AllowAPIGatewayFrontend"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.frontend.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/GET/"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = "$default"
  auto_deploy = true

  default_route_settings {
    detailed_metrics_enabled = false
    throttling_burst_limit   = var.throttling_burst_limit
    throttling_rate_limit    = var.throttling_rate_limit
  }
}
