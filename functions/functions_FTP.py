import os

from utils import *
from ftplib import FTP
from utils import load_fournisseurs_config, load_plateformes_config
from config.logging_config import logger
from config.config_path_variables import *
from functions.functions_check_ready_files import *
from utils import get_entity_mappings, load_yaml_config

# ------------------------------------------------------------------------------
#                           FTP Configuration
# ------------------------------------------------------------------------------
def create_ftp_config(keys, is_fournisseur=True):
    """
    keys: ["FOURNISSEUR_A", ...] or ["PLATFORM_A", ...]
    is_fournisseur: True for suppliers, False for platforms
    """
    config = {}
    all_creds = load_fournisseurs_config() if is_fournisseur else load_plateformes_config()
    for key in keys:
        creds = all_creds.get(key, {})
        host = creds.get('host')
        user = creds.get('username')
        password = creds.get('password')
        if not all([host, user, password]):
            logger.error(f'-- ❌ --  FTP config missing for {key}')
            raise ValueError(f"FTP config missing for {key}")
        config[key] = {
            "host": host,
            "user": user,
            "password": password
        }
    return config


# ------------------------------------------------------------------------------
#                           Download File via FTP
# ------------------------------------------------------------------------------
def download_file_from_ftp(ftp, remote_file, local_file):
    """
    Charger le fichier du serveur FTP ==> puis créer une copie localement
    """
    try:
        with open(local_file, "wb") as local_f:
            ftp.retrbinary("RETR " + remote_file, local_f.write)
        logger.info(f" -- ✅ --  Téléchargement terminé : {remote_file}")
        return True

    except Exception as e:
        logger.error(f"-- ❌ --  Error de téléchargement: {remote_file}: {e}")
        return False
    

# ------------------------------------------------------------------------------
#                 Fonction pour télécharger tous les fichiers FTP
# ------------------------------------------------------------------------------
def download_files_from_all_servers(ftp_servers, output_dir):    
    '''
    Args: 
        ftp_servers:
            {'FOURNISSEUR_A': {'host': 'ftp.fournisseur-a.com', 'user': 'user_a', 'password': 'pass_a'}, 
              'FOURNISSEUR_B': {'host': 'ftp.fournisseur-b.com', 'user': 'user_b', 'password': 'pass_b'}, 
              ...}
              & Same same for Platforms

        output_dir: fichiers_fournisseurs ou fichiers_platforms
    return: 
        list_fichiers ==> dict('FOURNISSEUR_A': chemin fichierA , 
                               'FOURNISSEUR_B': chemin fichierB,... )

    '''
    
    os.makedirs(output_dir, exist_ok=True)

    downloaded_files = {}

    for name, config in ftp_servers.items():      # sachant que: create_ftp_config <==> FTP_SERVERS_FOURNISSEURS = {"FOURNISSEUR_A": {"host": "ftp_host_FOURNISSEUR_A", "user": os.getenv("FTP_USER_FOURNISSEUR_A"), "password": os.getenv("FTP_PASS_FOURNISSEUR_A")},...}
        try:
            ftp = FTP(config["host"])
            ftp.login(config["user"], config["password"])
            logger.info(f"-- ✅ --  Bien connecté à l'FTP de {name}")

            filenames = ftp.nlst()       # pour récupérer la liste des fichiers et répertoires dans le répertoire courant du serveur FTP
            ftp_file = next((f for f in filenames if f.endswith(('.csv', '.xls', '.xlsx', '.txt'))), None)    # retourn le premier fichier de ces extension

            if ftp_file:
                extension = os.path.splitext(ftp_file)[1]  # exemple : '.csv'
                local_path = os.path.join(output_dir, f"{name}-{extension}")
                success = download_file_from_ftp(ftp, ftp_file, local_path)
                if success:
                    downloaded_files[name] = local_path 
                logger.info(f" -- ✅ --  Téléchargement terminé pour {name}: {ftp_file} → {local_path}")

            else:
                logger.exception(f"-- ⚠️ --  Aucun fichier valide trouvé pour {name}")

            ftp.quit()

        except Exception as e:
            logger.error(f"-- ❌ --  Erreur connexion FTP pour {name} : {e}")

    return downloaded_files



