import torch
from transformers import pipeline
import os
import logging
from utils.intent import process_intent
from utils.file_utils import change_suffix_in_path, read_file, save_file
from utils.load_sentiment_model import load_sentiment_model
import pandas as pd

from utils.db import update_task_stage, save_task_attribute
from db import TaskStage

# logger = logging.get# logger(__name__)
# logger.addHandler(logging.NullHandler())
# logger.propagate = False
# logger.setLevel(logging.CRITICAL)

def load_sentiment_model():
    # logger.info("Loading sentiment analysis model...")
    model_path = ".\\models_dir\\distilbert-base-uncased-finetuned-sst-2-english"
    device = 0 if torch.cuda.is_available() else -1
    # logger.debug(f"Using device: {'GPU' if device == 0 else 'CPU'}")
    return pipeline(
        "sentiment-analysis",
        model=model_path,
        return_all_scores=True,
        device=device
    )


def sentiment_file(df: pd.DataFrame, file_path: str):
    # logger.info(f"Starting sentiment analysis for file: {file_path}")

    question_col = "question"
    answer_col = "translated_text"

    df[question_col] = df[question_col].astype(str).str.strip()
    df[answer_col] = (
        df[answer_col]
        .astype(str)
        .str.replace(r'[",]', "", regex=True)
        .str.strip()
    )

    neutral_values = {
        "na", "n/a", "nil", "null", "nan", "none", "",
        "no comments", "not applicable", "no applicable", "no comment"
    }

    sentiments, scores, pos_scores, neg_scores = [], [], [], []
    prompts, skip_flags = [], []

    for _, row in df.iterrows():
        ans = str(row[answer_col]).strip().lower()

        if ans in neutral_values:
            skip_flags.append(True)
            prompts.append("NA")
        else:
            skip_flags.append(False)
            question = str(row[question_col]).strip().rstrip("?") + "?"
            prompt = f"Question: {question}, Answer: {row[answer_col]}"
            prompts.append(prompt)

    # logger.info("Loading sentiment model...")
    model = load_sentiment_model()

    batch_size = 16
    total = len(prompts)
    # logger.info(f"Processing {total} prompts in batches of {batch_size}")

    for i in range(0, total, batch_size):
        batch_inputs = [x for x in prompts[i:i+batch_size] if x and x != "NA"]
        results = model(batch_inputs, truncation=True) if batch_inputs else []

        local_idx = 0

        for j in range(i, min(i+batch_size, total)):
            if skip_flags[j]:
                sentiments.append("NEUTRAL")
                scores.append(1.0)
                pos_scores.append(0.0)
                neg_scores.append(0.0)
            else:
                res = results[local_idx]
                local_idx += 1

                best = max(res, key=lambda x: x["score"])
                sentiments.append(best["label"])
                scores.append(best["score"])

                pos_scores.append(next((r["score"] for r in res if r["label"] == "POSITIVE"), 0.0))
                neg_scores.append(next((r["score"] for r in res if r["label"] == "NEGATIVE"), 0.0))

    df["sentiment"] = sentiments
    df["sentiment score"] = scores
    df["positive score"] = pos_scores
    df["negative score"] = neg_scores

    output_path = change_suffix_in_path(file_path, "sentiment")

    # logger.info(f"Saving sentiment results to: {output_path}")
    save_file(df, output_path)

    return output_path, df


async def process_sentiment(df: pd.DataFrame = None, file_path: str = None, email: str = None, task_id: str = None):
    # logger.info(f"Processing sentiment for file: {file_path}, email: {email}")

    if task_id:
        await update_task_stage(task_id, TaskStage.SENTIMENT_STAGE_START)

    if df is None:
        df = read_file(file_path)

    output_path, new_df = sentiment_file(df, file_path)

    if task_id:
        await update_task_stage(task_id, TaskStage.SENTIMENT_STAGE_COMPLETE)
        await save_task_attribute(task_id, "output_file_path", output_path)
    # logger.info(f"Sentiment processing completed for: {file_path}")
    
    await process_intent(new_df, output_path, email, task_id)