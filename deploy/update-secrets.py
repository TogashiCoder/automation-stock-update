#!/usr/bin/env python3
"""
Script to update AWS Secrets Manager with FTP credentials and email settings
"""

import json
import boto3
import sys
import argparse
from pathlib import Path

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

def update_secrets(secrets_arn, secrets_data, region):
    """Update Secrets Manager secret"""
    try:
        client = boto3.client('secretsmanager', region_name=region)
        client.update_secret(
            SecretId=secrets_arn,
            SecretString=json.dumps(secrets_data, indent=2)
        )
        print(f"✅ Successfully updated secrets in {secrets_arn}")
    except Exception as e:
        print(f"❌ Error updating secrets: {e}")
        sys.exit(1)

def load_secrets_template():
    """Load secrets template with placeholders"""
    return {
        "SMTP_USER": "your-smtp-email@gmail.com",
        "SMTP_PASSWORD": "your-gmail-app-password",
        "SMTP_RECIPIENTS": "notification@example.com,admin@example.com",
        "EMAIL_ENABLED": "true",
        
        # Supplier FTP credentials - add all your suppliers here
        "FTP_PASS_ABAKUS": "supplier-password",
        "FTP_USER_ABAKUS": "supplier-username",
        "FTP_HOST_ABAKUS": "ftp.supplier.com",
        
        "FTP_PASS_AIRSTAL": "supplier-password",
        "FTP_USER_AIRSTAL": "supplier-username", 
        "FTP_HOST_AIRSTAL": "ftp.supplier.com",
        
        "FTP_PASS_AS_PL": "supplier-password",
        "FTP_USER_AS_PL": "supplier-username",
        "FTP_HOST_AS_PL": "ftp.supplier.com",
        
        "FTP_PASS_EMINIA_TRADING": "supplier-password",
        "FTP_USER_EMINIA_TRADING": "supplier-username",
        "FTP_HOST_EMINIA_TRADING": "ftp.supplier.com",
        
        "FTP_PASS_JPGROUP": "supplier-password",
        "FTP_USER_JPGROUP": "supplier-username",
        "FTP_HOST_JPGROUP": "ftp.supplier.com",
        
        "FTP_PASS_NTY": "supplier-password",
        "FTP_USER_NTY": "supplier-username",
        "FTP_HOST_NTY": "ftp.supplier.com",
        
        "FTP_PASS_SKV": "supplier-password",
        "FTP_USER_SKV": "supplier-username",
        "FTP_HOST_SKV": "ftp.supplier.com",
        
        "FTP_PASS_STORM": "supplier-password",
        "FTP_USER_STORM": "supplier-username",
        "FTP_HOST_STORM": "ftp.supplier.com",
        
        # Platform FTP credentials
        "FTP_PASS_07": "platform-password",
        "FTP_USER_07": "platform-username",
        "FTP_HOST_07": "ftp.platform.com",
        
        "FTP_PASS_ALZURA": "platform-password",
        "FTP_USER_ALZURA": "platform-username",
        "FTP_HOST_ALZURA": "ftp.platform.com",
        
        "FTP_PASS_DEPARTO": "platform-password",
        "FTP_USER_DEPARTO": "platform-username",
        "FTP_HOST_DEPARTO": "ftp.platform.com",
        
        "FTP_PASS_DROX_AUTO": "platform-password",
        "FTP_USER_DROX_AUTO": "platform-username", 
        "FTP_HOST_DROX_AUTO": "ftp.platform.com",
        
        "FTP_PASS_MARKET_DE_NEW": "platform-password",
        "FTP_USER_MARKET_DE_NEW": "platform-username",
        "FTP_HOST_MARKET_DE_NEW": "ftp.platform.com",
        
        "FTP_PASS_PRIMETURBO": "platform-password",
        "FTP_USER_PRIMETURBO": "platform-username",
        "FTP_HOST_PRIMETURBO": "ftp.platform.com",
        
        "FTP_PASS_TIELEHABERDER": "platform-password",
        "FTP_USER_TIELEHABERDER": "platform-username",
        "FTP_HOST_TIELEHABERDER": "ftp.platform.com"
    }

