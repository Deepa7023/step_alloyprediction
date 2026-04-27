# AWS Deployment

This project deploys to AWS as one ECS Fargate service with two containers:

- `frontend`: Next.js on port `3000`
- `backend`: FastAPI on port `5000`

An Application Load Balancer exposes the site on HTTP. Requests under `/api/*` are routed to FastAPI; all other paths are routed to Next.js.

## Prerequisites

- AWS CLI v2 configured with deploy permissions
- Docker Desktop running
- A VPC ID and at least two public subnet IDs in the target AWS region
- API keys in the local `.env` file if live Groq, Firecrawl, Tinyfish, or metals pricing should be enabled

## Deploy

```powershell
.\scripts\deploy-aws.ps1 `
  -Region ap-south-1 `
  -VpcId vpc-xxxxxxxx `
  -PublicSubnetIds subnet-aaaaaaaa,subnet-bbbbbbbb
```

The script builds both Docker images, pushes them to ECR, creates or updates the CloudFormation stack, stores runtime API keys in AWS Secrets Manager, and prints the public app URL.

## Notes

- The deployed frontend uses same-origin API calls by default, so no production backend URL is baked into the browser bundle.
- The stack currently exposes HTTP on port `80`. Add an ACM certificate and HTTPS listener before using it for customer data.
- AWS resources created by this stack can incur cost while running.
