#!/usr/bin/env python3
"""
Test script to verify platform FTP connections only
"""

import sys
from pathlib import Path
from ftplib import FTP

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.logging_config import logger
from utils import load_plateformes_config

# Import SFTP support
try:
    import paramiko
    SFTP_AVAILABLE = True
except ImportError:
    SFTP_AVAILABLE = False
    print("⚠️  paramiko not installed - SFTP connections will fail")

def test_sftp_connection(platform_name, host, port, username, password, path):
    """Test SFTP connection"""
    if not SFTP_AVAILABLE:
        print(f"   ❌ paramiko not available for SFTP connection")
        return False
    
    try:
        # Create SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Connect
        ssh.connect(hostname=host, port=port, username=username, password=password)
        print(f"   ✅ SSH connected to {host}:{port}")
        
        # Create SFTP client
        sftp = ssh.open_sftp()
        print(f"   ✅ SFTP session established")
        
        # Navigate to path if specified
        if path and path != '/':
            try:
                sftp.chdir(path)
                print(f"   ✅ Navigated to path: {path}")
            except Exception as path_error:
                print(f"   ❌ Failed to navigate to path '{path}': {path_error}")
                sftp.close()
                ssh.close()
                return False
        else:
            print(f"   ✅ Using root directory: /")
        
        # Get current directory
        current_dir = sftp.getcwd() or '/'
        print(f"   📁 Current directory: {current_dir}")
        
        # List files
        try:
            files = sftp.listdir('.')
            print(f"   📄 Files found: {len(files)} files")
            if files:
                print(f"      First few files: {files[:5]}")
        except Exception as list_error:
            print(f"   ⚠️  Could not list files: {list_error}")
        
        # Cleanup
        sftp.close()
        ssh.close()
        
        print(f"   ✅ {platform_name} SFTP connection successful!")
        return True
        
    except Exception as e:
        print(f"   ❌ SFTP Connection failed: {e}")
        return False

def test_ftp_connection(platform_name, host, port, username, password, path):
    """Test regular FTP connection"""
    try:
        with FTP() as ftp:
            # Connect
            ftp.connect(host, port)
            print(f"   ✅ Connected to {host}:{port}")
            
            # Login
            ftp.login(username, password)
            print(f"   ✅ Logged in as {username}")
            
            # Navigate to path if specified
            if path and path != '/':
                try:
                    ftp.cwd(path)
                    print(f"   ✅ Navigated to path: {path}")
                except Exception as path_error:
                    print(f"   ❌ Failed to navigate to path '{path}': {path_error}")
                    return False
            else:
                print(f"   ✅ Using root directory: /")
            
            # Get current directory
            current_dir = ftp.pwd()
            print(f"   📁 Current directory: {current_dir}")
            
            # List files (optional)
            try:
                files = ftp.nlst()
                print(f"   📄 Files found: {len(files)} files")
                if files:
                    print(f"      First few files: {files[:5]}")
            except Exception as list_error:
                print(f"   ⚠️  Could not list files: {list_error}")
            
            print(f"   ✅ {platform_name} FTP connection successful!")
            return True
            
    except Exception as e:
        print(f"   ❌ FTP Connection failed: {e}")
        return False

def test_platform_connection(platform_name, config):
    """Test connection to a single platform"""
    print(f"\n🔍 Testing {platform_name}...")
    
    host = config.get('host')
    username = config.get('username')
    password = config.get('password')
    path = config.get('path', '/')
    port = config.get('port', 21)
    protocol = config.get('type', 'FTP').upper()
    
    print(f"   Host: {host}:{port}")
    print(f"   User: {username}")
    print(f"   Path: {path}")
    print(f"   Protocol: {protocol}")
    
    if not all([host, username, password]):
        print(f"   ❌ Missing credentials for {platform_name}")
        return False
    
    # Choose connection method based on protocol
    if protocol == 'SFTP':
        return test_sftp_connection(platform_name, host, port, username, password, path)
    else:
        return test_ftp_connection(platform_name, host, port, username, password, path)

def main():
    """Test all platform connections"""
    print("🚀 Testing Platform FTP Connections...")
    print("=" * 50)
    
    # Load platform configurations
    try:
        platforms_config = load_plateformes_config()
        print(f"📋 Found {len(platforms_config)} platforms to test")
    except Exception as e:
        print(f"❌ Failed to load platform configuration: {e}")
        return
    
    if not platforms_config:
        print("❌ No platforms found in configuration")
        return
    
    # Test each platform
    results = {}
    for platform_name, config in platforms_config.items():
        success = test_platform_connection(platform_name, config)
        results[platform_name] = success
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Connection Test Summary:")
    
    successful = [name for name, success in results.items() if success]
    failed = [name for name, success in results.items() if not success]
    
    print(f"   ✅ Successful: {len(successful)}/{len(results)}")
    for platform in successful:
        print(f"      ✅ {platform}")
    
    if failed:
        print(f"   ❌ Failed: {len(failed)}/{len(results)}")
        for platform in failed:
            print(f"      ❌ {platform}")
    
    if len(successful) == len(results):
        print("\n🎉 All platform connections successful!")
    else:
        print(f"\n⚠️  {len(failed)} platform(s) failed connection test")

if __name__ == "__main__":
    import sys
    
    # If platform names provided as arguments, test only those
    if len(sys.argv) > 1:
        platforms_to_test = sys.argv[1:]
        print(f"🎯 Testing specific platforms: {platforms_to_test}")
        
        platforms_config = load_plateformes_config()
        results = {}
        
        for platform_name in platforms_to_test:
            if platform_name in platforms_config:
                success = test_platform_connection(platform_name, platforms_config[platform_name])
                results[platform_name] = success
            else:
                print(f"❌ Platform '{platform_name}' not found in configuration")
        
        # Summary for specific platforms
        if results:
            print("\n" + "=" * 50)
            successful = sum(results.values())
            print(f"📊 Results: {successful}/{len(results)} successful")
    else:
        main()
