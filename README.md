# Serverless URL Shortener

A small, production-minded URL-shortening API built on AWS serverless services and deployed with Terraform.

## Project structure

```text
.
├── lambda/       # Python Lambda handlers
├── scripts/      # Lambda packaging script
├── terraform/    # AWS infrastructure as code
├── .gitignore
└── README.md
```

## Architecture

```text
POST /shorten               GET /{slug}
      |                           |
      v                           v
API Gateway HTTP API        API Gateway HTTP API
      |                           |
      v                           v
Shorten Lambda              Redirect Lambda
      |                           |
      +-------> DynamoDB <--------+
```

- **API Gateway HTTP API** exposes the public routes and applies request throttling.
- **AWS Lambda** validates requests, creates collision-safe slugs, and handles redirects.
- **DynamoDB** stores each slug-to-URL mapping using on-demand billing.
- **CloudWatch Logs** stores Lambda logs for 14 days.
- **Terraform** provisions and tracks the entire AWS stack.

## API

| Method | Route | Description |
| --- | --- | --- |
| `POST` | `/shorten` | Validate a URL, persist it, and return a short URL. |
| `GET` | `/{slug}` | Return an HTTP `302` redirect to the stored URL. |

Example request:

```bash
curl -X POST "$API_URL/shorten" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com"}'
```

Example response:

```json
{
  "short_url": "https://abc123.execute-api.us-east-1.amazonaws.com/N7xD_a2Q"
}
```

## Portfolio-oriented safeguards

- Only `http` and `https` destinations are accepted.
- Malformed JSON, invalid slugs, missing records, and AWS errors return meaningful status codes.
- DynamoDB conditional writes prevent a rare slug collision from overwriting an existing URL.
- Each Lambda receives only the DynamoDB operation it needs (`PutItem` or `GetItem`).
- Lambda execution logs are enabled and automatically expire after 14 days.
- API Gateway is throttled to a configurable rate and burst limit.
- Lambda deployment hashes ensure Terraform publishes updated code archives.
- Terraform state, generated ZIP files, and Python caches are excluded from Git.

## Prerequisites

- An AWS account
- AWS CLI configured with credentials
- Terraform 1.6 or newer
- Bash, Python 3, and `zip`

Verify the tools and AWS identity:

```bash
terraform version
aws --version
aws sts get-caller-identity
```

## Deploy

Package both Lambda functions:

```bash
bash scripts/deploy.sh
```

Review and deploy the infrastructure:

```bash
cd terraform
terraform init
terraform fmt -check
terraform validate
terraform plan -out=tfplan
terraform apply tfplan
```

Retrieve the URL after a successful deployment:

```bash
export API_URL="$(terraform output -raw api_endpoint)"
echo "$API_URL"
```

Test both routes:

```bash
SHORT_URL="$(curl -sS -X POST "$API_URL/shorten" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["short_url"])')"

echo "$SHORT_URL"
curl -sS -o /dev/null -D - "$SHORT_URL"
```

## Configuration

Terraform variables and their defaults are in `terraform/variables.tf`:

| Variable | Default | Purpose |
| --- | --- | --- |
| `region` | `us-east-1` | AWS deployment region. |
| `project_name` | `portfolio-url-shortener` | Prefix for named AWS resources. |
| `shortener_table` | `url-shortener-table` | DynamoDB table name. |
| `throttling_rate_limit` | `10` | Sustained API requests per second. |
| `throttling_burst_limit` | `20` | Short API request burst. |

Override values on the command line when needed:

```bash
terraform apply -var="region=ap-south-1"
```

## Cost and teardown

The stack uses consumption-based services, but AWS usage can still incur charges. Set an AWS Budget for the account and remove the stack when it is no longer needed:

```bash
terraform destroy
```

## Scope and possible extensions

This repository currently provides an API rather than a graphical frontend. Natural extensions include a static web interface, a custom domain with TLS, expiring links through DynamoDB TTL, click analytics, and CI/CD deployment from GitHub Actions.
