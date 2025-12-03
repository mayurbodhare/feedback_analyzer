import torch
from transformers import pipeline
import os
from utils.file_utils import read_file, save_file
import pandas as pd
from email_sender import send_confirmation_email
import logging


logger = logging.getLogger(__name__)


POSITIVE_INTENTS = ["team appreciation","process appreciation","service satisfaction","general praise","irrelevant"]
NEGATIVE_INTENTS = ["technical issue","process issue","support dissatisfaction","resource complaint","irrelevant"]

def load_intent_model():
    return pipeline(
        "zero-shot-classification",
        model=r"./models_dir/bart-large-mnli",
        device=0 if torch.cuda.is_available() else -1
    )

def deduplicate_columns(columns):
    seen = {}
    result = []
    for col in columns:
        if col in seen:
            seen[col] += 1
            result.append(f"{col}_{seen[col]}")
        else:
            seen[col] = 0
            result.append(col)
    return result

def intent_file(df: pd.DataFrame, file_path: str):
    # normalize column names for safe access
    df.columns = [c.strip() for c in df.columns]

    # Validate columns
    required_columns = ["question", "translated_text", "Sentiment"]
    for col in required_columns:
        if col not in df.columns:
            raise KeyError(f"Missing required column: {col}")

    results = []
    model = load_intent_model()

    for _, row in df.iterrows():

        sentiment = str(row["Sentiment"]).strip().lower()
    
        if sentiment == "neutral":
            results.append({
                "Intent": "no feedback",
                "Intent Score": None
            })
            continue

        answer_text = str(row["translated_text"]).strip()
        question_text = str(row["question"]).strip().rstrip("?") + "?"

        prompt = f"Question: {question_text}, Answer: {answer_text}"

        labels = POSITIVE_INTENTS if sentiment == "positive" else NEGATIVE_INTENTS

        res = model(
            prompt,
            candidate_labels=labels,
            multi_label=False
        )

        results.append({
            "Intent": res["labels"][0],
            "Intent Score": res["scores"][0]
        })

    intent_df = pd.DataFrame(results)

    merged = pd.concat([df, intent_df], axis=1)
    merged.columns = deduplicate_columns(merged.columns)

    folder, filename = os.path.split(file_path)
    name, ext = os.path.splitext(filename)
    new_filename = f"{name}_intent_done{ext}"
    output_path = os.path.join(folder, new_filename)

    # IMPORTANT FIX
    save_file(merged, output_path)

    return output_path, merged


async def process_intent(df: pd.DataFrame, file_path: str, email: str):
    logger.info(f"Processing intent for file: {file_path}, email: {email}")
    output_path, new_df = intent_file(df, file_path)
    await send_confirmation_email(output_path, email)
    logger.info(f"Intent processing completed for: {file_path}")