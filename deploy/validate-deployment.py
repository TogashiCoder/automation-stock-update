#!/usr/bin/env python3
"""
Complete validation script for the stock update automation deployment
"""

import boto3
import json
import sys
import argparse
import time
from pathlib import Path
from datetime import datetime, timedelta

class DeploymentValidator:
    def __init__(self, stack_name, region):
        self.stack_name = stack_name
        self.region = region
        self.cf_client = boto3.client('cloudformation', region_name=region)
        self.cb_client = boto3.client('codebuild', region_name=region)
        self.events_client = boto3.client('events', region_name=region)
        self.s3_client = boto3.client('s3', region_name=region)
        self.secrets_client = boto3.client('secretsmanager', region_name=region)
        self.cw_client = boto3.client('cloudwatch', region_name=region)
        
        self.outputs = {}
        self.validation_results = []
    
    def log_result(self, test_name, success, message="", details=None):
        """Log validation result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if message:
            print(f"    {message}")
        if details:
            print(f"    Details: {details}")
        
        self.validation_results.append({
            'test': test_name,
            'success': success,
            'message': message,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
    
    def get_stack_outputs(self):
        """Get CloudFormation stack outputs"""
        try:
            response = self.cf_client.describe_stacks(StackName=self.stack_name)
            stack = response['Stacks'][0]
            
            # Check stack status
            stack_status = stack['StackStatus']
            if 'COMPLETE' in stack_status:
                self.log_result("Stack Status", True, f"Status: {stack_status}")
            else:
                self.log_result("Stack Status", False, f"Status: {stack_status}")
                return False
            
            # Extract outputs
            if 'Outputs' in stack:
                for output in stack['Outputs']:
                    self.outputs[output['OutputKey']] = output['OutputValue']
                self.log_result("Stack Outputs", True, f"Found {len(self.outputs)} outputs")
            else:
                self.log_result("Stack Outputs", False, "No outputs found")
                return False
            
            return True
            
        except Exception as e:
            self.log_result("Stack Status", False, f"Error: {e}")
            return False
    
    def validate_iam_roles(self):
        """Validate IAM roles exist and have correct permissions"""
        try:
            iam_client = boto3.client('iam', region_name=self.region)
            
            # Check CodeBuild role
            try:
                role_name = f"{self.stack_name}-codebuild-role"
                iam_client.get_role(RoleName=role_name)
                self.log_result("CodeBuild IAM Role", True, f"Role exists: {role_name}")
            except Exception as e:
                self.log_result("CodeBuild IAM Role", False, f"Role not found: {e}")
            
            # Check EventBridge role
            try:
                role_name = f"{self.stack_name}-eventbridge-role"
                iam_client.get_role(RoleName=role_name)
                self.log_result("EventBridge IAM Role", True, f"Role exists: {role_name}")
            except Exception as e:
                self.log_result("EventBridge IAM Role", False, f"Role not found: {e}")
                
        except Exception as e:
            self.log_result("IAM Validation", False, f"Error checking IAM roles: {e}")
    
    def validate_s3_bucket(self):
        """Validate S3 bucket exists and is accessible"""
        bucket_name = self.outputs.get('ArtifactsBucketName')
        if not bucket_name:
            self.log_result("S3 Bucket", False, "Bucket name not found in outputs")
            return
        
        try:
            # Check bucket exists
            self.s3_client.head_bucket(Bucket=bucket_name)
            self.log_result("S3 Bucket Existence", True, f"Bucket exists: {bucket_name}")
            
            # Check bucket permissions
            try:
                self.s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
                self.log_result("S3 Bucket Access", True, "Can list objects")
            except Exception as e:
                self.log_result("S3 Bucket Access", False, f"Cannot list objects: {e}")
            
        except Exception as e:
            self.log_result("S3 Bucket", False, f"Error: {e}")
    
    def validate_secrets_manager(self):
        """Validate Secrets Manager secret exists and is accessible"""
        secret_arn = self.outputs.get('SecretsManagerArn')
        if not secret_arn:
            self.log_result("Secrets Manager", False, "Secret ARN not found in outputs")
            return
        
        try:
            # Check secret exists
            response = self.secrets_client.describe_secret(SecretId=secret_arn)
            self.log_result("Secrets Manager Existence", True, f"Secret exists: {response['Name']}")
            
            # Try to read secret value
            try:
                secret_response = self.secrets_client.get_secret_value(SecretId=secret_arn)
                secret_data = json.loads(secret_response['SecretString'])
                
                # Check for required keys
                required_keys = ['SMTP_USER', 'SMTP_PASSWORD', 'SMTP_RECIPIENTS']
                missing_keys = [key for key in required_keys if key not in secret_data]
                
                if missing_keys:
                    self.log_result("Secrets Content", False, f"Missing required keys: {missing_keys}")
                else:
                    self.log_result("Secrets Content", True, "All required email keys present")
                
                # Check FTP credentials
                ftp_keys = [key for key in secret_data.keys() if key.startswith('FTP_')]
                if ftp_keys:
                    self.log_result("FTP Credentials", True, f"Found {len(ftp_keys)} FTP credential entries")
                else:
                    self.log_result("FTP Credentials", False, "No FTP credentials found")
                
            except Exception as e:
                self.log_result("Secrets Access", False, f"Cannot read secret: {e}")
                
        except Exception as e:
            self.log_result("Secrets Manager", False, f"Error: {e}")
    
    def validate_codebuild_project(self):
        """Validate CodeBuild project configuration"""
        project_name = self.outputs.get('CodeBuildProjectName')
        if not project_name:
            self.log_result("CodeBuild Project", False, "Project name not found in outputs")
            return
        
        try:
            response = self.cb_client.batch_get_projects(names=[project_name])
            if not response['projects']:
                self.log_result("CodeBuild Project", False, "Project not found")
                return
            
            project = response['projects'][0]
            self.log_result("CodeBuild Project Existence", True, f"Project exists: {project_name}")
            
            # Check project configuration
            source = project.get('source', {})
            if source.get('type') == 'GITHUB':
                self.log_result("CodeBuild Source", True, f"GitHub source: {source.get('location', 'N/A')}")
            else:
                self.log_result("CodeBuild Source", False, f"Unexpected source type: {source.get('type')}")
            
            # Check environment
            environment = project.get('environment', {})
            if environment.get('type') == 'LINUX_CONTAINER':
                self.log_result("CodeBuild Environment", True, f"Linux container: {environment.get('image', 'N/A')}")
            else:
                self.log_result("CodeBuild Environment", False, f"Unexpected environment: {environment.get('type')}")
                
        except Exception as e:
            self.log_result("CodeBuild Project", False, f"Error: {e}")
    
    def validate_eventbridge_rule(self):
        """Validate EventBridge rule configuration"""
        rule_name = self.outputs.get('EventBridgeRuleName')
        if not rule_name:
            self.log_result("EventBridge Rule", False, "Rule name not found in outputs")
            return
        
        try:
            response = self.events_client.describe_rule(Name=rule_name)
            self.log_result("EventBridge Rule Existence", True, f"Rule exists: {rule_name}")
            
            # Check rule state
            state = response.get('State')
            if state == 'ENABLED':
                self.log_result("EventBridge Rule State", True, "Rule is enabled")
            else:
                self.log_result("EventBridge Rule State", False, f"Rule state: {state}")
            
            # Check schedule
            schedule = response.get('ScheduleExpression', '')
            if schedule:
                self.log_result("EventBridge Schedule", True, f"Schedule: {schedule}")
            else:
                self.log_result("EventBridge Schedule", False, "No schedule expression found")
            
            # Check targets
            try:
                targets_response = self.events_client.list_targets_by_rule(Rule=rule_name)
                targets = targets_response.get('Targets', [])
                if targets:
                    self.log_result("EventBridge Targets", True, f"Found {len(targets)} targets")
                else:
                    self.log_result("EventBridge Targets", False, "No targets configured")
            except Exception as e:
                self.log_result("EventBridge Targets", False, f"Error checking targets: {e}")
                
        except Exception as e:
            self.log_result("EventBridge Rule", False, f"Error: {e}")
    
    def validate_cloudwatch_logs(self):
        """Validate CloudWatch log groups exist"""
        try:
            log_group_name = f"/aws/codebuild/{self.stack_name}-build"
            
            response = self.cw_client.describe_log_groups(
                logGroupNamePrefix=log_group_name
            )
            
            log_groups = response.get('logGroups', [])
            found = any(lg['logGroupName'] == log_group_name for lg in log_groups)
            
            if found:
                self.log_result("CloudWatch Log Group", True, f"Log group exists: {log_group_name}")
            else:
                self.log_result("CloudWatch Log Group", False, f"Log group not found: {log_group_name}")
                
        except Exception as e:
            self.log_result("CloudWatch Logs", False, f"Error: {e}")
    
    def test_build_execution(self, dry_run=True):
        """Test actual build execution"""
        project_name = self.outputs.get('CodeBuildProjectName')
        if not project_name:
            self.log_result("Build Test", False, "Cannot test build - project name not found")
            return
        
        try:
            print(f"\n🧪 Starting test build (dry_run={dry_run})...")
            
            env_overrides = [
                {'name': 'DRY_RUN_UPLOAD', 'value': 'true' if dry_run else 'false'},
                {'name': 'NO_EMAIL', 'value': 'true'},  # Always skip email in tests
                {'name': 'TRIGGER_SOURCE', 'value': 'Validation Test'}
            ]
            
            response = self.cb_client.start_build(
                projectName=project_name,
                environmentVariablesOverride=env_overrides
            )
            
            build_id = response['build']['id']
            print(f"   Build started: {build_id}")
            
            # Monitor build (timeout after 10 minutes)
            start_time = time.time()
            timeout = 600  # 10 minutes
            
            while time.time() - start_time < timeout:
                build_response = self.cb_client.batch_get_builds(ids=[build_id])
                build = build_response['builds'][0]
                
                status = build['buildStatus']
                phase = build.get('currentPhase', 'UNKNOWN')
                
                print(f"   Status: {status}, Phase: {phase}")
                
                if status in ['SUCCEEDED', 'FAILED', 'FAULT', 'STOPPED', 'TIMED_OUT']:
                    break
                
                time.sleep(15)  # Check every 15 seconds
            
            # Final result
            if status == 'SUCCEEDED':
                self.log_result("Build Execution Test", True, f"Build completed successfully: {build_id}")
            else:
                self.log_result("Build Execution Test", False, f"Build failed with status: {status}")
            
            return status == 'SUCCEEDED'
            
        except Exception as e:
            self.log_result("Build Execution Test", False, f"Error: {e}")
            return False
    
    def run_full_validation(self, include_build_test=False):
        """Run complete validation suite"""
        print(f"🔍 Validating deployment: {self.stack_name} in {self.region}")
        print("=" * 60)
        
        # Core infrastructure validation
        if not self.get_stack_outputs():
            return False
        
        self.validate_iam_roles()
        self.validate_s3_bucket()
        self.validate_secrets_manager()
        self.validate_codebuild_project()
        self.validate_eventbridge_rule()
        self.validate_cloudwatch_logs()
        
        # Optional build test
        if include_build_test:
            self.test_build_execution(dry_run=True)
        
        # Summary
        total_tests = len(self.validation_results)
        passed_tests = sum(1 for result in self.validation_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print("\n" + "=" * 60)
        print(f"📊 Validation Summary:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests}")
        print(f"   Failed: {failed_tests}")
        
        if failed_tests == 0:
            print("\n🎉 All validations passed! Your deployment is ready.")
            return True
        else:
            print(f"\n❌ {failed_tests} validation(s) failed. Please review and fix the issues.")
            return False
    
    def save_validation_report(self, output_file):
        """Save validation results to file"""
        report = {
            'stack_name': self.stack_name,
            'region': self.region,
            'validation_timestamp': datetime.now().isoformat(),
            'outputs': self.outputs,
            'results': self.validation_results,
            'summary': {
                'total_tests': len(self.validation_results),
                'passed': sum(1 for r in self.validation_results if r['success']),
                'failed': sum(1 for r in self.validation_results if not r['success'])
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📄 Validation report saved to: {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Validate stock automation deployment')
    parser.add_argument('--stack-name', default='automation-stock-update', help='CloudFormation stack name')
    parser.add_argument('--region', default='eu-north-1', help='AWS region')
    parser.add_argument('--test-build', action='store_true', help='Include actual build test')
    parser.add_argument('--report', help='Save validation report to file')
    
    args = parser.parse_args()
    
    validator = DeploymentValidator(args.stack_name, args.region)
    success = validator.run_full_validation(include_build_test=args.test_build)
    
    if args.report:
        validator.save_validation_report(args.report)
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
