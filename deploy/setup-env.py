#!/usr/bin/env python3
"""
Script to set up local development environment for testing
"""

import yaml
import json
import sys
import argparse
from pathlib import Path

def create_sample_configs():
    """Create sample configuration files for testing"""
    
    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)
    
    # Sample fournisseurs (suppliers) configuration
    fournisseurs_config = {
        "ABAKUS": {
            "host": "ftp.abakus.com",
            "username": "your_username",
            "password": "your_password"
        },
        "AIRSTAL": {
            "host": "ftp.airstal.com", 
            "username": "your_username",
            "password": "your_password"
        },
        "AS-PL": {
            "host": "ftp.as-pl.com",
            "username": "your_username", 
            "password": "your_password"
        },
        "eminia trading": {
            "host": "ftp.eminia.com",
            "username": "your_username",
            "password": "your_password"
        },
        "JPGROUP": {
            "host": "ftp.jpgroup.com",
            "username": "your_username",
            "password": "your_password"
        },
        "NTY": {
            "host": "ftp.nty.com", 
            "username": "your_username",
            "password": "your_password"
        },
        "SKV": {
            "host": "ftp.skv.com",
            "username": "your_username",
            "password": "your_password"
        },
        "STORM": {
            "host": "ftp.storm.com",
            "username": "your_username",
            "password": "your_password"
        }
    }
    
    # Sample plateformes (platforms) configuration
    plateformes_config = {
        "07": {
            "host": "ftp.platform07.com",
            "username": "your_username",
            "password": "your_password"
        },
        "Alzura": {
            "host": "ftp.alzura.com", 
            "username": "your_username",
            "password": "your_password"
        },
        "Departo": {
            "host": "ftp.departo.com",
            "username": "your_username",
            "password": "your_password"
        },
        "Drox_auto": {
            "host": "ftp.droxauto.com",
            "username": "your_username",
            "password": "your_password"
        },
        "Market-DE-NEW": {
            "host": "ftp.market-de.com",
            "username": "your_username",
            "password": "your_password"
        },
        "Primeturbo": {
            "host": "ftp.primeturbo.com",
            "username": "your_username",
            "password": "your_password"
        },
        "TIELEHABERDER": {
            "host": "ftp.tielehaberder.com",
            "username": "your_username", 
            "password": "your_password"
        }
    }
    
    # Notification settings
    notification_config = {
        "enabled": True,
        "smtp_user": "your-email@gmail.com",
        "smtp_password": "your-gmail-app-password",
        "recipients": ["notification@example.com"]
    }
    
    # AWS backup settings
    aws_backup_config = {
        "enabled": False,
        "bucket": "your-backup-bucket",
        "prefix": "backups/platforms",
        "region": "eu-north-1",
        "access_key_id": "",
        "secret_access_key": "",
        "session_token": "",
        "endpoint_url": ""
    }
    
    # Write configuration files
    configs = [
        ("fournisseurs_connexions.yaml", fournisseurs_config),
        ("plateformes_connexions.yaml", plateformes_config),
        ("notification_settings.yaml", notification_config),
        ("aws_backup.yaml", aws_backup_config)
    ]
    
    for filename, config in configs:
        config_path = config_dir / filename
        if not config_path.exists():
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(config, f, allow_unicode=True, default_flow_style=False)
            print(f"✅ Created {config_path}")
        else:
            print(f"⚠️  {config_path} already exists, skipping")

def create_directories():
    """Create required directories"""
    directories = [
        "logs",
        "fichiers_fournisseurs", 
        "fichiers_platforms",
        "UPDATED_FILES",
        "UPDATED_FILES/fichiers_platforms",
        "Verifier",
        "backup"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"📁 Created directory: {directory}")

