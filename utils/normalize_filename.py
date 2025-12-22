def normalize_image_path(path: str) -> str:
    """
    Normalize a stored image path to be served under /uploads/.
    Handles cases where path starts with /uploads/uploads/ or /uploads/.
    Returns a clean path like /uploads/filename.ext
    """
    if not path:
        return ""
    
    # Remove any leading/trailing slashes for consistent processing
    path = path.strip("/")
    
    # If it starts with "uploads/uploads/", remove the first "uploads/"
    if path.startswith("uploads\\uploads\\"):
        filename = path[len("uploads\\uploads\\"):]
    elif path.startswith("uploads\\"):
        filename = path[len("uploads\\"):]
    else:
        # Just use the whole path as filename (fallback)
        filename = path

    # print("#" * 100)
    # print(filename)
    # print("#" * 100)
    # Return clean URL path
    return f"{filename}"