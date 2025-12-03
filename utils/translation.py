import os
import argostranslate.package
import argostranslate.translate
import langid
import pandas as pd
import logging
from utils.file_utils import read_file, save_file
from utils.sentiment import process_sentiment

logger = logging.getLogger(__name__)


def load_translation_models(models_path="./models_dir/Translation_Model"):
    if not os.path.exists(models_path):
        logger.error(f"Translation model path '{models_path}' not found.")
        raise FileNotFoundError(f"Translation model path '{models_path}' not found.")

    logger.info(f"Loading translation models from: {models_path}")
    # Install models
    for fname in os.listdir(models_path):
        if fname.endswith(".argosmodel"):
            try:
                argostranslate.package.install_from_path(os.path.join(models_path, fname))
                logger.debug(f"Installed model: {fname}")
            except Exception as e:
                logger.warning(f"Failed to install model {fname}: {e}")
                pass

    # Build translation function map
    installed = argostranslate.translate.get_installed_languages()
    logger.info(f"Found {len(installed)} installed languages")

    funcs = {}

    for from_lang in installed:
        for to_lang in installed:
            if to_lang.code == "en" and from_lang.code != "en":
                funcs[from_lang.code] = from_lang.get_translation(to_lang).translate

    logger.info(f"Translation functions loaded for languages: {list(funcs.keys())}")
    return funcs


def detect_language(text: str):
    if not text.strip():
        return "en"
    
    try:
        lang, _ = langid.classify(text)
        return lang
    except Exception as e:
        logger.warning(f"Language detection failed for text '{text[:50]}...': {e}")
        return "en"


def translate_file(df: pd.DataFrame, file_path: str):
    logger.info(f"Starting translation for file: {file_path}")

    funcs = load_translation_models()

    if "answer" not in df.columns:
        logger.error("Column 'answer' not found in the input file")
        raise KeyError("Column 'answer' not found in the input file")

    logger.info("Detecting languages in 'answer' column")
    df["detected_lang"] = df["answer"].apply(
        lambda text: detect_language(str(text)) if isinstance(text, str) else "en"
    )

    df["translated_text"] = None

    for lang, group in df.groupby("detected_lang"):
        func = funcs.get(lang)

        if lang == "en" or func is None:
            logger.debug(f"Skipping translation for language '{lang}' (English or unsupported)")
            df.loc[group.index, "translated_text"] = group["answer"]
        else:
            logger.info(f"Translating {len(group)} rows from '{lang}' to English")
            try:
                df.loc[group.index, "translated_text"] = group["answer"].apply(func)
            except Exception as e:
                logger.error(f"Translation failed for language '{lang}': {e}")
                # Fallback: keep original text
                df.loc[group.index, "translated_text"] = group["answer"]

    folder, filename = os.path.split(file_path)
    name, ext = os.path.splitext(filename)
    new_filename = f"{name}_translated{ext}"
    output_path = os.path.join(folder, new_filename)

    logger.info(f"Saving translated file to: {output_path}")
    save_file(df, output_path)

    return output_path, df


async def process_translate(df: pd.DataFrame, file_path: str, email: str):
    logger.info(f"Processing translation for file: {file_path}, email: {email}")
    output_path, new_df = translate_file(df, file_path)
    await process_sentiment(new_df, file_path, email)
    logger.info(f"Translation processing completed for: {file_path}")