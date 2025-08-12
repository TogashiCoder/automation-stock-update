#!/bin/bash

# Deployment script for stock update automation infrastructure
set -e

# Configuration
STACK_NAME="automation-stock-update"
REGION="eu-north-1"  # Change to your preferred region
GITHUB_REPO="https://github.com/TogashiCoder/automation-stock-update"
NOTIFICATION_EMAIL="silverproduction2023@gmail.com"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Deploying Stock Update Automation Infrastructure${NC}"
echo "Stack Name: $STACK_NAME"
echo "Region: $REGION"
echo "GitHub Repo: $GITHUB_REPO"
echo "Notification Email: $NOTIFICATION_EMAIL"
echo

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo -e "${RED}❌ AWS CLI is not configured or you don't have access${NC}"
    echo "Please run: aws configure"
    exit 1
fi

echo -e "${GREEN}✅ AWS CLI is configured${NC}"

# Get current AWS account and region
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
CURRENT_REGION=$(aws configure get region)

if [ "$CURRENT_REGION" != "$REGION" ]; then
    echo -e "${YELLOW}⚠️  Current AWS region ($CURRENT_REGION) differs from target region ($REGION)${NC}"
    read -p "Do you want to continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "Account ID: $ACCOUNT_ID"
echo "Target Region: $REGION"
echo

# Validate CloudFormation template
echo -e "${YELLOW}🔍 Validating CloudFormation template...${NC}"
aws cloudformation validate-template \
    --template-body file://cloudformation/codebuild-eventbridge.yaml \
    --region $REGION

echo -e "${GREEN}✅ Template is valid${NC}"

# Check if stack already exists
STACK_EXISTS=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].StackStatus' \
    --output text 2>/dev/null || echo "DOES_NOT_EXIST")

if [ "$STACK_EXISTS" != "DOES_NOT_EXIST" ]; then
    echo -e "${YELLOW}⚠️  Stack $STACK_NAME already exists with status: $STACK_EXISTS${NC}"
    read -p "Do you want to update it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ACTION="update-stack"
        echo -e "${YELLOW}🔄 Updating existing stack...${NC}"
    else
        echo "Deployment cancelled."
        exit 0
    fi
else
    ACTION="create-stack"
    echo -e "${GREEN}📦 Creating new stack...${NC}"
fi

# Deploy the stack
aws cloudformation $ACTION \
    --stack-name $STACK_NAME \
    --template-body file://cloudformation/codebuild-eventbridge.yaml \
    --parameters \
        ParameterKey=GitHubRepoUrl,ParameterValue=$GITHUB_REPO \
        ParameterKey=GitHubBranch,ParameterValue=main \
        ParameterKey=MorningScheduleExpression,ParameterValue="cron(0 6 * * MON-SAT *)" \
        ParameterKey=AfternoonScheduleExpression,ParameterValue="cron(0 16 * * MON-SAT *)" \
        ParameterKey=NotificationEmail,ParameterValue=$NOTIFICATION_EMAIL \
        ParameterKey=ProjectName,ParameterValue=$STACK_NAME \
    --capabilities CAPABILITY_NAMED_IAM \
    --region $REGION \
    --tags \
        Key=Project,Value="StockUpdateAutomation" \
        Key=Environment,Value="Production" \
        Key=ManagedBy,Value="CloudFormation"

echo -e "${YELLOW}⏳ Waiting for stack operation to complete...${NC}"

# Wait for stack operation to complete
aws cloudformation wait stack-${ACTION%-stack}-complete \
    --stack-name $STACK_NAME \
    --region $REGION

# Check final status
FINAL_STATUS=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].StackStatus' \
    --output text)

if [[ $FINAL_STATUS == *"COMPLETE"* ]]; then
    echo -e "${GREEN}🎉 Stack deployment successful!${NC}"
    echo
    
    # Get outputs
    echo -e "${GREEN}📋 Stack Outputs:${NC}"
    aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --region $REGION \
        --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
        --output table
    
    echo
    echo -e "${GREEN}🔧 Next Steps:${NC}"
    echo "1. Update the Secrets Manager secret with your actual FTP credentials"
    echo "2. Test the CodeBuild project manually first"
    echo "3. Monitor the first scheduled run"
    echo "4. Check CloudWatch logs for any issues"
    echo
    
    # Get the secrets ARN
    SECRETS_ARN=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --region $REGION \
        --query 'Stacks[0].Outputs[?OutputKey==`SecretsManagerArn`].OutputValue' \
        --output text)
    
    echo -e "${YELLOW}🔐 To update secrets, run:${NC}"
    echo "aws secretsmanager update-secret --secret-id $SECRETS_ARN --secret-string '{\"SMTP_USER\":\"your-email@gmail.com\",\"SMTP_PASSWORD\":\"your-app-password\"}' --region $REGION"
    
else
    echo -e "${RED}❌ Stack deployment failed with status: $FINAL_STATUS${NC}"
    
    # Show stack events for debugging
    echo -e "${RED}📝 Recent stack events:${NC}"
    aws cloudformation describe-stack-events \
        --stack-name $STACK_NAME \
        --region $REGION \
        --query 'StackEvents[0:10].[Timestamp,ResourceStatus,ResourceStatusReason]' \
        --output table
    
    exit 1
fi