# ------------------------------------------------------------------------------
#       Load all/few Fournisseurs/ platforms existed in env file             
# ------------------------------------------------------------------------------
def load_fournisseurs_ftp(list_fournisseurs, report_gen=None):
    # Clean old downloaded files (>5h) before fetching new ones
    try:
        os.makedirs(DOSSIER_FOURNISSEURS, exist_ok=True)
        delete_old_files(DOSSIER_FOURNISSEURS, max_age_hours=5, extensions=(".csv", ".xls", ".xlsx", ".txt"))
    except Exception as _cleanup_err:
        logger.warning(f"[WARNING]: Cleanup fournisseurs folder failed: {_cleanup_err}")
    f_data_ftp = create_ftp_config(list_fournisseurs, is_fournisseur=True)
    downloaded_files_F = {}
    for name, config in f_data_ftp.items():
        try:
            # Check if this supplier is multi_file
            _, _, multi_file = get_entity_mappings(name)
            ftp = FTP(config["host"])
            ftp.login(config["user"], config["password"])
            logger.info(f"-- ✅ --  Bien connecté à l'FTP de {name}")
            
            # Get the specific path for this supplier from config
            supplier_path = config.get('path', '/')  # Default to root if not specified
            logger.info(f"[INFO]: Using supplier path: {supplier_path}")
            
            try:
                # Navigate to the supplier-specific path
                if supplier_path != '/':
                    ftp.cwd(supplier_path)
                    logger.info(f"[INFO]: Changed to directory: {supplier_path}")
                
                # List files in the specified directory
                filenames = ftp.nlst()
                valid_files = [f for f in filenames if f.endswith((".csv", ".xls", ".xlsx", ".txt"))]
                logger.info(f"[INFO]: Found {len(valid_files)} files in {supplier_path}: {valid_files}")
                
            except Exception as e:
                logger.error(f"[ERROR]: Could not access path {supplier_path} for {name}: {e}")
                valid_files = []
            if multi_file:
                local_paths = []
                for ftp_file in valid_files:
                    extension = os.path.splitext(ftp_file)[1]
                    local_path = os.path.join(DOSSIER_FOURNISSEURS, f"{name}-{ftp_file}")
                    success = download_file_from_ftp(ftp, ftp_file, local_path)
                    if success:
                        local_paths.append(local_path)
                        if report_gen:
                            report_gen.add_supplier_processed(name)
                            report_gen.add_file_result(local_path, success=True)
                    else:
                        if report_gen:
                            report_gen.add_file_result(local_path, success=False, error_msg=f"Échec du téléchargement pour {name}")
                if local_paths:
                    downloaded_files_F[name] = local_paths
                else:
                    logger.exception(f"-- ⚠️ --  Aucun fichier valide trouvé pour {name}")
                    if report_gen:
                        report_gen.add_file_result(f"Aucun fichier pour {name}", success=False, error_msg="Aucun fichier valide trouvé")
            else:
                ftp_file = next((f for f in valid_files), None)
                if ftp_file:
                    extension = os.path.splitext(ftp_file)[1]
                    local_path = os.path.join(DOSSIER_FOURNISSEURS, f"{name}-{extension}")
                    success = download_file_from_ftp(ftp, ftp_file, local_path)
                    if success:
                        downloaded_files_F[name] = local_path
                        if report_gen:
                            report_gen.add_supplier_processed(name)
                            report_gen.add_file_result(local_path, success=True)
                    else:
                        if report_gen:
                            report_gen.add_file_result(local_path, success=False, error_msg=f"Échec du téléchargement pour {name}")
                else:
                    logger.exception(f"-- ⚠️ --  Aucun fichier valide trouvé pour {name}")
                    if report_gen:
                        report_gen.add_file_result(f"Aucun fichier pour {name}", success=False, error_msg="Aucun fichier valide trouvé")
            ftp.quit()
        except Exception as e:
            logger.error(f"-- ❌ --  Erreur connexion FTP pour {name} : {e}")
            if report_gen:
                report_gen.add_file_result(f"FTP {name}", success=False, error_msg=str(e))
                report_gen.add_error(f"Erreur FTP fournisseur {name}: {e}")
    return downloaded_files_F


