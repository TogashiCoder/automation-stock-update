# 07 Platform Files

Place the **original 07 platform file** in this folder.

## 📄 Expected File

- Any supported file: `.csv`, `.xlsx`, `.xls`, or `.txt`
- File name can be anything (e.g., `07_stock.csv`, `products.xlsx`, `inventory.txt`)
- **Only one file** should be in this folder

## 🔄 Process

1. **Load**: Original file is loaded from here for processing
2. **Update**: Stock quantities are updated with supplier data
3. **Upload**: Updated file is sent to 07 FTP (`/` root directory)
4. **Replace**: If upload succeeds, original file here is replaced with updated version
5. **Backup**: Previous version is saved to `backup_original_files/`

## ✅ Ready to Use

This subfolder is ready for your 07 platform file.
