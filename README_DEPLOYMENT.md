# 🚀 AWS CodeBuild + EventBridge Automation Setup

Complete "set and forget" deployment guide for automated stock updates using AWS CodeBuild and EventBridge.

## 📋 Quick Start Checklist

- [ ] AWS Account with appropriate permissions
- [ ] AWS CLI configured (`aws configure`)
- [ ] GitHub repository with your code
- [ ] Gmail account with app password for notifications
- [ ] Python 3.11+ installed locally

## 🎯 One-Command Deployment

```bash
# 1. Configure your settings
vim deploy/deploy-stack.sh  # Update GITHUB_REPO and NOTIFICATION_EMAIL

# 2. Deploy everything
bash deploy/deploy-stack.sh

# 3. Configure secrets
python deploy/update-secrets.py --interactive

# 4. Test the setup
python deploy/test-build.py --start --dry-run

# 5. Validate deployment
python deploy/validate-deployment.py --test-build

# 6. Go live!
python deploy/schedule-management.py --enable
```

## 🏗️ What Gets Deployed

### Infrastructure Components

1. **CodeBuild Project**: Runs your stock update script
2. **EventBridge Rule**: Schedules daily execution (6 AM UTC, weekdays)
3. **S3 Bucket**: Stores build artifacts and logs
4. **Secrets Manager**: Securely stores FTP credentials and email settings
5. **IAM Roles**: Proper permissions for all services
6. **CloudWatch**: Logs and monitoring
7. **SNS Topic**: Failure notifications

### Default Configuration

- **Schedule**: `cron(0 6 * * MON-FRI *)` (6 AM UTC, weekdays)
- **Build Environment**: Amazon Linux 2, Python 3.11
- **Timeout**: 60 minutes
- **Dry Run**: Enabled by default (safe testing)
- **Email Reports**: Disabled during initial testing

## 🔧 Management Scripts

### Deployment and Setup

```bash
# Deploy infrastructure
bash deploy/deploy-stack.sh

# Set up local development environment
python deploy/setup-env.py --all

# Update secrets interactively
python deploy/update-secrets.py --interactive

# Update secrets from file
python deploy/update-secrets.py --secrets-file secrets.json
```

### Testing and Validation

```bash
# Start a test build
python deploy/test-build.py --start --dry-run --no-email

# Monitor specific build
python deploy/test-build.py --monitor <build-id>

# View recent builds
python deploy/test-build.py --recent

# Full deployment validation
python deploy/validate-deployment.py --test-build

# Save validation report
python deploy/validate-deployment.py --report validation-report.json
```

### Schedule Management

```bash
# View current status
python deploy/schedule-management.py --status

# Enable/disable automation
python deploy/schedule-management.py --enable
python deploy/schedule-management.py --disable

# Update schedule
python deploy/schedule-management.py --schedule "cron(0 8 * * MON-FRI *)"

# View next execution times
python deploy/schedule-management.py --status --next 10

# Show recent invocations
python deploy/schedule-management.py --invocations

# Show schedule examples
python deploy/schedule-management.py --examples
```

## 🔐 Security Configuration

### Secrets Manager Structure

Your secrets should include:

```json
{
  "SMTP_USER": "your-email@gmail.com",
  "SMTP_PASSWORD": "your-gmail-app-password",
  "SMTP_RECIPIENTS": "notify1@example.com,notify2@example.com",
  "EMAIL_ENABLED": "true",

  "FTP_PASS_SUPPLIER1": "password",
  "FTP_USER_SUPPLIER1": "username",
  "FTP_HOST_SUPPLIER1": "ftp.supplier1.com",

  "FTP_PASS_PLATFORM1": "password",
  "FTP_USER_PLATFORM1": "username",
  "FTP_HOST_PLATFORM1": "ftp.platform1.com"
}
```

### Environment Variables (CodeBuild)