def load_platforms_ftp(list_platforms, report_gen=None):
    """
    DEPRECATED: This function is commented out for the new workflow.
    Platform FTP servers are now upload-only. Use load_platforms_local() instead.
    
    This function is kept for manual population of original platform files later.
    """
    logger.warning("⚠️ DEPRECATED: Platform FTP download is disabled. Platform files should be loaded locally.")
    logger.info("💡 Use load_platforms_local() instead for the new workflow.")
    logger.info("📝 To manually populate original files, temporarily enable this function.")
    return {}
    
    # COMMENTED OUT - Original FTP download logic below
    """
    # Clean old downloaded platform files (>5h)
    try:
        os.makedirs(DOSSIER_PLATFORMS, exist_ok=True)
        delete_old_files(DOSSIER_PLATFORMS, max_age_hours=5, extensions=(".csv", ".xls", ".xlsx", ".txt"))
    except Exception as _cleanup_err:
        logger.warning(f"[WARNING]: Cleanup platforms folder failed: {_cleanup_err}")
    p_data_ftp = create_ftp_config(list_platforms, is_fournisseur=False)
    downloaded_files_P = {}
    for name, config in p_data_ftp.items():
        try:
            ftp = FTP(config["host"])
            ftp.login(config["user"], config["password"])
            logger.info(f"-- ✅ --  Bien connecté à l'FTP de {name}")
            
            # Get the specific path for this platform from config
            platform_path = config.get('path', '/')  # Default to root if not specified
            logger.info(f"[INFO]: Using platform path: {platform_path}")
            
            supported_exts = (".csv", ".xls", ".xlsx", ".txt")
            
            try:
                # Navigate to the platform-specific path
                if platform_path != '/':
                    ftp.cwd(platform_path)
                    logger.info(f"[INFO]: Changed to directory: {platform_path}")
                
                # List files in the specified directory
                filenames = ftp.nlst()
                candidates = [f for f in filenames if f.lower().endswith(supported_exts)]
                logger.info(f"[INFO]: Found {len(candidates)} files in {platform_path}: {candidates}")
                
            except Exception as e:
                logger.error(f"[ERROR]: Could not access path {platform_path} for {name}: {e}")
                candidates = []
            canonical = [f for f in candidates if (not f.lower().startswith(f"{name.lower()}-")) and ("-latest" not in f.lower())]
            prefixed = [f for f in candidates if f.lower().startswith(f"{name.lower()}-") and ("-latest" not in f.lower())]
            latests = [f for f in candidates if f.lower().startswith(f"{name.lower()}-latest")]
            ftp_file = None
            if canonical:
                ftp_file = canonical[0]
            elif prefixed:
                ftp_file = prefixed[0]
            elif latests:
                ftp_file = latests[0]
            elif candidates:
                ftp_file = candidates[0]
            if ftp_file:
                # Extract just the filename for local storage
                filename_only = os.path.basename(ftp_file)
                extension = os.path.splitext(filename_only)[1]
                local_path = os.path.join(DOSSIER_PLATFORMS, f"{name}{extension}")
                
                # File is already in the correct directory (we navigated there above)
                success = download_file_from_ftp(ftp, ftp_file, local_path)
                if success:
                    downloaded_files_P[name] = local_path
                    if report_gen:
                        report_gen.add_platform_processed(name)
                        report_gen.add_file_result(local_path, success=True)
                else:
                    logger.debug(f"[DEBUG]: Candidates on FTP for {name}: {candidates}")
            else:
                logger.exception(f"-- ⚠️ --  Aucun fichier valide trouvé pour {name}")
                if report_gen:
                    report_gen.add_file_result(f"Aucun fichier pour {name}", success=False, error_msg="Aucun fichier valide trouvé")
            ftp.quit()
        except Exception as e:
            logger.error(f"-- ❌ --  Erreur connexion FTP pour {name} : {e}")
            if report_gen:
                report_gen.add_file_result(f"FTP {name}", success=False, error_msg=str(e))
                report_gen.add_error(f"Erreur FTP plateforme {name}: {e}")
    return downloaded_files_P
    """


# ------------------------------------------------------------------------------
#         Upload updated marketplace files to their respective FTP servers
# ------------------------------------------------------------------------------
def find_latest_file_for_platform(platform_dir, platform_name):
    """
    Helper to find the latest updated file for a platform.
    Prefer <PLATFORM_NAME>-latest.<ext> for ext in {csv,xlsx,xls,txt},
    else pick the most recent timestamped file across supported extensions.
    """
    supported_exts = ('.csv', '.xlsx', '.xls', '.txt')
    # Prefer latest by extension priority
    for ext in supported_exts:
        latest_path = platform_dir / f"{platform_name}-latest{ext}"
        if latest_path.exists():
            return latest_path
    # Fallback to most recent timestamped file across supported exts
    candidates = []
    for ext in supported_exts:
        candidates.extend([f for f in platform_dir.glob(f"{platform_name}-*{ext}") if '-latest' not in f.name])
    if candidates:
        return max(candidates, key=lambda f: f.stat().st_mtime)
    return None


