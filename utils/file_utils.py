import pandas as pd
import os


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
    

 