output "api_endpoint" {
  description = "Base URL of the deployed URL shortener API."
  value       = aws_apigatewayv2_api.http_api.api_endpoint
}

output "demo_url" {
  description = "Browser-friendly URL for the live project demo."
  value       = aws_apigatewayv2_api.http_api.api_endpoint
}

output "shorten_endpoint" {
  description = "Endpoint used to create a short URL."
  value       = "${aws_apigatewayv2_api.http_api.api_endpoint}/shorten"
}