def load_platforms_local(list_platforms, report_gen=None):
    """
    NEW: Load platform files from local original_platform_files folder
    instead of downloading from FTP servers.
    This is the new workflow where platform FTP is upload-only.
    """
    logger.info("🔄 Loading platform files from local storage (new workflow)")
    
    # Ensure the original platform files directory exists
    try:
        ORIGINAL_PLATFORM_FILES_PATH.mkdir(parents=True, exist_ok=True)
        logger.info(f"[INFO]: Original platform files directory: {ORIGINAL_PLATFORM_FILES_PATH}")
    except Exception as e:
        logger.error(f"[ERROR]: Could not create original platform files directory: {e}")
        return {}
    
    # Load platform configurations to validate against available platforms
    try:
        plateformes_config = load_plateformes_config()
    except Exception as e:
        logger.error(f"[ERROR]: Could not load platform configurations: {e}")
        return {}
    
    loaded_files_P = {}
    supported_exts = (".csv", ".xls", ".xlsx", ".txt")
    
    for platform_name in list_platforms:
        if platform_name not in plateformes_config:
            logger.warning(f"[WARNING]: Platform {platform_name} not found in configuration")
            if report_gen:
                report_gen.add_file_result(f"Platform {platform_name}", success=False, error_msg="Platform not in configuration")
            continue
        
        try:
            # Look for original file in platform-specific subfolder
            platform_subfolder = ORIGINAL_PLATFORM_FILES_PATH / platform_name
            platform_files = []
            
            # Check if the platform subfolder exists
            if not platform_subfolder.exists():
                logger.warning(f"[WARNING]: Platform subfolder not found: {platform_subfolder}")
                logger.info(f"[INFO]: Expected subfolder: original_platform_files/{platform_name}/")
                if report_gen:
                    report_gen.add_file_result(f"Subfolder for {platform_name}", success=False, error_msg="Platform subfolder not found")
                continue
            
            # Look for files in the platform subfolder
            for ext in supported_exts:
                # Check for any files with supported extensions in the platform subfolder
                pattern_files = list(platform_subfolder.glob(f"*{ext}"))
                platform_files.extend(pattern_files)
            
            if not platform_files:
                logger.warning(f"[WARNING]: No original file found in platform subfolder: {platform_subfolder}")
                logger.info(f"[INFO]: Expected files in: original_platform_files/{platform_name}/ (any .csv, .xlsx, .xls, .txt file)")
                if report_gen:
                    report_gen.add_file_result(f"Original file for {platform_name}", success=False, error_msg="No original file found in platform subfolder")
                continue
            
            # Use the first found file (you can modify this logic if needed)
            original_file = platform_files[0]
            logger.info(f"[INFO]: Found original file for {platform_name}: {original_file.name} in subfolder {platform_name}")
            
            # Copy to legacy location for compatibility with existing processing logic
            legacy_path = DOSSIER_PLATFORMS / f"{platform_name}{original_file.suffix}"
            
            # Ensure legacy directory exists
            DOSSIER_PLATFORMS.mkdir(parents=True, exist_ok=True)
            
            # Copy original file to legacy location
            import shutil
            shutil.copy2(original_file, legacy_path)
            
            loaded_files_P[platform_name] = str(legacy_path)
            logger.info(f"[INFO]: ✅ Loaded original file for {platform_name}: {original_file} -> {legacy_path}")
            
            if report_gen:
                report_gen.add_platform_processed(platform_name)
                report_gen.add_file_result(str(original_file), success=True)
                
        except Exception as e:
            logger.error(f"[ERROR]: Failed to load original file for platform {platform_name}: {e}")
            if report_gen:
                report_gen.add_file_result(f"Original file for {platform_name}", success=False, error_msg=str(e))
    
    logger.info(f"[INFO]: Loaded {len(loaded_files_P)} platform files from local storage")
    return loaded_files_P


