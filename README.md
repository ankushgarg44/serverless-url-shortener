# Serverless URL Shortener

A small, production-minded URL shortener with a live web interface, built on AWS serverless services and deployed with Terraform.

## Project structure

```text
.
├── lambda/       # Python Lambda handlers
├── scripts/      # Lambda packaging script
├── tests/        # Unit tests and opt-in live API tests
├── terraform/    # AWS infrastructure as code
├── pytest.ini
├── requirements-dev.txt
├── .gitignore
└── README.md
```

## Architecture

```text
GET /                 POST /shorten             GET /{slug}
  |                          |                         |
  v                          v                         v
Frontend Lambda        Shorten Lambda             Redirect Lambda
                             |                         |
                             +-----> DynamoDB <--------+
```

- **API Gateway HTTP API** exposes the web interface and API routes with request throttling.
- **AWS Lambda** serves the interface, validates requests, creates collision-safe slugs, and handles redirects.
- **DynamoDB** stores each slug-to-URL mapping using on-demand billing.
- **CloudWatch Logs** stores Lambda logs for 14 days.
- **Terraform** provisions and tracks the entire AWS stack.

## API

| Method | Route | Description |
| --- | --- | --- |
| `GET` | `/` | Serve the browser-based project demonstration. |
| `POST` | `/shorten` | Validate a URL, persist it, and return a short URL. |
| `GET` | `/{slug}` | Return an HTTP `302` redirect to the stored URL. |

After deployment, open the `demo_url` output in a browser to use the graphical interface:

```bash
open "$(terraform -chdir=terraform output -raw demo_url)"
```

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
- Unit tests mock DynamoDB; end-to-end tests verify the deployed API over HTTPS.
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

## Tests

Create an isolated Python environment and install the development dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

Run the fast unit test suite. The deployed API tests skip automatically when
`API_URL` is not set:

```bash
pytest
```

Run only the end-to-end tests against the currently deployed stack:

```bash
export API_URL="$(terraform -chdir=terraform output -raw api_endpoint)"
pytest tests/api -m api -v
```

The live suite checks the frontend, URL creation, redirects, validation, and
missing slugs. It creates one small URL record in DynamoDB per run.

## Continuous integration

The GitHub Actions workflow in `.github/workflows/ci.yml` runs automatically on
every push and pull request. It performs two independent checks:

- installs the pinned Python dependencies and runs the unit tests;
- packages the Lambda functions, checks Terraform formatting, and runs
  `terraform validate`.

The workflow can also be started manually from **GitHub → Actions → CI → Run
workflow**. It does not deploy infrastructure, use AWS credentials, or run the
live API tests.

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

Natural extensions include a custom domain, expiring links through DynamoDB TTL, click analytics, and CI/CD deployment from GitHub Actions.
