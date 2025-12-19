import pandas as pd
import os
from pathlib import Path

def read_file(file_path :str) -> pd.DataFrame:

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    _,file_extension =os.path.splitext(file_path)
    file_extension = file_extension.lower()

    if file_extension == ".csv":
        df = pd.read_csv(file_path)
    elif file_extension == ".tsv":
        df = pd.read_csv(file_path, sep="\t")
    elif file_extension in [".xlsx", ".xls"]:
        df = pd.read_excel(file_path)
    elif file_extension == ".ods":
        df = pd.read_excel(file_path, engine="odf")
    else:
        raise ValueError(f"Unsupported file type: {file_extension}")
    
    return df

def save_file(df:pd.DataFrame, file_path:str):
    _,file_extension =os.path.splitext(file_path)
    file_extension = file_extension.lower()

    if file_extension == ".csv":
        df.to_csv(file_path, index=False)
    elif file_extension == ".tsv":
        df.to_csv(file_path, sep="\t",index=False)
    elif file_extension in [".xlsx", ".xls"]:
        df.to_excel(file_path, index=False)
    elif file_extension == ".ods":
        df.to_excel(file_path, engine="odf", index=False)
    else:
        raise ValueError(f"Unable to save file. Unsupported format")
    

def add_suffix_to_path(file_path: str, suffix: str) -> str:
    """
    Add a suffix to the filename before the extension.
    
    Example:
        add_suffix_to_path("uploads/data.csv", "_translated") 
        → "uploads/data_translated.csv"
    """
    path = Path(file_path)
    return str(path.parent / f"{path.stem}{suffix}{path.suffix}")

def get_path_without_suffix(file_path: str) -> str:
    """
    Return the file path with:
      - the extension removed
      - and everything after the last underscore (_) in the filename also removed.
    
    Example:
        get_path_without_suffix("uploads/report_final.xlsx") → "uploads/report"
        get_path_without_suffix("data/user_backup_v2.csv") → "data/user_backup"
        get_path_without_suffix("notes.txt") → "notes"  (no underscore → unchanged stem)
    """
    path = Path(file_path)
    stem = path.stem
    
    # If there's an underscore, take everything before the last one
    if '_' in stem:
        base_name = stem.rsplit('_', 1)[0]
    else:
        base_name = stem
    
    return str(path.parent / base_name)

def change_suffix_in_path(file_path: str, new_suffix: str) -> str:
    """
    Replace the last underscore-based suffix in the filename with a new suffix.
    
    Uses the logic from `get_path_without_suffix` to find the base name,
    then appends the new suffix before the file extension.
    
    Examples:
        change_suffix_in_path("uploads/data_raw.csv", "_clean")
            → "uploads/data_clean.csv"
            
        change_suffix_in_path("uploads/report_final.xlsx", "_sentiment")
            → "uploads/report_sentiment.xlsx"
            
        change_suffix_in_path("uploads/notes.csv", "_processed")
            → "uploads/notes_processed.csv"  (no underscore → treat full name as base)
    """
    # Get base path without last suffix and without extension
    base_path = get_path_without_suffix(file_path)  # e.g., "uploads/report" from "uploads/report_final.xlsx"
    
    # Ensure new_suffix starts with underscore (convention)
    if not new_suffix.startswith("_"):
        new_suffix = "_" + new_suffix

    # Get original extension
    original_ext = Path(file_path).suffix  # e.g., ".xlsx"
    
    # Combine: base + new_suffix + extension
    new_path = f"{base_path}{new_suffix}{original_ext}"
    
    return new_path