def interactive_update():
    """Interactive mode to update specific credentials"""
    secrets = load_secrets_template()
    
    print("\n🔧 Interactive Secrets Update")
    print("=" * 50)
    
    # Email settings
    print("\n📧 Email Configuration:")
    secrets["SMTP_USER"] = input(f"SMTP User [{secrets['SMTP_USER']}]: ") or secrets["SMTP_USER"]
    secrets["SMTP_PASSWORD"] = input(f"SMTP Password [{secrets['SMTP_PASSWORD']}]: ") or secrets["SMTP_PASSWORD"]
    secrets["SMTP_RECIPIENTS"] = input(f"Recipients [{secrets['SMTP_RECIPIENTS']}]: ") or secrets["SMTP_RECIPIENTS"]
    
    # FTP credentials
    print("\n🔌 FTP Credentials:")
    print("Enter credentials for each system (press Enter to skip):")
    
    # Group credentials by system
    systems = {}
    for key in secrets.keys():
        if key.startswith('FTP_'):
            parts = key.split('_')
            if len(parts) >= 3:
                system = '_'.join(parts[2:])
                if system not in systems:
                    systems[system] = {}
                systems[system][parts[1]] = key
    
    for system, creds in systems.items():
        print(f"\n🏢 {system}:")
        for cred_type, env_key in creds.items():
            current_value = secrets.get(env_key, "")
            if cred_type == 'PASS':
                new_value = input(f"  Password [{current_value}]: ")
            elif cred_type == 'USER':
                new_value = input(f"  Username [{current_value}]: ")
            elif cred_type == 'HOST':
                new_value = input(f"  Host [{current_value}]: ")
            else:
                new_value = input(f"  {cred_type} [{current_value}]: ")
            
            if new_value:
                secrets[env_key] = new_value
    
    return secrets

def main():
    parser = argparse.ArgumentParser(description='Update AWS Secrets Manager for stock automation')
    parser.add_argument('--stack-name', default='automation-stock-update', help='CloudFormation stack name')
    parser.add_argument('--region', default='eu-north-1', help='AWS region')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode')
    parser.add_argument('--secrets-file', help='Load secrets from JSON file')
    parser.add_argument('--template-only', action='store_true', help='Generate template file only')
    
    args = parser.parse_args()
    
    # Generate template file if requested
    if args.template_only:
        template = load_secrets_template()
        template_file = Path("secrets-template.json")
        with open(template_file, 'w') as f:
            json.dump(template, f, indent=2)
        print(f"✅ Template saved to {template_file}")
        print("Edit this file with your credentials and run:")
        print(f"python {sys.argv[0]} --secrets-file {template_file}")
        return
    
    # Get stack outputs
    print(f"🔍 Getting stack outputs for {args.stack_name} in {args.region}...")
    outputs = get_stack_outputs(args.stack_name, args.region)
    secrets_arn = outputs.get('SecretsManagerArn')
    
    if not secrets_arn:
        print("❌ Could not find SecretsManagerArn in stack outputs")
        sys.exit(1)
    
    print(f"📋 Found secrets: {secrets_arn}")
    
    # Load secrets data
    if args.secrets_file:
        print(f"📄 Loading secrets from {args.secrets_file}")
        with open(args.secrets_file) as f:
            secrets_data = json.load(f)
    elif args.interactive:
        secrets_data = interactive_update()
    else:
        print("❌ Please specify --interactive or --secrets-file")
        sys.exit(1)
    
    # Update secrets
    print(f"🔐 Updating secrets in AWS...")
    update_secrets(secrets_arn, secrets_data, args.region)
    
    print("\n🎉 Secrets updated successfully!")
    print("\n💡 Next steps:")
    print("1. Test your CodeBuild project manually")
    print("2. Check the first scheduled run")
    print("3. Monitor CloudWatch logs")

if __name__ == '__main__':
    main()
