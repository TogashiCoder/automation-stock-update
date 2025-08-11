#!/usr/bin/env python3
"""
Script to test the CodeBuild project and monitor execution
"""

import boto3
import time
import sys
import argparse
import json
from datetime import datetime

def get_stack_outputs(stack_name, region):
    """Get CloudFormation stack outputs"""
    try:
        cf = boto3.client('cloudformation', region_name=region)
        response = cf.describe_stacks(StackName=stack_name)
        outputs = response['Stacks'][0]['Outputs']
        return {output['OutputKey']: output['OutputValue'] for output in outputs}
    except Exception as e:
        print(f"❌ Error getting stack outputs: {e}")
        sys.exit(1)

def start_build(project_name, region, dry_run=True, no_email=False):
    """Start a CodeBuild execution"""
    try:
        client = boto3.client('codebuild', region_name=region)
        
        # Environment variable overrides
        env_overrides = [
            {
                'name': 'DRY_RUN_UPLOAD',
                'value': 'true' if dry_run else 'false'
            },
            {
                'name': 'NO_EMAIL', 
                'value': 'true' if no_email else 'false'
            },
            {
                'name': 'TRIGGER_SOURCE',
                'value': 'Manual Test'
            },
            {
                'name': 'TRIGGER_TIME',
                'value': datetime.now().isoformat()
            }
        ]
        
        response = client.start_build(
            projectName=project_name,
            environmentVariablesOverride=env_overrides
        )
        
        build_id = response['build']['id']
        print(f"🚀 Started build: {build_id}")
        return build_id
        
    except Exception as e:
        print(f"❌ Error starting build: {e}")
        sys.exit(1)

def monitor_build(build_id, region):
    """Monitor build execution"""
    client = boto3.client('codebuild', region_name=region)
    
    print(f"⏳ Monitoring build {build_id}...")
    
    while True:
        try:
            response = client.batch_get_builds(ids=[build_id])
            build = response['builds'][0]
            
            status = build['buildStatus']
            phase = build.get('currentPhase', 'UNKNOWN')
            
            print(f"📊 Status: {status}, Phase: {phase}")
            
            if status in ['SUCCEEDED', 'FAILED', 'FAULT', 'STOPPED', 'TIMED_OUT']:
                break
                
            time.sleep(30)  # Check every 30 seconds
            
        except Exception as e:
            print(f"❌ Error monitoring build: {e}")
            break
    
    # Final status
    print(f"\n🏁 Build completed with status: {status}")
    
    # Show build details
    if 'logs' in build and 'groupName' in build['logs']:
        log_group = build['logs']['groupName']
        log_stream = build['logs']['streamName']
        print(f"📋 Logs: {log_group}/{log_stream}")
        
        # Get CloudWatch logs URL
        region_name = region
        logs_url = f"https://{region_name}.console.aws.amazon.com/cloudwatch/home?region={region_name}#logsV2:log-groups/log-group/{log_group.replace('/', '%2F')}/log-events/{log_stream.replace('/', '%2F')}"
        print(f"🔗 CloudWatch Logs: {logs_url}")
    
    # Show artifacts
    if 'artifacts' in build and 'location' in build['artifacts']:
        artifacts_location = build['artifacts']['location']
        print(f"📦 Artifacts: {artifacts_location}")
    
    return status == 'SUCCEEDED'

def get_recent_builds(project_name, region, limit=5):
    """Get recent builds for the project"""
    try:
        client = boto3.client('codebuild', region_name=region)
        response = client.list_builds_for_project(
            projectName=project_name,
            sortOrder='DESCENDING'
        )
        
        if not response['ids']:
            print("📭 No builds found")
            return
        
        # Get build details
        builds_response = client.batch_get_builds(
            ids=response['ids'][:limit]
        )
        
        print(f"\n📋 Recent {limit} builds:")
        print("-" * 80)
        
        for build in builds_response['builds']:
            build_id = build['id']
            status = build['buildStatus']
            start_time = build.get('startTime', 'Unknown')
            end_time = build.get('endTime', 'In Progress')
            
            if isinstance(start_time, datetime):
                start_time = start_time.strftime('%Y-%m-%d %H:%M:%S')
            if isinstance(end_time, datetime):
                end_time = end_time.strftime('%Y-%m-%d %H:%M:%S')
            
            duration = "Unknown"
            if 'startTime' in build and 'endTime' in build:
                duration = str(build['endTime'] - build['startTime'])
            
            print(f"🔹 {build_id}")
            print(f"   Status: {status}")
            print(f"   Started: {start_time}")
            print(f"   Ended: {end_time}")
            print(f"   Duration: {duration}")
            print()
            
    except Exception as e:
        print(f"❌ Error getting recent builds: {e}")

def main():
    parser = argparse.ArgumentParser(description='Test CodeBuild project')
    parser.add_argument('--stack-name', default='automation-stock-update', help='CloudFormation stack name')
    parser.add_argument('--region', default='eu-north-1', help='AWS region')
    parser.add_argument('--start', action='store_true', help='Start a new test build')
    parser.add_argument('--monitor', help='Monitor specific build ID')
    parser.add_argument('--recent', action='store_true', help='Show recent builds')
    parser.add_argument('--dry-run', action='store_true', default=True, help='Run in dry-run mode (default)')
    parser.add_argument('--no-dry-run', action='store_true', help='Disable dry-run mode')
    parser.add_argument('--no-email', action='store_true', help='Skip email sending')
    
    args = parser.parse_args()
    
    # Handle dry-run flag logic
    if args.no_dry_run:
        dry_run = False
    else:
        dry_run = args.dry_run
    
    # Get stack outputs
    print(f"🔍 Getting stack outputs for {args.stack_name} in {args.region}...")
    outputs = get_stack_outputs(args.stack_name, args.region)
    project_name = outputs.get('CodeBuildProjectName')
    
    if not project_name:
        print("❌ Could not find CodeBuildProjectName in stack outputs")
        sys.exit(1)
    
    print(f"📋 Found project: {project_name}")
    
    if args.recent:
        get_recent_builds(project_name, args.region)
    
    elif args.monitor:
        monitor_build(args.monitor, args.region)
    
    elif args.start:
        print(f"🧪 Starting test build...")
        print(f"   Dry Run: {'Yes' if dry_run else 'No'}")
        print(f"   Email: {'Disabled' if args.no_email else 'Enabled'}")
        
        build_id = start_build(project_name, args.region, dry_run, args.no_email)
        success = monitor_build(build_id, args.region)
        
        if success:
            print("\n🎉 Test build completed successfully!")
            print("\n💡 Next steps:")
            print("1. Check the artifacts in S3")
            print("2. Review the logs for any warnings")
            print("3. If everything looks good, disable dry-run mode")
            print("4. Test with actual FTP uploads")
        else:
            print("\n❌ Test build failed!")
            print("Check the CloudWatch logs for details")
            sys.exit(1)
    
    else:
        print("❓ Please specify an action: --start, --monitor <build-id>, or --recent")
        parser.print_help()

if __name__ == '__main__':
    main()