def backup_all_original_platform_files(trigger_platform_name):
    """
    Backup ALL original platform files (entire directory structure):
    - Triggered when ANY platform upload succeeds
    - If S3 available: Upload ALL original files to S3 (no local backup)
    - If S3 not available: Create local backup of ALL platform files in organized structure
    - Keep script clean and organized
    """
    try:
        from datetime import datetime
        from utils import load_yaml_config
        import shutil
        import os
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Get all platform files to backup
        platform_files_to_backup = []
        supported_exts = (".csv", ".xls", ".xlsx", ".txt")
        
        for platform_folder in ORIGINAL_PLATFORM_FILES_PATH.iterdir():
            if platform_folder.is_dir() and platform_folder.name != '__pycache__':
                for file_path in platform_folder.iterdir():
                    if file_path.is_file() and file_path.suffix.lower() in supported_exts:
                        platform_files_to_backup.append({
                            'platform': platform_folder.name,
                            'file_path': file_path,
                            'file_name': file_path.name
                        })
        
        logger.info(f"[INFO]: 📦 Backing up {len(platform_files_to_backup)} original platform files (triggered by {trigger_platform_name})")
        
        # Try S3 backup first (preferred)
        s3_success = False
        try:
            import boto3
            aws_config = load_yaml_config(CONFIG / "aws_backup.yaml") or {}
            
            if aws_config.get("enabled", False):
                # Configure S3 client with credentials from config
                s3_kwargs = {
                    'region_name': aws_config.get("region", "eu-north-1")
                }
                if aws_config.get("access_key_id"):
                    s3_kwargs['aws_access_key_id'] = aws_config["access_key_id"]
                if aws_config.get("secret_access_key"):
                    s3_kwargs['aws_secret_access_key'] = aws_config["secret_access_key"]
                if aws_config.get("session_token"):
                    s3_kwargs['aws_session_token'] = aws_config["session_token"]
                if aws_config.get("endpoint_url"):
                    s3_kwargs['endpoint_url'] = aws_config["endpoint_url"]
                
                s3_client = boto3.client('s3', **s3_kwargs)
                bucket = aws_config.get("bucket")
                
                if bucket:
                    original_prefix = aws_config.get("prefix", "backups/platforms").replace("platforms", "original_platform_files")
                    s3_uploaded = 0
                    
                    # Upload all platform files to S3
                    for file_info in platform_files_to_backup:
                        try:
                            # Read file data
                            with open(file_info['file_path'], 'rb') as f:
                                file_data = f.read()
                            
                            # S3 key: backups/original_platform_files/YYYYMMDD_HHMMSS/Platform/filename.ext
                            s3_key = f"{original_prefix}/{timestamp}/{file_info['platform']}/{file_info['file_name']}"
                            
                            # Upload to S3
                            s3_client.put_object(
                                Bucket=bucket,
                                Key=s3_key,
                                Body=file_data
                            )
                            s3_uploaded += 1
                            
                        except Exception as file_error:
                            logger.warning(f"[WARNING]: Failed to upload {file_info['platform']}/{file_info['file_name']} to S3: {file_error}")
                    
                    logger.info(f"[INFO]: ☁️ S3 backup completed: {s3_uploaded}/{len(platform_files_to_backup)} files uploaded to s3://{bucket}/{original_prefix}/{timestamp}/")
                    logger.info(f"[INFO]: 🧹 S3 available - skipping local backup (keeping script clean)")
                    s3_success = True
                    return f"s3://{bucket}/{original_prefix}/{timestamp}/"
                    
        except Exception as s3_error:
            logger.warning(f"[WARNING]: S3 backup failed: {s3_error}")
        
        # Local backup only if S3 failed or not available
        if not s3_success:
            logger.info(f"[INFO]: 💾 S3 not available - creating local backup of all original platform files")
            
            # Create timestamped backup directory
            backup_session_dir = BACKUP_ORIGINAL_FILES_PATH / f"backup_{timestamp}"
            backup_session_dir.mkdir(parents=True, exist_ok=True)
            
            local_backed_up = 0
            
            # Copy all platform files to local backup with organized structure
            for file_info in platform_files_to_backup:
                try:
                    # Create platform subfolder in backup session
                    platform_backup_dir = backup_session_dir / file_info['platform']
                    platform_backup_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Copy file to backup location
                    backup_file_path = platform_backup_dir / file_info['file_name']
                    shutil.copy2(file_info['file_path'], backup_file_path)
                    local_backed_up += 1
                    
                except Exception as file_error:
                    logger.warning(f"[WARNING]: Failed to backup {file_info['platform']}/{file_info['file_name']} locally: {file_error}")
            
            logger.info(f"[INFO]: 💾 Local backup completed: {local_backed_up}/{len(platform_files_to_backup)} files backed up to {backup_session_dir}")
            return backup_session_dir
        
    except Exception as e:
        logger.error(f"[ERROR]: Failed to backup all original platform files: {e}")
        return None


def cleanup_temporary_directories():
    """
    Clean up temporary directories after successful completion:
    - Clear fichiers_fournisseurs/ (downloaded supplier files)
    - Clear fichiers_platforms/ (temporary platform files for processing)
    Keep script clean and organized
    """
    try:
        import shutil
        
        directories_to_clean = [
            ("fichiers_fournisseurs", DOSSIER_FOURNISSEURS),
            ("fichiers_platforms", DOSSIER_PLATFORMS)
        ]
        
        cleaned_count = 0
        total_files_removed = 0
        
        for dir_name, dir_path in directories_to_clean:
            try:
                if dir_path.exists():
                    # Count files before deletion
                    files_in_dir = list(dir_path.glob("*"))
                    file_count = len([f for f in files_in_dir if f.is_file()])
                    
                    if file_count > 0:
                        # Remove all contents
                        for item in files_in_dir:
                            if item.is_file():
                                item.unlink()
                                total_files_removed += 1
                            elif item.is_dir():
                                shutil.rmtree(item)
                        
                        logger.info(f"[INFO]: 🧹 Cleaned {dir_name}/: removed {file_count} files")
                        cleaned_count += 1
                    else:
                        logger.info(f"[INFO]: 🧹 {dir_name}/ already clean (0 files)")
                else:
                    logger.info(f"[INFO]: 🧹 {dir_name}/ does not exist")
                    
            except Exception as dir_error:
                logger.warning(f"[WARNING]: Failed to clean {dir_name}/: {dir_error}")
        
        logger.info(f"[INFO]: ✅ Cleanup completed: {cleaned_count}/2 directories processed, {total_files_removed} total files removed")
        logger.info(f"[INFO]: 🧹 Temporary directories cleaned - script ready for next run")
        
        return True
        
    except Exception as e:
        logger.error(f"[ERROR]: Failed to cleanup temporary directories: {e}")
        return False


