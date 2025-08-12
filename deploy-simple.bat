@echo off
echo Deploying Stock Update Automation to AWS...

echo Step 1: Validating CloudFormation template...
aws cloudformation validate-template --template-body file://cloudformation/codebuild-eventbridge.yaml --region eu-north-1
if %errorlevel% neq 0 (
    echo Template validation failed!
    pause
    exit /b 1
)
echo Template is valid!

echo Step 2: Creating CloudFormation stack...
aws cloudformation create-stack ^
  --stack-name automation-stock-update ^
  --template-body file://cloudformation/codebuild-eventbridge.yaml ^
  --parameters ^
    ParameterKey=GitHubRepoUrl,ParameterValue=https://github.com/TogashiCoder/automation-stock-update ^
    ParameterKey=GitHubBranch,ParameterValue=main ^
    ParameterKey=NotificationEmail,ParameterValue=silverproduction2023@gmail.com ^
    ParameterKey=ProjectName,ParameterValue=automation-stock-update ^
  --capabilities CAPABILITY_NAMED_IAM ^
  --region eu-north-1

if %errorlevel% neq 0 (
    echo Stack creation failed!
    pause
    exit /b 1
)

echo Stack creation initiated! Waiting for completion...
aws cloudformation wait stack-create-complete --stack-name automation-stock-update --region eu-north-1

echo Deployment complete! Getting stack outputs...
aws cloudformation describe-stacks --stack-name automation-stock-update --region eu-north-1 --query "Stacks[0].Outputs"

echo.
echo =====================================================
echo Deployment successful! Next steps:
echo 1. Update Secrets Manager with your FTP credentials
echo 2. Test the CodeBuild project manually
echo 3. Monitor the scheduled runs
echo =====================================================
pause