def create_env_template():
    """Create .env template file"""
    env_template = '''# Stock Update Automation Environment Variables
# Copy this file to .env and fill in your actual values

# Email Configuration (Gmail)
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-gmail-app-password
SMTP_RECIPIENTS=notification@example.com,admin@example.com
EMAIL_ENABLED=true

# AWS Configuration (optional - prefer IAM roles in production)
AWS_REGION=eu-north-1
S3_BACKUP_BUCKET=your-backup-bucket

# Execution Control
DRY_RUN_UPLOAD=true
NO_EMAIL=false
SUPPLIERS=
PLATFORMS=

# FTP Credentials for Suppliers
# Format: FTP_{PASS|USER|HOST}_<SUPPLIER_NAME>
FTP_PASS_ABAKUS=supplier_password
FTP_USER_ABAKUS=supplier_username
FTP_HOST_ABAKUS=ftp.supplier.com

FTP_PASS_AIRSTAL=supplier_password
FTP_USER_AIRSTAL=supplier_username
FTP_HOST_AIRSTAL=ftp.supplier.com

# Add more suppliers as needed...

# FTP Credentials for Platforms
FTP_PASS_ALZURA=platform_password
FTP_USER_ALZURA=platform_username
FTP_HOST_ALZURA=ftp.platform.com

# Add more platforms as needed...
'''
    
    env_path = Path(".env.template")
    if not env_path.exists():
        with open(env_path, 'w') as f:
            f.write(env_template)
        print(f"✅ Created {env_path}")
        print("   Copy this to .env and update with your actual credentials")
    else:
        print(f"⚠️  {env_path} already exists, skipping")

def validate_existing_config():
    """Validate existing configuration files"""
    config_dir = Path("config")
    
    required_files = [
        "header_mappings.yaml",
        "config_encodings_separateurs.yaml", 
        "report_settings.yaml"
    ]
    
    optional_files = [
        "fournisseurs_connexions.yaml",
        "plateformes_connexions.yaml", 
        "notification_settings.yaml",
        "aws_backup.yaml"
    ]
    
    print("\n🔍 Validating configuration files:")
    
    # Check required files
    for filename in required_files:
        file_path = config_dir / filename
        if file_path.exists():
            print(f"✅ {filename}")
        else:
            print(f"❌ {filename} (required)")
    
    # Check optional files  
    for filename in optional_files:
        file_path = config_dir / filename
        if file_path.exists():
            print(f"✅ {filename}")
        else:
            print(f"⚠️  {filename} (will be created)")

def check_dependencies():
    """Check if required Python packages are installed"""
    required_packages = [
        'pandas',
        'pyyaml', 
        'python-dotenv',
        'yagmail',
        'jinja2',
        'boto3',
        'ftplib'  # Built-in, but check anyway
    ]
    
    print("\n📦 Checking Python dependencies:")
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'ftplib':
                import ftplib
            else:
                __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package}")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n📥 To install missing packages, run:")
        print(f"pip install {' '.join(missing_packages)}")
        print("Or use the requirements.txt file:")
        print("pip install -r requirements.txt")

def main():
    parser = argparse.ArgumentParser(description='Set up development environment')
    parser.add_argument('--create-configs', action='store_true', help='Create sample configuration files')
    parser.add_argument('--create-dirs', action='store_true', help='Create required directories')
    parser.add_argument('--create-env', action='store_true', help='Create .env template')
    parser.add_argument('--validate', action='store_true', help='Validate existing configuration')
    parser.add_argument('--check-deps', action='store_true', help='Check Python dependencies')
    parser.add_argument('--all', action='store_true', help='Do everything')
    
    args = parser.parse_args()
    
    if args.all:
        args.create_dirs = True
        args.create_configs = True
        args.create_env = True
        args.validate = True
        args.check_deps = True
    
    if not any([args.create_configs, args.create_dirs, args.create_env, args.validate, args.check_deps]):
        print("❓ Please specify an action. Use --help for options or --all to do everything.")
        return
    
    print("🚀 Setting up development environment for Stock Update Automation")
    print("=" * 60)
    
    if args.create_dirs:
        print("\n📁 Creating required directories...")
        create_directories()
    
    if args.create_configs:
        print("\n⚙️  Creating sample configuration files...")
        create_sample_configs()
        print("\n💡 Remember to update these files with your actual credentials!")
    
    if args.create_env:
        print("\n🔧 Creating environment template...")
        create_env_template()
    
    if args.validate:
        validate_existing_config()
    
    if args.check_deps:
        check_dependencies()
    
    print("\n🎉 Environment setup complete!")
    print("\n📋 Next steps:")
    print("1. Update configuration files with your actual credentials")
    print("2. Copy .env.template to .env and configure")
    print("3. Test the application locally with sample data")
    print("4. Deploy to AWS when ready")

if __name__ == '__main__':
    main()