def update_original_platform_file(platform_name, updated_file_path):
    """
    Replace the original platform file with the updated version after successful upload.
    NOTE: Backup is now done at the beginning of the script run, not here.
    """
    try:
        # Find the current original file in platform subfolder
        supported_exts = (".csv", ".xls", ".xlsx", ".txt")
        platform_subfolder = ORIGINAL_PLATFORM_FILES_PATH / platform_name
        original_files = []
        
        # Check if the platform subfolder exists
        if not platform_subfolder.exists():
            logger.warning(f"[WARNING]: Platform subfolder not found for update: {platform_subfolder}")
            return False
        
        # Look for files in the platform subfolder
        for ext in supported_exts:
            pattern_files = list(platform_subfolder.glob(f"*{ext}"))
            original_files.extend(pattern_files)
        
        if not original_files:
            logger.warning(f"[WARNING]: No original file found in {platform_subfolder} to update")
            return False
        
        # Use the first found original file
        original_file = original_files[0]
        
        # Replace original file with updated version (backup already done at script start)
        import shutil
        shutil.copy2(updated_file_path, original_file)
        
        logger.info(f"[INFO]: ✅ Updated original file: {updated_file_path} -> {original_file}")
        logger.info(f"[INFO]: 🔄 Original file updated for {platform_name} after successful upload")
        
        return True
        
    except Exception as e:
        logger.error(f"[ERROR]: Failed to update original file for {platform_name}: {e}")
        return False


