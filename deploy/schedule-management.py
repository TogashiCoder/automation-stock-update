#!/usr/bin/env python3
"""
Script to manage EventBridge scheduling for the stock update automation
"""

import boto3
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

def get_rule_status(rule_name, region):
    """Get EventBridge rule status"""
    try:
        client = boto3.client('events', region_name=region)
        response = client.describe_rule(Name=rule_name)
        return response
    except Exception as e:
        print(f"❌ Error getting rule status: {e}")
        return None

def enable_rule(rule_name, region):
    """Enable EventBridge rule"""
    try:
        client = boto3.client('events', region_name=region)
        client.enable_rule(Name=rule_name)
        print(f"✅ Enabled rule: {rule_name}")
        return True
    except Exception as e:
        print(f"❌ Error enabling rule: {e}")
        return False

def disable_rule(rule_name, region):
    """Disable EventBridge rule"""
    try:
        client = boto3.client('events', region_name=region)
        client.disable_rule(Name=rule_name)
        print(f"🛑 Disabled rule: {rule_name}")
        return True
    except Exception as e:
        print(f"❌ Error disabling rule: {e}")
        return False

def update_schedule(rule_name, region, new_schedule):
    """Update EventBridge rule schedule"""
    try:
        client = boto3.client('events', region_name=region)
        
        # Get current rule configuration
        current_rule = client.describe_rule(Name=rule_name)
        
        # Update schedule
        client.put_rule(
            Name=rule_name,
            ScheduleExpression=new_schedule,
            Description=current_rule['Description'],
            State=current_rule['State']
        )
        
        print(f"📅 Updated schedule for {rule_name}: {new_schedule}")
        return True
    except Exception as e:
        print(f"❌ Error updating schedule: {e}")
        return False

