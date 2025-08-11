# Original Platform Files Directory

This directory stores the **original platform files** for the new upload-only workflow.

## 📁 New Workflow Overview

**Previous workflow**: Download from platform FTP → Process → Upload
**New workflow**: Use local originals → Process → Upload → Update local originals

## 🗂️ Subfolder Structure

Each platform has its own subfolder named exactly as defined in `config/plateformes_connexions.yaml`:

```
original_platform_files/
├── 07/                    ← Platform "07" files
├── Alzura/                ← Platform "Alzura" files
├── Departo/               ← Platform "Departo" files
├── Drox_auto/             ← Platform "Drox_auto" files
├── Market-DE-NEW/         ← Platform "Market-DE-NEW" files
└── TIELEHABERDER/         ← Platform "TIELEHABERDER" files
```

## 🔧 How to Populate This Directory

### Method 1: Manual Copy (Recommended for initial setup)

1. Place your current platform files in the respective subfolders:

   - `original_platform_files/Alzura/alzura_stock.csv`
   - `original_platform_files/Departo/departo_products.xlsx`
   - `original_platform_files/07/stock_07.csv`
   - etc.

2. **File naming**: Any name is acceptable within each subfolder. The script will use the first supported file found (.csv, .xlsx, .xls, .txt).

### Method 2: Temporary FTP Download (For initial population)

1. Temporarily enable the old FTP download function in `functions/functions_FTP.py`
2. Run the script once to download current platform files
3. Copy the downloaded files from `fichiers_platforms/` to the appropriate subfolders
4. Re-disable the FTP download function

## 📋 Expected Subfolders and Files

Based on your platform configuration:

| Platform      | Subfolder        | Example File                 |
| ------------- | ---------------- | ---------------------------- |
| 07            | `07/`            | `stock.csv`, `products.xlsx` |
| Alzura        | `Alzura/`        | `alzura_stock.csv`           |
| Departo       | `Departo/`       | `departo_products.xlsx`      |
| Drox_auto     | `Drox_auto/`     | `drox_inventory.csv`         |
| Market-DE-NEW | `Market-DE-NEW/` | `market_de.csv`              |
| TIELEHABERDER | `TIELEHABERDER/` | `tielehaberder.xlsx`         |

**Important**:

- Each subfolder must contain **exactly one** supported file (.csv, .xlsx, .xls, .txt)
- File name within the subfolder can be anything
- Subfolder name must match the platform name in `plateformes_connexions.yaml` exactly

## 🔄 Automatic Updates

After each successful upload to a platform FTP server:

1. ✅ The original file is **backed up** to `backup_original_files/`
2. ✅ The original file is **replaced** with the updated version
3. ✅ Next run will use the updated file as the new baseline

## 🚨 Important Notes

- **Upload-only**: Platform FTP servers are now upload-only (no download)
- **Backup safety**: Original files are backed up before each replacement
- **Failure-safe**: If upload fails, original files remain unchanged
- **Self-updating**: Original files automatically update after successful uploads
- **Subfolder structure**: Each platform has its own subfolder for organization

## 📂 Directory Structure

```
original_platform_files/     ← You are here (original files in subfolders)
backup_original_files/       ← Timestamped backups
fichiers_platforms/          ← Legacy (now for compatibility only)
UPDATED_FILES/               ← Generated updated files for upload
```
