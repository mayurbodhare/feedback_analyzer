import torch
from transformers import pipeline
import os
from utils.file_utils import change_suffix_in_path, read_file, save_file
import pandas as pd
from email_sender import send_confirmation_email
import logging

from utils.db import save_task_attribute, update_task_stage
from utils.donut_chart import process_distribution_charts

from db import TaskStage

# logger = logging.get# logger(__name__)
# logger.addHandler(logging.NullHandler())
# logger.propagate = False
# logger.setLevel(logging.CRITICAL)

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
    required_columns = ["question", "translated_text", "sentiment"]
    for col in required_columns:
        if col not in df.columns:
            raise KeyError(f"Missing required column: {col}")

    results = []
    model = load_intent_model()

    for _, row in df.iterrows():

        sentiment = str(row["sentiment"]).strip().lower()
    
        if sentiment == "neutral":
            results.append({
                "intent": "no feedback",
                "intent score": None
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
            "intent": res["labels"][0],
            "intent score": res["scores"][0]
        })

    intent_df = pd.DataFrame(results)

    merged = pd.concat([df, intent_df], axis=1)
    merged.columns = deduplicate_columns(merged.columns)

    output_path = change_suffix_in_path(file_path, "intent")

    # IMPORTANT FIX
    save_file(merged, output_path)

    return output_path, merged



async def process_intent(df: pd.DataFrame = None, file_path: str = None, email: str = None, task_id: str = None):
    # logger.info(f"Processing intent for file: {file_path}, email: {email}")
    if task_id:
        await update_task_stage(task_id, TaskStage.INTENT_STAGE_START)

    if df is None:
        df = read_file(file_path)

    output_path, new_df = intent_file(df, file_path)

    if task_id:
        await update_task_stage(task_id, TaskStage.INTENT_STAGE_COMPLETE)
        await save_task_attribute(task_id, "output_file_path", output_path)
    # logger.info(f"Intent processing completed for: {file_path}")
    
    await process_distribution_charts(new_df, output_path, email, task_id)
    