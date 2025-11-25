import os
import argostranslate.package
import argostranslate.translate
import langid
import pandas as pd
from utils.file_utils import read_file, save_file

def load_translation_models(models_path="./models_dir/Translation_models"):
    if not os.path.exists(models_path):
        raise FileNotFoundError(f"Translation model path '{models_path}' not found.")

    # Install models
    for fname in os.listdir(models_path):
        if fname.endswith(".argosmodel"):
            try:
                argostranslate.package.install_from_path(os.path.join(models_path, fname))
            except Exception:
                pass

    # Build translation function map
    installed = argostranslate.translate.get_installed_languages()
    funcs = {}

    for from_lang in installed:
        for to_lang in installed:
            if to_lang.code == "en" and from_lang.code != "en":
                funcs[from_lang.code] = from_lang.get_translation(to_lang).translate

    return funcs


def detect_language(text: str):
    
    if not text.strip():
        return "en"
    
    try:
        lang, _ = langid.classify(text)
        return lang
    except Exception:
        return "en"


def translate_file(file_path: str):

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    funcs = load_translation_models()
    
    df = read_file(file_path)

    if "answer" not in df.columns:
        raise KeyError("Column 'answer' not found in the input file")

    df["detected_lang"] = df["answer"].apply(
        lambda text: detect_language(str(text)) if isinstance(text, str) else "en"
    )

    df["translated_text"] = None

    for lang, group in df.groupby("detected_lang"):
        func = funcs.get(lang)

        if lang == "en" or func is None:
            # If English or unsupported language
            df.loc[group.index, "translated_text"] = group["answer"]
        else:
            try:
                df.loc[group.index, "translated_text"] = group["answer"].apply(func)
            except Exception:
                # Fallback: keep original text
                df.loc[group.index, "translated_text"] = group["answer"]

    folder, filename = os.path.split(file_path)
    name, ext = os.path.splitext(filename)
    new_filename = f"{name}_translated{ext}"
    output_path = os.path.join(folder, new_filename)

    save_file(df, output_path)

    return output_path