def upload_updated_files_to_marketplace(dry_run=False):
    """
    Uploads the <PLATFORM_NAME>-latest.csv file for each platform in UPDATED_FILES/fichiers_platforms/<PLATFORM_NAME>/ to its FTP server.
    If dry_run is True, only log actions without uploading.
    """
    import time
    from ftplib import error_perm
    from dotenv import load_dotenv
    load_dotenv()

    upload_root = UPDATED_FILES_PATH
    if not upload_root.exists() or not upload_root.is_dir():
        logger.error(f"[ERROR]: Upload directory {upload_root} does not exist or is not a directory.")
        return

    plateformes_creds = load_plateformes_config()
    # Load optional S3 backup settings
    s3_settings = load_yaml_config(CONFIG / "aws_backup.yaml") or {}
    s3_enabled = bool(s3_settings.get("enabled", False))
    s3_bucket = s3_settings.get("bucket")
    s3_prefix = s3_settings.get("prefix", "backups/platforms")
    s3_region = s3_settings.get("region")
    s3_access_key = s3_settings.get("access_key_id")
    s3_secret_key = s3_settings.get("secret_access_key")
    s3_session_token = s3_settings.get("session_token")
    s3_endpoint_url = s3_settings.get("endpoint_url")
    s3_client = None
    if s3_enabled and s3_bucket:
        try:
            import boto3  # type: ignore
            client_kwargs = {}
            if s3_region:
                client_kwargs["region_name"] = s3_region
            if s3_access_key and s3_secret_key:
                client_kwargs["aws_access_key_id"] = s3_access_key
                client_kwargs["aws_secret_access_key"] = s3_secret_key
            if s3_session_token:
                client_kwargs["aws_session_token"] = s3_session_token
            if s3_endpoint_url:
                client_kwargs["endpoint_url"] = s3_endpoint_url
            s3_client = boto3.client("s3", **client_kwargs)
            logger.info(f"[INFO]: S3 backup enabled. Bucket='{s3_bucket}', Prefix='{s3_prefix}'")
        except Exception as e:
            logger.error(f"[ERROR]: Failed to initialize S3 client: {e}")
            s3_client = None
    
    for platform_dir in upload_root.iterdir():
        if not platform_dir.is_dir():
            continue
        platform_name = platform_dir.name
        file_path = find_latest_file_for_platform(platform_dir, platform_name)
        if not file_path or not file_path.exists():
            logger.warning(f"[WARNING]: No latest file found for {platform_name} in {platform_dir}. Skipping upload.")
            continue
        creds = plateformes_creds.get(platform_name, {})
        host = creds.get('host')
        user = creds.get('username')
        password = creds.get('password')
        ftp_path = creds.get('path', '/')  # Get custom FTP path, default to root
        protocol = creds.get('type', 'FTP').upper()  # Get protocol type
        port = creds.get('port', 22 if protocol == 'SFTP' else 21)  # Default ports
        
        if not all([host, user, password]):
            logger.error(f"[ERROR]: Credentials missing for {platform_name}. Skipping upload for {file_path.name}.")
            continue
        
        logger.info(f"[INFO]: Preparing to upload {file_path.name} for {platform_name} via {protocol}.")
        logger.info(f"[INFO]: Using platform path: {ftp_path}")
        if dry_run:
            logger.info(f"[DRY RUN]: Would upload {file_path} to {protocol} for {platform_name} at path {ftp_path}.")
            continue
        success = False
        for attempt in range(1, 4):  # 3 retries
            try:
                if protocol == 'SFTP':
                    success = upload_via_sftp(platform_name, host, port, user, password, ftp_path, file_path, attempt)
                else:
                    success = upload_via_ftp(platform_name, host, port, user, password, ftp_path, file_path, attempt)
                
                if success:
                    break
                    
                    from datetime import datetime
                    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M')
                    # Prepare local backup directory under project
                    try:
                        local_backup_dir = BACKUP_LOCAL_PATH / timestamp / platform_name
                        local_backup_dir.mkdir(parents=True, exist_ok=True)
                    except Exception as e:
                        logger.warning(f"[WARNING]: Could not create local backup dir: {e}")

                    # Determine existing remote files and back them up (any supported ext)
                    remote_candidates = []
                    backed_up_count = 0
                    try:
                        filenames = ftp.nlst()
                        supported_exts = ('.csv', '.xls', '.xlsx', '.txt')
                        remote_candidates = [f for f in filenames if f.lower().endswith(supported_exts)]
                        for fname in remote_candidates:
                            try:
                                from io import BytesIO
                                buf = BytesIO()
                                ftp.retrbinary(f"RETR {fname}", buf.write)
                                buf.seek(0)
                                # 1) Always save a local backup copy in project backup folder
                                try:
                                    local_copy_path = local_backup_dir / fname  # type: ignore
                                    with open(local_copy_path, 'wb') as lf:
                                        lf.write(buf.getvalue())
                                    backed_up_count += 1
                                    logger.info(f"[INFO]: Local backup saved: {local_copy_path}")
                                except Exception as e:
                                    logger.warning(f"[WARNING]: Could not save local backup for '{fname}': {e}")
                                # 2) Optional S3 backup
                                if s3_client is not None:
                                    s3_key = f"{s3_prefix}/{timestamp}/{platform_name}/{fname}"
                                    s3_client.put_object(Bucket=s3_bucket, Key=s3_key, Body=buf.getvalue())
                                    logger.info(f"[INFO]: Backed up remote file '{fname}' to s3://{s3_bucket}/{s3_key}")
                            except Exception as e:
                                logger.warning(f"[WARNING]: Failed to back up remote file '{fname}' for {platform_name}: {e}")
                    except Exception as e:
                        logger.warning(f"[WARNING]: Could not list remote files for {platform_name}: {e}")

                    # If there were remote files and none were backed up, do not overwrite
                    if len(remote_candidates) > 0 and backed_up_count == 0:
                        logger.error(f"[ERROR]: Backup verification failed for {platform_name}. Aborting upload.")
                        raise Exception("Backup verification failed")

                    # Choose the target remote filename to replace
                    upload_ext = file_path.suffix.lower()
                    target_remote_name = None
                    # Build categorized lists
                    latest_candidates = [f for f in remote_candidates if f.lower().startswith(f"{platform_name.lower()}-latest") and f.lower().endswith(upload_ext)]
                    prefix_candidates = [f for f in remote_candidates if f.lower().startswith(f"{platform_name.lower()}-") and f not in latest_candidates and f.lower().endswith(upload_ext)]
                    # Canonical: any supported file that is NOT '-latest' and NOT starting with platform prefix
                    canonical_candidates = [f for f in remote_candidates if (not f.lower().startswith(f"{platform_name.lower()}-")) and ("-latest" not in f.lower()) and f.lower().endswith(upload_ext)]

                    # Priority 1: canonical file (likely marketplace original)
                    if canonical_candidates:
                        target_remote_name = canonical_candidates[0]
                    # Priority 2: prefixed file without '-latest'
                    elif prefix_candidates:
                        target_remote_name = prefix_candidates[0]
                    # Priority 3: existing '-latest'
                    elif latest_candidates:
                        target_remote_name = latest_candidates[0]
                    # Priority 4: any supported file
                    elif remote_candidates:
                        target_remote_name = remote_candidates[0]
                    else:
                        # Default to our latest file name
                        target_remote_name = file_path.name

                    # Proceed with upload using temp + rename for atomic replace
                    logger.info(f"[INFO]: Connected to FTP for {platform_name} (attempt {attempt}).")
                    temp_name = f"{target_remote_name}.tmp"
                    with open(file_path, "rb") as f:
                        ftp.storbinary(f"STOR {temp_name}", f)
                    try:
                        ftp.rename(temp_name, target_remote_name)
                    except Exception as e:
                        logger.warning(f"[WARNING]: Atomic rename failed, attempting direct overwrite: {e}")
                        with open(file_path, "rb") as f:
                            ftp.storbinary(f"STOR {target_remote_name}", f)

                    logger.info(f"[INFO]: Uploaded and replaced file for {platform_name}: {target_remote_name}")

                    # Cleanup: remove other old remote files for this platform to avoid duplicates
                    try:
                        filenames = ftp.nlst()
                        for fname in filenames:
                            if fname == target_remote_name:
                                continue
                            lower_name = fname.lower()
                            # Remove '-latest' files and platform-prefixed variants
                            if (lower_name.startswith(f"{platform_name.lower()}-") or '-latest' in lower_name) and lower_name.endswith(supported_exts):
                                try:
                                    ftp.delete(fname)
                                    logger.info(f"[INFO]: Removed old remote file: {fname}")
                                except Exception as e:
                                    logger.warning(f"[WARNING]: Could not delete remote file '{fname}': {e}")
                    except Exception as e:
                        logger.warning(f"[WARNING]: Cleanup listing failed for {platform_name}: {e}")
                    success = True
                    
                    # NEW: Update original platform file after successful upload
                    if success and not dry_run:
                        logger.info(f"[INFO]: 🔄 Upload successful, updating original file for {platform_name}")
                        update_success = update_original_platform_file(platform_name, str(file_path))
                        if update_success:
                            logger.info(f"[INFO]: ✅ Original file updated successfully for {platform_name}")
                        else:
                            logger.warning(f"[WARNING]: Original file update failed for {platform_name}, but upload was successful")
                    
                    break
            except Exception as e:
                logger.error(f"[ERROR]: Failed to upload file {file_path.name} to FTP for {platform_name} (attempt {attempt}): {e}")
                time.sleep(2)  # Wait before retry
        if not success and not dry_run:
            logger.error(f"[ERROR]: Failed to upload file {file_path.name} to FTP for {platform_name} after 3 attempts.")
            logger.info(f"[INFO]: ❌ Upload failed, keeping original file unchanged for {platform_name}")


