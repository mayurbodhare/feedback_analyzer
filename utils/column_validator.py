import pandas as pd
from typing import List, Tuple, Dict
import re
from difflib import SequenceMatcher

# Required columns (normalized)
REQUIRED_COLUMNS = [
    "depute geography",
    "depute country",
    "depute branch",
    "depute datacenter",
    "question",
    "answer"
]


def normalize_column_name(col_name: str) -> str:
    """
    Normalize column name by:
    - Converting to lowercase
    - Removing extra spaces
    - Removing special characters except spaces
    """
    if not isinstance(col_name, str):
        return ""
    
    # Convert to lowercase
    normalized = col_name.lower()
    
    # Remove extra spaces and strip
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    # Remove special characters but keep spaces
    normalized = re.sub(r'[^\w\s]', '', normalized)
    
    return normalized


def calculate_similarity(str1: str, str2: str) -> float:
    """Calculate similarity ratio between two strings"""
    return SequenceMatcher(None, str1, str2).ratio()


def find_best_match(column: str, required_columns: List[str], threshold: float = 0.8) -> Tuple[str, float]:
    """
    Find the best matching required column for a given column name
    
    Args:
        column: The column name to match
        required_columns: List of required column names
        threshold: Minimum similarity threshold (0-1)
    
    Returns:
        Tuple of (best_match, similarity_score)
    """
    normalized_col = normalize_column_name(column)
    best_match = None
    best_score = 0.0
    
    for req_col in required_columns:
        normalized_req = normalize_column_name(req_col)
        score = calculate_similarity(normalized_col, normalized_req)
        
        if score > best_score:
            best_score = score
            best_match = req_col
    
    return best_match, best_score


def validate_columns(df: pd.DataFrame, threshold: float = 0.8) -> Tuple[bool, Dict]:
    """
    Validate if DataFrame contains all required columns (with fuzzy matching)
    
    Args:
        df: DataFrame to validate
        threshold: Minimum similarity threshold for fuzzy matching (default: 0.8)
    
    Returns:
        Tuple of (is_valid, result_dict)
        result_dict contains:
            - valid: bool
            - missing_columns: list of missing columns
            - found_columns: dict mapping required columns to actual column names
            - invalid_columns: list of columns that couldn't be matched
            - suggestions: dict of possible corrections for missing columns
    """
    result = {
        "valid": True,
        "missing_columns": [],
        "found_columns": {},
        "invalid_columns": [],
        "suggestions": {}
    }
    
    # Normalize all DataFrame columns
    df_columns = [col for col in df.columns if isinstance(col, str)]
    normalized_df_cols = {normalize_column_name(col): col for col in df_columns}
    
    # Track which required columns we've found
    found_required = set()
    
    # First pass: try exact matches (after normalization)
    for req_col in REQUIRED_COLUMNS:
        normalized_req = normalize_column_name(req_col)
        
        if normalized_req in normalized_df_cols:
            result["found_columns"][req_col] = normalized_df_cols[normalized_req]
            found_required.add(req_col)
    
    # Second pass: fuzzy matching for missing columns
    missing_required = set(REQUIRED_COLUMNS) - found_required
    
    for req_col in missing_required:
        best_match = None
        best_score = 0.0
        best_actual_col = None
        
        # Try to find the best match among remaining columns
        for actual_col in df_columns:
            if actual_col in result["found_columns"].values():
                continue  # Skip already matched columns
            
            normalized_actual = normalize_column_name(actual_col)
            normalized_req = normalize_column_name(req_col)
            score = calculate_similarity(normalized_actual, normalized_req)
            
            if score > best_score:
                best_score = score
                best_match = req_col
                best_actual_col = actual_col
        
        if best_score >= threshold:
            result["found_columns"][req_col] = best_actual_col
            found_required.add(req_col)
        else:
            result["missing_columns"].append(req_col)
            if best_actual_col and best_score > 0.5:  # Lower threshold for suggestions
                result["suggestions"][req_col] = {
                    "suggested_column": best_actual_col,
                    "similarity": round(best_score * 100, 2)
                }
    
    # Check if all required columns are found
    if result["missing_columns"]:
        result["valid"] = False
    
    return result["valid"], result


def get_column_mapping(df: pd.DataFrame, threshold: float = 0.8) -> Dict[str, str]:
    """
    Get mapping of required columns to actual DataFrame columns
    
    Args:
        df: DataFrame to analyze
        threshold: Minimum similarity threshold
    
    Returns:
        Dictionary mapping required column names to actual column names
    """
    is_valid, validation_result = validate_columns(df, threshold)
    return validation_result["found_columns"]


def rename_columns_to_standard(df: pd.DataFrame, threshold: float = 0.8) -> Tuple[pd.DataFrame, bool, Dict]:
    """
    Rename DataFrame columns to standard required names
    
    Args:
        df: DataFrame to rename
        threshold: Minimum similarity threshold
    
    Returns:
        Tuple of (renamed_df, success, validation_result)
    """
    is_valid, validation_result = validate_columns(df, threshold)
    
    if not is_valid:
        return df, False, validation_result
    
    # Create reverse mapping (actual column -> required column)
    reverse_mapping = {v: k for k, v in validation_result["found_columns"].items()}
    
    # Rename columns
    renamed_df = df.rename(columns=reverse_mapping)
    
    return renamed_df, True, validation_result