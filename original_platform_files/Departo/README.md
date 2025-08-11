# Departo Platform Files

Place the **original Departo platform file** in this folder.

## 📄 Expected File

- Any supported file: `.csv`, `.xlsx`, `.xls`, or `.txt`
- File name can be anything (e.g., `departo_products.csv`, `stock.xlsx`, `inventory.txt`)
- **Only one file** should be in this folder

## 🔄 Process

1. **Load**: Original file is loaded from here for processing
2. **Update**: Stock quantities are updated with supplier data
3. **Upload**: Updated file is sent to Departo FTP (`/files` directory)
4. **Replace**: If upload succeeds, original file here is replaced with updated version
5. **Backup**: Previous version is saved to `backup_original_files/`

## ✅ Ready to Use

This subfolder is ready for your Departo platform file.