def list_recent_invocations(rule_name, region, hours=24):
    """List recent rule invocations"""
    try:
        # Get CloudWatch events for the rule
        cloudwatch = boto3.client('cloudwatch', region_name=region)
        
        from datetime import datetime, timedelta
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        response = cloudwatch.get_metric_statistics(
            Namespace='AWS/Events',
            MetricName='InvocationsCount',
            Dimensions=[
                {
                    'Name': 'RuleName',
                    'Value': rule_name
                }
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=3600,  # 1 hour periods
            Statistics=['Sum']
        )
        
        print(f"\n📊 Invocations in last {hours} hours:")
        if response['Datapoints']:
            for datapoint in sorted(response['Datapoints'], key=lambda x: x['Timestamp']):
                timestamp = datapoint['Timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                count = int(datapoint['Sum'])
                print(f"   {timestamp}: {count} invocations")
        else:
            print("   No invocations found")
            
    except Exception as e:
        print(f"❌ Error getting invocation metrics: {e}")

def get_next_execution_times(schedule_expression, count=5):
    """Calculate next execution times for a cron expression"""
    try:
        from croniter import croniter
        from datetime import datetime
        
        # Remove 'cron(' prefix and ')' suffix if present
        if schedule_expression.startswith('cron('):
            cron_expr = schedule_expression[5:-1]
        else:
            cron_expr = schedule_expression
        
        base = datetime.utcnow()
        cron = croniter(cron_expr, base)
        
        print(f"\n⏰ Next {count} execution times (UTC):")
        for i in range(count):
            next_time = cron.get_next(datetime)
            print(f"   {next_time.strftime('%Y-%m-%d %H:%M:%S')} ({next_time.strftime('%A')})")
            
    except ImportError:
        print("❌ croniter package not installed. Install with: pip install croniter")
    except Exception as e:
        print(f"❌ Error calculating next execution times: {e}")

def validate_cron_expression(expression):
    """Validate a cron expression"""
    try:
        from croniter import croniter
        
        # Remove 'cron(' prefix and ')' suffix if present
        if expression.startswith('cron('):
            cron_expr = expression[5:-1]
        else:
            cron_expr = expression
        
        # Test if the expression is valid
        base = datetime.utcnow()
        cron = croniter(cron_expr, base)
        next_time = cron.get_next(datetime)
        
        print(f"✅ Valid cron expression: {expression}")
        print(f"   Next execution: {next_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        return True
        
    except ImportError:
        print("❌ croniter package not installed. Install with: pip install croniter")
        return False
    except Exception as e:
        print(f"❌ Invalid cron expression: {e}")
        return False

def show_common_schedules():
    """Show common schedule examples"""
    schedules = [
        ("Daily at 6 AM UTC", "cron(0 6 * * ? *)"),
        ("Weekdays at 6 AM UTC", "cron(0 6 ? * MON-FRI *)"),
        ("Mon-Sat at 6 AM UTC", "cron(0 6 ? * MON-SAT *)"),
        ("France 7 AM (6 AM UTC)", "cron(0 6 ? * MON-SAT *)"),
        ("France 5 PM (4 PM UTC)", "cron(0 16 ? * MON-SAT *)"),
        ("Every 2 hours", "cron(0 */2 * * ? *)"),
        ("Twice daily (6 AM, 6 PM)", "cron(0 6,18 * * ? *)"),
        ("Weekly on Monday at 6 AM", "cron(0 6 ? * MON *)"),
        ("Monthly on 1st at 6 AM", "cron(0 6 1 * ? *)"),
        ("Every 30 minutes", "cron(*/30 * * * ? *)"),
    ]
    
    print("\n📋 Common Schedule Examples:")
    print("-" * 70)
    for description, expression in schedules:
        print(f"   {description:<30} {expression}")
    
    print("\n💡 Note: France time schedules assume winter time (UTC+1)")
    print("   During summer time (UTC+2), adjust by -1 hour")
    print("   Current schedule: Monday through Saturday (6 days/week)")

def main():
    parser = argparse.ArgumentParser(description='Manage EventBridge scheduling')
    parser.add_argument('--stack-name', default='automation-stock-update', help='CloudFormation stack name')
    parser.add_argument('--region', default='eu-north-1', help='AWS region')
    
    # Actions
    parser.add_argument('--status', action='store_true', help='Show rule status')
    parser.add_argument('--enable', action='store_true', help='Enable the rule')
    parser.add_argument('--disable', action='store_true', help='Disable the rule')
    parser.add_argument('--schedule', help='Update schedule (cron expression)')
    parser.add_argument('--validate', help='Validate cron expression')
    parser.add_argument('--invocations', action='store_true', help='Show recent invocations')
    parser.add_argument('--next', type=int, default=5, help='Show next N execution times')
    parser.add_argument('--examples', action='store_true', help='Show common schedule examples')
    
    args = parser.parse_args()
    
    if args.examples:
        show_common_schedules()
        return
    
    if args.validate:
        validate_cron_expression(args.validate)
        return
    
    # Get stack outputs
    print(f"🔍 Getting stack outputs for {args.stack_name} in {args.region}...")
    outputs = get_stack_outputs(args.stack_name, args.region)
    
    # Handle both old single rule and new dual rule configurations
    morning_rule = outputs.get('MorningEventBridgeRuleName')
    afternoon_rule = outputs.get('AfternoonEventBridgeRuleName')
    old_rule = outputs.get('EventBridgeRuleName')
    
    if morning_rule and afternoon_rule:
        rule_names = [morning_rule, afternoon_rule]
        rule_types = ['Morning', 'Afternoon']
        print(f"📋 Found dual schedule rules:")
        print(f"   Morning: {morning_rule}")
        print(f"   Afternoon: {afternoon_rule}")
    elif old_rule:
        rule_names = [old_rule]
        rule_types = ['Single']
        print(f"📋 Found single rule: {old_rule}")
    else:
        print("❌ Could not find EventBridge rule names in stack outputs")
        sys.exit(1)
    
    # Get current status for all rules
    rule_infos = []
    for rule_name in rule_names:
        rule_info = get_rule_status(rule_name, args.region)
        if not rule_info:
            print(f"❌ Could not get status for rule: {rule_name}")
            continue
        rule_infos.append(rule_info)
    
    if args.status or not any([args.enable, args.disable, args.schedule, args.invocations]):
        print(f"\n📊 Rule Status:")
        for i, (rule_info, rule_type) in enumerate(zip(rule_infos, rule_types)):
            print(f"\n   {rule_type} Rule:")
            print(f"     Name: {rule_info['Name']}")
            print(f"     State: {rule_info['State']}")
            print(f"     Schedule: {rule_info.get('ScheduleExpression', 'N/A')}")
            print(f"     Description: {rule_info.get('Description', 'N/A')}")
            
            # Show next execution times for each rule
            if 'ScheduleExpression' in rule_info:
                print(f"\n   Next {args.next} execution times for {rule_type} rule:")
                get_next_execution_times(rule_info['ScheduleExpression'], args.next)
    
    if args.enable:
        for rule_name in rule_names:
            enable_rule(rule_name, args.region)
    
    elif args.disable:
        for rule_name in rule_names:
            disable_rule(rule_name, args.region)
    
    elif args.schedule:
        if len(rule_names) > 1:
            print("❌ Schedule update for multiple rules is not supported via command line.")
            print("   Please update individual rules using AWS Console or specify which rule to update.")
            print("   Consider updating the CloudFormation template parameters instead.")
        else:
            if validate_cron_expression(args.schedule):
                update_schedule(rule_names[0], args.region, args.schedule)
    
    if args.invocations:
        for rule_name in rule_names:
            list_recent_invocations(rule_name, args.region)

if __name__ == '__main__':
    main()
