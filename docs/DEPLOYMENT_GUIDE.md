# Stock Update Automation - Deployment Guide

This guide walks you through setting up automated stock updates using AWS CodeBuild and EventBridge for a "set and forget" solution.

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   EventBridge   │───▶│   CodeBuild     │───▶│   Your Script   │
│   (Scheduler)   │    │   (Container)   │    │  (run_daily.py) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │ Secrets Manager │
                       │ (FTP Creds)     │
                       └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   S3 Bucket     │
                       │ (Artifacts)     │
                       └─────────────────┘
```

## 📋 Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** configured with credentials
3. **Python 3.11+** (for deployment scripts)
4. **GitHub repository** with your code
5. **Gmail account** with app password (for notifications)

## 🚀 Quick Start

### Step 1: Clone and Configure

```bash
git clone https://github.com/your-username/automation-stock-update
cd automation-stock-update
```

### Step 2: Update Configuration

1. Edit `deploy/deploy-stack.sh`:

   ```bash
   GITHUB_REPO="https://github.com/your-username/automation-stock-update"
   NOTIFICATION_EMAIL="your-email@example.com"
   ```

2. Ensure your FTP configuration files exist:
   - `config/fournisseurs_connexions.yaml`
   - `config/plateformes_connexions.yaml`
   - `config/header_mappings.yaml`

### Step 3: Deploy Infrastructure

```bash
# Make deployment script executable (Linux/Mac)
chmod +x deploy/deploy-stack.sh

# Deploy the CloudFormation stack
./deploy/deploy-stack.sh

# Windows users: run directly with bash
# bash deploy/deploy-stack.sh
```

### Step 4: Configure Secrets

```bash
# Interactive setup
python deploy/update-secrets.py --interactive

# Or use a secrets file
python deploy/update-secrets.py --template-only
# Edit secrets-template.json with your credentials
python deploy/update-secrets.py --secrets-file secrets-template.json
```

### Step 5: Test the Setup

```bash
# Test build in dry-run mode
python deploy/test-build.py --start --dry-run --no-email

# Monitor the build
python deploy/test-build.py --recent
```

### Step 6: Go Live

```bash
# Enable real uploads and email notifications
python deploy/test-build.py --start --no-dry-run

# Manage the schedule
python deploy/schedule-management.py --status
python deploy/schedule-management.py --enable
```

## 🔧 Detailed Configuration

### AWS Secrets Manager Configuration

Your secrets should include:

#### Email Configuration

```json
{
  "SMTP_USER": "your-email@gmail.com",
  "SMTP_PASSWORD": "your-gmail-app-password",
  "SMTP_RECIPIENTS": "notify1@example.com,notify2@example.com",
  "EMAIL_ENABLED": "true"
}
```

#### FTP Credentials (for each supplier/platform)

```json
{
  "FTP_PASS_SUPPLIER_NAME": "password",
  "FTP_USER_SUPPLIER_NAME": "username",
  "FTP_HOST_SUPPLIER_NAME": "ftp.supplier.com"
}
```

### Environment Variables

The following environment variables control behavior:

| Variable           | Default | Description                                  |
| ------------------ | ------- | -------------------------------------------- |
| `DRY_RUN_UPLOAD`   | `true`  | Skip actual FTP uploads when `true`          |
| `NO_EMAIL`         | `false` | Skip email reports when `true`               |
| `SUPPLIERS`        | (empty) | Comma-separated list of suppliers to process |
| `PLATFORMS`        | (empty) | Comma-separated list of platforms to process |
| `S3_BACKUP_BUCKET` | (empty) | S3 bucket for backups                        |

### Schedule Configuration

Default schedule: `cron(0 6 * * MON-FRI *)` (6 AM UTC, weekdays)

Common schedule examples:

- Daily: `cron(0 6 * * ? *)`
- Twice daily: `cron(0 6,18 * * ? *)`
- Every 2 hours: `cron(0 */2 * * ? *)`
- Weekly: `cron(0 6 ? * MON *)`

## 📊 Monitoring and Troubleshooting

### CloudWatch Logs

Logs are available in CloudWatch at:

```
/aws/codebuild/automation-stock-update-build
```

### Build Artifacts

Artifacts are stored in S3:

```
automation-stock-update-artifacts-{account-id}/
├── logs/
├── UPDATED_FILES/
├── Verifier/
└── backup/
```

### Common Issues

#### 1. Build Fails with FTP Connection Error

- Check your FTP credentials in Secrets Manager
- Verify FTP server accessibility from AWS (security groups/firewalls)
- Test individual supplier connections

#### 2. Email Notifications Not Sent

- Verify Gmail app password (not regular password)
- Check `EMAIL_ENABLED` is set to `"true"`
- Review SMTP settings in secrets

#### 3. No Files Downloaded

- Check your `config/header_mappings.yaml` file
- Verify supplier FTP servers have files available
- Review the logs for specific error messages

#### 4. Permission Errors

- Ensure IAM roles have proper permissions
- Check S3 bucket policies
- Verify Secrets Manager access

### Monitoring Commands

```bash
# Check recent builds
python deploy/test-build.py --recent

# View rule status
python deploy/schedule-management.py --status

# Check recent invocations
python deploy/schedule-management.py --invocations

# Monitor specific build
python deploy/test-build.py --monitor <build-id>
```

## 🔐 Security Best Practices

1. **Use IAM Roles**: Never use long-term access keys in CodeBuild
2. **Secrets Manager**: Store all sensitive data in AWS Secrets Manager
3. **Least Privilege**: Grant minimal required permissions
4. **VPC**: Consider running CodeBuild in a VPC for network isolation
5. **Encryption**: Enable encryption for S3 buckets and secrets

## 📈 Scaling and Optimization

### Performance Tuning

1. **Parallel Processing**: The script already processes suppliers in parallel
2. **Build Size**: Use `BUILD_GENERAL1_MEDIUM` for most workloads
3. **Timeouts**: Adjust build timeout based on your data volume
4. **Caching**: Consider caching dependencies for faster builds

### Cost Optimization

1. **Schedule Wisely**: Only run when needed (e.g., weekdays only)
2. **Build Size**: Use smallest instance that meets performance needs
3. **Artifacts**: Clean up old artifacts automatically
4. **Logs**: Set appropriate log retention periods

## 🔄 Maintenance

### Regular Tasks

1. **Update Dependencies**: Keep Python packages current
2. **Review Logs**: Check for warnings or errors
3. **Test Connections**: Verify FTP access remains valid
4. **Backup Strategy**: Ensure S3 backups are working

### Updates and Changes

1. **Code Changes**: Push to GitHub, builds will use latest code
2. **Schedule Changes**: Use the schedule management script
3. **Configuration**: Update secrets via AWS console or script
4. **Infrastructure**: Update CloudFormation template as needed

## 📞 Support

For issues:

1. Check CloudWatch logs first
2. Review this documentation
3. Test components individually
4. Check AWS service health
5. Verify network connectivity

## 🔗 Useful Links

- [AWS CodeBuild Documentation](https://docs.aws.amazon.com/codebuild/)
- [EventBridge Cron Expressions](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-cron-expressions.html)
- [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/)
- [CloudWatch Logs](https://docs.aws.amazon.com/cloudwatch/latest/logs/)
