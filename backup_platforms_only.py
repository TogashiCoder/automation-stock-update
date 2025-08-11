#!/usr/bin/env python3
"""
Backup-only script to download original platform files from FTP servers
without processing suppliers or making any updates.
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from ftplib import FTP
from io import BytesIO

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.logging_config import logger
from config.config_path_variables import *
from utils import load_plateformes_config, load_yaml_config

def create_backup_directory():
    """Create timestamped backup directory"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = BACKUP_LOCAL_PATH / f"platform_backup_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir, timestamp

def backup_platform_files(platforms=None, include_s3=True):
    """
    Download and backup platform files from FTP servers
    
    Args:
        platforms: List of specific platforms to backup (None = all)
        include_s3: Whether to also backup to S3 if configured
    """
    print("🔄 Starting platform files backup...")
    
    # Load platform configurations
    plateformes_config = load_plateformes_config()
    
    if platforms:
        # Filter to specific platforms
        available_platforms = list(plateformes_config.keys())
        platforms = [p for p in platforms if p in available_platforms]
        if not platforms:
            print(f"❌ No valid platforms found. Available: {available_platforms}")
            return False
        plateformes_config = {k: v for k, v in plateformes_config.items() if k in platforms}
    
    print(f"📋 Platforms to backup: {list(plateformes_config.keys())}")
    
    # Create backup directory
    backup_dir, timestamp = create_backup_directory()
    print(f"📁 Backup directory: {backup_dir}")
    
    # Load S3 settings if enabled
    s3_client = None
    s3_settings = {}
    if include_s3:
        s3_settings = load_yaml_config(CONFIG / "aws_backup.yaml") or {}
        s3_enabled = bool(s3_settings.get("enabled", False))
        if s3_enabled and s3_settings.get("bucket"):
            try:
                import boto3
                session_kwargs = {}
                if s3_settings.get("region"):
                    session_kwargs["region_name"] = s3_settings["region"]
                
                session = boto3.Session(**session_kwargs)
                client_kwargs = {}
                if s3_settings.get("endpoint_url"):
                    client_kwargs["endpoint_url"] = s3_settings["endpoint_url"]
                if s3_settings.get("access_key_id") and s3_settings.get("secret_access_key"):
                    client_kwargs["aws_access_key_id"] = s3_settings["access_key_id"]
                    client_kwargs["aws_secret_access_key"] = s3_settings["secret_access_key"]
                    if s3_settings.get("session_token"):
                        client_kwargs["aws_session_token"] = s3_settings["session_token"]
                
                s3_client = session.client("s3", **client_kwargs)
                print(f"☁️ S3 backup enabled: s3://{s3_settings['bucket']}/{s3_settings.get('prefix', 'backups/platforms')}")
            except Exception as e:
                print(f"⚠️ S3 backup setup failed: {e}")
    
    success_count = 0
    total_files = 0
    
    # Process each platform
    for platform_name, config in plateformes_config.items():
        print(f"\n🔍 Processing platform: {platform_name}")
        
        # Create platform-specific backup directory
        platform_backup_dir = backup_dir / platform_name
        platform_backup_dir.mkdir(exist_ok=True)
        
        try:
            # Connect to FTP
            host = config.get('host')
            username = config.get('username')
            password = config.get('password')
            
            if not all([host, username, password]):
                print(f"❌ Missing FTP credentials for {platform_name}")
                continue
            
            print(f"🔗 Connecting to {host}...")
            ftp = FTP(host)
            ftp.login(username, password)
            print(f"✅ Connected to {platform_name} FTP")
            
            # Use platform-specific path from config
            try:
                platform_path = config.get('path', '/')  # Default to root if not specified
                print(f"📁 Using platform path: {platform_path}")
                
                # Navigate to the platform-specific path
                if platform_path != '/':
                    ftp.cwd(platform_path)
                    print(f"📂 Changed to directory: {platform_path}")
                
                # List files in the specified directory
                supported_exts = ('.csv', '.xls', '.xlsx', '.txt')
                filenames = ftp.nlst()
                candidates = [f for f in filenames if f.lower().endswith(supported_exts)]
                
                print(f"📄 Found {len(candidates)} files to backup: {candidates}")
                
                if not candidates:
                    print(f"⚠️ No supported files found for {platform_name}")
                    ftp.quit()
                    continue
                
                # Download and backup each file
                for filename in candidates:
                    try:
                        print(f"⬇️ Downloading {filename}...")
                        
                        # Download file to memory (we're already in the correct directory)
                        buf = BytesIO()
                        ftp.retrbinary(f"RETR {filename}", buf.write)
                        buf.seek(0)
                        file_data = buf.getvalue()
                        
                        # Save local backup
                        local_backup_path = platform_backup_dir / filename
                        with open(local_backup_path, 'wb') as f:
                            f.write(file_data)
                        
                        print(f"💾 Local backup: {local_backup_path}")
                        total_files += 1
                        
                        # S3 backup if enabled
                        if s3_client and s3_settings.get("bucket"):
                            try:
                                s3_prefix = s3_settings.get("prefix", "backups/platforms")
                                s3_key = f"{s3_prefix}/{timestamp}/{platform_name}/{filename}"
                                s3_client.put_object(
                                    Bucket=s3_settings["bucket"],
                                    Key=s3_key,
                                    Body=file_data
                                )
                                print(f"☁️ S3 backup: s3://{s3_settings['bucket']}/{s3_key}")
                            except Exception as e:
                                print(f"⚠️ S3 backup failed for {filename}: {e}")
                        
                    except Exception as e:
                        print(f"❌ Failed to backup {filename}: {e}")
                
                success_count += 1
                print(f"✅ {platform_name} backup completed")
                
            except Exception as e:
                print(f"❌ Failed to list files for {platform_name}: {e}")
            
            ftp.quit()
            
        except Exception as e:
            print(f"❌ FTP connection failed for {platform_name}: {e}")
    
    # Summary
    print(f"\n📊 Backup Summary:")
    print(f"  Platforms processed: {success_count}/{len(plateformes_config)}")
    print(f"  Total files backed up: {total_files}")
    print(f"  Backup location: {backup_dir}")
    
    if s3_client and s3_settings.get("bucket"):
        s3_prefix = s3_settings.get("prefix", "backups/platforms")
        print(f"  S3 backup location: s3://{s3_settings['bucket']}/{s3_prefix}/{timestamp}/")
    
    return success_count > 0

def main():
    parser = argparse.ArgumentParser(
        description="Backup platform files from FTP servers without making any updates"
    )
    parser.add_argument(
        "--platforms",
        type=str,
        default="",
        help="Comma-separated list of platforms to backup (default: all configured platforms)"
    )
    parser.add_argument(
        "--no-s3",
        action="store_true",
        help="Skip S3 backup even if configured"
    )
    parser.add_argument(
        "--list-platforms",
        action="store_true",
        help="List available platforms and exit"
    )
    
    args = parser.parse_args()
    
    # List platforms if requested
    if args.list_platforms:
        plateformes_config = load_plateformes_config()
        print("📋 Available platforms:")
        for platform in plateformes_config.keys():
            print(f"  - {platform}")
        return
    
    # Parse platform list
    platforms = None
    if args.platforms:
        platforms = [p.strip() for p in args.platforms.split(',') if p.strip()]
    
    # Run backup
    try:
        success = backup_platform_files(
            platforms=platforms,
            include_s3=not args.no_s3
        )
        if success:
            print("\n🎉 Backup completed successfully!")
        else:
            print("\n❌ Backup failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️ Backup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Backup failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
