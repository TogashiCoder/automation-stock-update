# PowerShell deployment script for Windows
# Stock Update Automation Infrastructure

$STACK_NAME = "automation-stock-update"
$REGION = "eu-north-1"
$GITHUB_REPO = "https://github.com/TogashiCoder/automation-stock-update"
$NOTIFICATION_EMAIL = "silverproduction2023@gmail.com"

Write-Host "🚀 Deploying Stock Update Automation Infrastructure" -ForegroundColor Green
Write-Host "Stack Name: $STACK_NAME"
Write-Host "Region: $REGION"
Write-Host "GitHub Repo: $GITHUB_REPO"
Write-Host "Notification Email: $NOTIFICATION_EMAIL"
Write-Host ""

# Check if AWS CLI is configured
try {
    $callerIdentity = aws sts get-caller-identity 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "AWS CLI not configured"
    }
    Write-Host "✅ AWS CLI is configured" -ForegroundColor Green
} catch {
    Write-Host "❌ AWS CLI is not configured or you don't have access" -ForegroundColor Red
    Write-Host "Please run: aws configure"
    exit 1
}

# Get current AWS account and region
$ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text)
Write-Host "Account ID: $ACCOUNT_ID"
Write-Host "Target Region: $REGION"
Write-Host ""

# Validate CloudFormation template
Write-Host "🔍 Validating CloudFormation template..." -ForegroundColor Yellow
try {
    aws cloudformation validate-template --template-body file://cloudformation/codebuild-eventbridge.yaml --region $REGION
    Write-Host "✅ Template is valid" -ForegroundColor Green
} catch {
    Write-Host "❌ Template validation failed" -ForegroundColor Red
    exit 1
}

# Check if stack already exists
Write-Host "📋 Checking if stack exists..."
$STACK_EXISTS = $false
try {
    $stackStatus = aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].StackStatus' --output text 2>$null
    if ($LASTEXITCODE -eq 0) {
        $STACK_EXISTS = $true
        Write-Host "⚠️  Stack $STACK_NAME already exists with status: $stackStatus" -ForegroundColor Yellow
        $response = Read-Host "Do you want to update it? (y/N)"
        if ($response -eq "y" -or $response -eq "Y") {
            $ACTION = "update-stack"
            Write-Host "🔄 Updating existing stack..." -ForegroundColor Yellow
        } else {
            Write-Host "Deployment cancelled."
            exit 0
        }
    }
} catch {
    # Stack doesn't exist
}

if (-not $STACK_EXISTS) {
    $ACTION = "create-stack"
    Write-Host "📦 Creating new stack..." -ForegroundColor Green
}

# Deploy the stack
Write-Host "🚀 Deploying stack..." -ForegroundColor Green
try {
    aws cloudformation $ACTION `
        --stack-name $STACK_NAME `
        --template-body file://cloudformation/codebuild-eventbridge.yaml `
        --parameters `
            ParameterKey=GitHubRepoUrl,ParameterValue=$GITHUB_REPO `
            ParameterKey=GitHubBranch,ParameterValue=main `
            "ParameterKey=MorningScheduleExpression,ParameterValue=cron(0 6 * * MON-SAT *)" `
            "ParameterKey=AfternoonScheduleExpression,ParameterValue=cron(0 16 * * MON-SAT *)" `
            ParameterKey=NotificationEmail,ParameterValue=$NOTIFICATION_EMAIL `
            ParameterKey=ProjectName,ParameterValue=$STACK_NAME `
        --capabilities CAPABILITY_NAMED_IAM `
        --region $REGION `
        --tags `
            Key=Project,Value="StockUpdateAutomation" `
            Key=Environment,Value="Production" `
            Key=ManagedBy,Value="CloudFormation"

    if ($LASTEXITCODE -ne 0) {
        throw "Stack deployment failed"
    }
} catch {
    Write-Host "❌ Stack deployment failed" -ForegroundColor Red
    exit 1
}

Write-Host "⏳ Waiting for stack operation to complete..." -ForegroundColor Yellow

# Wait for stack operation to complete
$waitAction = if ($ACTION -eq "create-stack") { "stack-create-complete" } else { "stack-update-complete" }
aws cloudformation wait $waitAction --stack-name $STACK_NAME --region $REGION

# Check final status
$FINAL_STATUS = aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].StackStatus' --output text

if ($FINAL_STATUS -like "*COMPLETE*") {
    Write-Host "🎉 Stack deployment successful!" -ForegroundColor Green
    Write-Host ""
    
    # Get outputs
    Write-Host "📋 Stack Outputs:" -ForegroundColor Green
    aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' --output table
    
    Write-Host ""
    Write-Host "🔧 Next Steps:" -ForegroundColor Green
    Write-Host "1. Update the Secrets Manager secret with your actual FTP credentials"
    Write-Host "2. Test the CodeBuild project manually first"
    Write-Host "3. Monitor the first scheduled run"
    Write-Host "4. Check CloudWatch logs for any issues"
    Write-Host ""
    
    # Get the secrets ARN
    $SECRETS_ARN = aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`SecretsManagerArn`].OutputValue' --output text
    
    Write-Host "🔐 To update secrets, run:" -ForegroundColor Yellow
    Write-Host "aws secretsmanager update-secret --secret-id $SECRETS_ARN --secret-string '{...}' --region $REGION"
    
} else {
    Write-Host "❌ Stack deployment failed with status: $FINAL_STATUS" -ForegroundColor Red
    
    # Show stack events for debugging
    Write-Host "📝 Recent stack events:" -ForegroundColor Red
    aws cloudformation describe-stack-events --stack-name $STACK_NAME --region $REGION --query 'StackEvents[0:10].[Timestamp,ResourceStatus,ResourceStatusReason]' --output table
    
    exit 1
}
