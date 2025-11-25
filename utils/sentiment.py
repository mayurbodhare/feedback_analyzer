import torch
from transformers import pipeline
import os
from utils.file_utils import read_file, save_file

def load_sentiment_model():
    return pipeline("sentiment-analysis",
                    model = ".\models_dir\distilbert-base-uncased-finetuned-sst-2-english",
                    return_all_scores=True,
                    device=0 if torch.cuda.is_available() else -1)

def sentiment_file(file_path: str):

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    df = read_file(file_path)

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

    model = load_sentiment_model()

    batch_size = 16
    total = len(prompts)


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

                # Extract pos/neg scores (AS IS)
                pos_scores.append(next((r["score"] for r in res if r["label"] == "POSITIVE"), 0.0))
                neg_scores.append(next((r["score"] for r in res if r["label"] == "NEGATIVE"), 0.0))


    df["Sentiment"] = sentiments
    df["Sentiment Score"] = scores
    df["Positive Score"] = pos_scores
    df["Negative Score"] = neg_scores

    folder, filename = os.path.split(file_path)
    name, ext = os.path.splitext(filename)
    new_filename = f"{name}_sentiment_done{ext}"
    output_path = os.path.join(folder, new_filename)

    save_file(df, output_path)

    return output_path





    