| Variable           | Default | Description                         |
| ------------------ | ------- | ----------------------------------- |
| `DRY_RUN_UPLOAD`   | `false` | Skip actual FTP uploads when `true` |
| `NO_EMAIL`         | `false` | Skip email reports when `true`      |
| `SUPPLIERS`        | (empty) | Comma-separated supplier list       |
| `PLATFORMS`        | (empty) | Comma-separated platform list       |
| `S3_BACKUP_BUCKET` | (auto)  | S3 bucket for backups               |

## 📊 Monitoring and Logs

### CloudWatch Logs

Access logs at: `/aws/codebuild/automation-stock-update-build`

### Build Artifacts

Stored in S3: `automation-stock-update-artifacts-{account-id}/`

### Key Metrics to Monitor

- Build success rate
- Execution duration
- FTP connection failures
- Email delivery status
- File processing counts

## 🛠️ Troubleshooting

### Common Issues

#### 1. Build Fails Immediately

```bash
# Check IAM permissions
python deploy/validate-deployment.py

# Review secrets configuration
python deploy/update-secrets.py --interactive
```

#### 2. FTP Connection Errors

```bash
# Test individual builds with specific suppliers
python deploy/test-build.py --start --dry-run
# Then check CloudWatch logs
```

#### 3. Email Not Sent

- Verify Gmail app password (not regular password)
- Check `EMAIL_ENABLED` is `"true"` in secrets
- Ensure SMTP settings are correct

#### 4. Schedule Not Triggering

```bash
# Check rule status
python deploy/schedule-management.py --status

# Enable if disabled
python deploy/schedule-management.py --enable

# Validate cron expression
python deploy/schedule-management.py --validate "cron(0 6 * * MON-FRI *)"
```

### Debug Commands

```bash
# Full validation with build test
python deploy/validate-deployment.py --test-build --report debug-report.json

# Check recent invocations
python deploy/schedule-management.py --invocations

# Monitor build in real-time
python deploy/test-build.py --start --dry-run
# Copy build ID from output, then:
python deploy/test-build.py --monitor <build-id>
```

## 🔄 Going from Test to Production

### Step 1: Test Everything

```bash
# 1. Validate deployment
python deploy/validate-deployment.py --test-build

# 2. Run test with dry-run enabled
python deploy/test-build.py --start --dry-run --no-email

# 3. Check results and logs
python deploy/test-build.py --recent
```

### Step 2: Enable Email Notifications

```bash
# Update secrets to enable email
python deploy/update-secrets.py --interactive
# Set EMAIL_ENABLED to "true"
```

### Step 3: Enable Real FTP Uploads

```bash
# Test with real uploads (but no email)
python deploy/test-build.py --start --no-dry-run --no-email

# Check results carefully
python deploy/test-build.py --recent
```

### Step 4: Go Fully Live

```bash
# Enable the schedule
python deploy/schedule-management.py --enable

# Test with full functionality
python deploy/test-build.py --start --no-dry-run

# Monitor first scheduled run
python deploy/schedule-management.py --status
```

## 📈 Optimization Tips

### Performance

- Use `BUILD_GENERAL1_MEDIUM` for most workloads
- Consider parallel processing for large supplier lists
- Monitor execution times and adjust timeout if needed

### Cost Optimization

- Schedule only when needed (weekdays vs. daily)
- Clean up old artifacts automatically
- Use appropriate build instance size

### Reliability

- Set up CloudWatch alarms for build failures
- Monitor FTP connection success rates
- Test with individual suppliers if issues arise

## 🔗 Additional Resources

- [AWS CodeBuild Documentation](https://docs.aws.amazon.com/codebuild/)
- [EventBridge Cron Expressions](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-cron-expressions.html)
- [Gmail App Password Setup](https://support.google.com/accounts/answer/185833)
- [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/)

## 📞 Support

For issues:

1. Run validation: `python deploy/validate-deployment.py`
2. Check CloudWatch logs
3. Test individual components
4. Review this documentation
5. Check AWS service health status