def upload_via_ftp(platform_name, host, port, user, password, ftp_path, file_path, attempt):
    """Upload file via FTP"""
    try:
        with FTP(host) as ftp:
            ftp.login(user, password)
            
            # Navigate to the specified FTP path
            if ftp_path and ftp_path != '/':
                try:
                    ftp.cwd(ftp_path)
                    logger.info(f"[INFO]: Navigated to FTP path: {ftp_path}")
                except Exception as path_error:
                    logger.error(f"[ERROR]: Failed to navigate to FTP path '{ftp_path}' for {platform_name}: {path_error}")
                    raise path_error
            
            # Upload the file with a temp name first, then rename
            temp_name = f"{file_path.name}.tmp"
            logger.info(f"[INFO]: Connected to FTP for {platform_name} (attempt {attempt}).")
            
            with open(file_path, "rb") as f:
                ftp.storbinary(f"STOR {temp_name}", f)
            
            try:
                ftp.rename(temp_name, file_path.name)
            except Exception as e:
                logger.warning(f"[WARNING]: Could not rename {temp_name} -> {file_path.name}: {e}")
                logger.info(f"[INFO]: Trying to delete old file and upload with final name...")
                try:
                    ftp.delete(file_path.name)
                except:
                    pass
                with open(file_path, "rb") as f:
                    ftp.storbinary(f"STOR {file_path.name}", f)
            
            logger.info(f"[INFO]: ✅ Uploaded {file_path.name} via FTP for {platform_name}")
            return True
            
    except Exception as e:
        logger.error(f"[ERROR]: FTP upload failed for {platform_name} (attempt {attempt}): {e}")
        return False


def upload_via_sftp(platform_name, host, port, user, password, ftp_path, file_path, attempt):
    """Upload file via SFTP"""
    try:
        import paramiko
        
        # Create SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Connect
        ssh.connect(hostname=host, port=port, username=user, password=password)
        logger.info(f"[INFO]: SSH connected to {host}:{port} for {platform_name} (attempt {attempt})")
        
        # Create SFTP client
        sftp = ssh.open_sftp()
        logger.info(f"[INFO]: SFTP session established for {platform_name}")
        
        # Navigate to the specified path
        if ftp_path and ftp_path != '/':
            try:
                sftp.chdir(ftp_path)
                logger.info(f"[INFO]: Navigated to SFTP path: {ftp_path}")
            except Exception as path_error:
                logger.error(f"[ERROR]: Failed to navigate to SFTP path '{ftp_path}' for {platform_name}: {path_error}")
                sftp.close()
                ssh.close()
                raise path_error
        
        # Upload the file
        remote_file_path = file_path.name
        sftp.put(str(file_path), remote_file_path)
        
        logger.info(f"[INFO]: ✅ Uploaded {file_path.name} via SFTP for {platform_name}")
        
        # Cleanup
        sftp.close()
        ssh.close()
        
        return True
        
    except ImportError:
        logger.error(f"[ERROR]: paramiko not available for SFTP upload to {platform_name}")
        return False
    except Exception as e:
        logger.error(f"[ERROR]: SFTP upload failed for {platform_name} (attempt {attempt}): {e}")
        return False

