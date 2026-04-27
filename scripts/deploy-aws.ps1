param(
  [Parameter(Mandatory = $true)]
  [string] $Region,

  [Parameter(Mandatory = $true)]
  [string] $VpcId,

  [Parameter(Mandatory = $true)]
  [string[]] $PublicSubnetIds,

  [string] $ProjectName = "hpdc-estimator",
  [int] $DesiredCount = 1
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$TemplatePath = Join-Path $Root "aws/cloudformation.yml"
$EnvPath = Join-Path $Root ".env"

function Assert-Command {
  param([string] $Name)
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "$Name is not installed or not available on PATH."
  }
}

function Read-DotEnv {
  param([string] $Path)
  $values = @{}
  if (-not (Test-Path $Path)) {
    return $values
  }

  Get-Content $Path | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
      return
    }

    $parts = $line.Split("=", 2)
    $key = $parts[0].Trim()
    $value = $parts[1].Trim().Trim('"').Trim("'")
    $values[$key] = $value
  }

  return $values
}

function Ensure-EcrRepository {
  param(
    [string] $Name,
    [string] $Region
  )

  $repoUri = aws ecr describe-repositories `
    --repository-names $Name `
    --region $Region `
    --query "repositories[0].repositoryUri" `
    --output text 2>$null

  if ($LASTEXITCODE -ne 0 -or -not $repoUri -or $repoUri -eq "None") {
    $repoUri = aws ecr create-repository `
      --repository-name $Name `
      --region $Region `
      --image-scanning-configuration scanOnPush=true `
      --query "repository.repositoryUri" `
      --output text
  }

  return $repoUri
}

Assert-Command "aws"
Assert-Command "docker"

$envValues = Read-DotEnv $EnvPath
$accountId = aws sts get-caller-identity --query "Account" --output text --region $Region
if (-not $accountId) {
  throw "AWS credentials are not configured. Run aws configure or set AWS_PROFILE/AWS_* environment variables."
}

$registry = "$accountId.dkr.ecr.$Region.amazonaws.com"
aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin $registry

$tag = Get-Date -Format "yyyyMMddHHmmss"
$backendRepo = Ensure-EcrRepository "$ProjectName-backend" $Region
$frontendRepo = Ensure-EcrRepository "$ProjectName-frontend" $Region
$backendImage = "$backendRepo`:$tag"
$frontendImage = "$frontendRepo`:$tag"

docker build -t $backendImage -f (Join-Path $Root "backend/Dockerfile") $Root
docker push $backendImage

docker build -t $frontendImage (Join-Path $Root "frontend")
docker push $frontendImage

$groqModel = if ($envValues.ContainsKey("GROQ_MODEL")) { $envValues["GROQ_MODEL"] } else { "llama-3.3-70b-versatile" }
$groqApiKey = if ($envValues.ContainsKey("GROQ_API_KEY")) { $envValues["GROQ_API_KEY"] } else { "" }
$firecrawlApiKey = if ($envValues.ContainsKey("FIRECRAWL_API_KEY")) { $envValues["FIRECRAWL_API_KEY"] } else { "" }
$tinyfishApiKey = if ($envValues.ContainsKey("TINYFISH_API_KEY")) { $envValues["TINYFISH_API_KEY"] } else { "" }
$metalsApiKey = if ($envValues.ContainsKey("METALS_API_KEY")) { $envValues["METALS_API_KEY"] } else { "" }
$subnetCsv = $PublicSubnetIds -join ","

aws cloudformation deploy `
  --template-file $TemplatePath `
  --stack-name "$ProjectName-stack" `
  --region $Region `
  --capabilities CAPABILITY_IAM `
  --parameter-overrides `
    "ProjectName=$ProjectName" `
    "VpcId=$VpcId" `
    "PublicSubnetIds=$subnetCsv" `
    "BackendImageUri=$backendImage" `
    "FrontendImageUri=$frontendImage" `
    "DesiredCount=$DesiredCount" `
    "GroqModel=$groqModel" `
    "GroqApiKey=$groqApiKey" `
    "FirecrawlApiKey=$firecrawlApiKey" `
    "TinyfishApiKey=$tinyfishApiKey" `
    "MetalsApiKey=$metalsApiKey"

$appUrl = aws cloudformation describe-stacks `
  --stack-name "$ProjectName-stack" `
  --region $Region `
  --query "Stacks[0].Outputs[?OutputKey=='AppUrl'].OutputValue | [0]" `
  --output text

Write-Host "Deployment complete: $appUrl"
