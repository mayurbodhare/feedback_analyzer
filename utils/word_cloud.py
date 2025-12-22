from collections import Counter
from wordcloud import WordCloud
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
from db.config import AsyncSessionLocal
from db.models import Task, TaskStage
from utils.db import update_task_stage, save_task_attribute
from utils.file_utils import read_file, get_path_without_suffix
# from utils.word_cloud_by_questions import process_wordcloud_by_questions
import matplotlib.pyplot as plt
import pandas as pd
import logging
import os

from PIL import Image, ImageDraw, ImageFont
from utils.load_sentiment_model import load_sentiment_model
# from utils.word_cloud import generate_wordcloud_freq, generate_wordcloud_image
import re
from utils.treemap import process_treemap

logger = logging.getLogger(__name__)

WORDCLOUD_EXCLUDE_WORDS = set().union(
    ENGLISH_STOP_WORDS,
    {
        "na",
        "n/a",
        "nil",
        "null",
        "nan",
        "none",
        "",
        "no",
        "comments",
        "no comments",
        "not",
        "applicable",
        "not applicable",
        "ok",
    },
)


def generate_wordcloud_freq(text):
    words = [word.strip().lower() for word in text.split() if word.isalpha()]
    return dict(Counter([w for w in words if w not in WORDCLOUD_EXCLUDE_WORDS]))


def generate_wordcloud_image(freq_dict, colormap):
    wc = WordCloud(
        width=680, height=480, background_color="white", colormap=colormap
    ).generate_from_frequencies(freq_dict)

    return wc


def overall_wordcloud(df: pd.DataFrame = None, file_path: str= None):


    if df is None:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        df = read_file(file_path)

    pos_text = " ".join(
        df[df["sentiment"] == "POSITIVE"]["translated_text"].dropna().astype(str)
    )

    neg_text = " ".join(
        df[df["sentiment"] == "NEGATIVE"]["translated_text"].dropna().astype(str)
    )

    pos_freq = generate_wordcloud_freq(pos_text)
    neg_freq = generate_wordcloud_freq(neg_text)

    word_cloud_figs = {
        "positive": generate_wordcloud_image(
            pos_freq if pos_freq else {"no": 1}, colormap="Greens"
        ),
        "negative": generate_wordcloud_image(
            neg_freq if neg_freq else {"no": 1}, colormap="Reds"
        ),
    }

    # Create a new figure with side-by-side subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))

    # Plot the positive wordcloud
    ax1.imshow(word_cloud_figs["positive"], interpolation="bilinear")
    ax1.axis("off")
    ax1.set_title("Positive Sentiment")

    # Plot the negative wordcloud
    ax2.imshow(word_cloud_figs["negative"], interpolation="bilinear")
    ax2.axis("off")
    ax2.set_title("Negative Sentiment")

    folder, filename = os.path.split(file_path)
    name, ext = os.path.splitext(filename)
    output_path = os.path.join(folder, f"{name}_overall_worclouds.jpeg")

    fig.savefig(output_path, format="jpg", bbox_inches="tight", dpi=300)
    plt.close(fig)

    return output_path



# Sentiment mapping
sentiment_map = {
    "POSITIVE": ("Positive sentiment", "Greens"),
    "NEGATIVE": ("Negative sentiment", "Reds"),
    "NEUTRAL": ("Neutral / Mixed sentiment", "Blues"),
}

# Sanitize filenames by replacing invalid characters
def sanitize_filename(filename: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', '_', filename)

# Get sentiment label from text
def get_sentiment_label_from_text(text: str, model, cache: dict) -> str:
    key = f"question_sentiment::{text}"

    if key not in cache:
        result = model(text.strip().rstrip("?") + "?")[0]
        label = max(result, key=lambda x: x["score"])["label"].upper()
        cache[key] = label

    return cache[key]

# Function to save wordclouds for top questions
def save_question_wordclouds(df: pd.DataFrame = None, file_path: str = None):
    if df is None:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        df = read_file(file_path)
    file_name = get_path_without_suffix(file_path)
    question_col = "question"
    output_dir = "{name}".format(name=file_name)
    sentiment_model = load_sentiment_model()

    os.makedirs(output_dir, exist_ok=True)
    sentiment_cache = {}

    top_questions = df[question_col].value_counts().index.tolist()

    # This will be the JSON-compatible list: [{"question": "path"}, ...]
    wordcloud_mapping = []

    for question in top_questions:
        # Get sentiment and colormap
        sentiment = get_sentiment_label_from_text(question, sentiment_model, sentiment_cache)
        label, colormap = sentiment_map.get(sentiment, sentiment_map["NEUTRAL"])

        # Filter answers
        if sentiment in ["POSITIVE", "NEGATIVE"]:
            filtered = df[(df[question_col] == question) & (df["sentiment"] == sentiment)]
        else:
            filtered = df[df[question_col] == question]

        # Generate wordcloud frequency
        text_blob = "".join(filtered["translated_text"].dropna().astype(str))
        freq_dict = generate_wordcloud_freq(text_blob) if text_blob else {"No Words Found": 1}
        wordcloud_image = generate_wordcloud_image(freq_dict, colormap)

        count = len(filtered)
        total = len(df[df[question_col] == question])
        pct = round((count / total) * 100, 2) if total else 0

        # Sanitize filename
        sanitized_question = sanitize_filename(question)

        # Create final image with header
        wc_img = wordcloud_image.to_image().convert("RGB")
        width = wc_img.width
        header_height = 220
        final_img = Image.new("RGB", (width, wc_img.height + header_height), "white")
        draw = ImageDraw.Draw(final_img)
        font = ImageFont.load_default()

        y = 20
        draw.text((20, y), f"Question: {question}", fill="black", font=font)
        y += 30
        draw.text((20, y), f"Detected Sentiment: {sentiment}", fill="black", font=font)
        y += 30
        draw.text((20, y), f"Answers Matching Sentiment: {count} / {total}", fill="black", font=font)
        y += 30
        draw.text((20, y), f"Sentiment Coverage: {pct}%", fill="black", font=font)

        final_img.paste(wc_img, (0, header_height))

        # Save image
        final_image_path = os.path.join(output_dir, f"{sanitized_question}.jpg")
        final_img.save(final_image_path, "JPEG", quality=95)

        # Append mapping: one dict per question
        wordcloud_mapping.append({question: final_image_path})

    return wordcloud_mapping  


async def process_wordcloud_by_questions(
    df: pd.DataFrame = None,
    file_path: str = None,
    email: str = None,
    task_id: str = None,
):
    # logger.info(f"Processing wordcloud by questions for file: {file_path}, email: {email}, task_id: {task_id}")
    
    if task_id:
        await update_task_stage(task_id, TaskStage.WORDCLOUD_BY_QUESTIONS_STAGE_START)

    # Generate wordclouds and get JSON mapping
    wordcloud_by_questions = save_question_wordclouds(df=df, file_path=file_path)

    if task_id:
        # async with AsyncSessionLocal() as session:
        #     task = await session.get(Task, task_id)
        #     if task:
        #         task.wordcloud_by_questions = wordcloud_by_questions  # Directly assign list of dicts
        #         await session.commit()
        #         # logger.info(f"Saved wordcloud_by_questions to DB for task {task_id}")
        #     else:
        #         # logger.error(f"Task {task_id} not found for wordcloud_by_questions update.")
        #         raise ValueError(f"Task {task_id} not found")

        await save_task_attribute(task_id, "wordcloud_by_questions", wordcloud_by_questions)
    if task_id:
        await update_task_stage(task_id, TaskStage.WORDCLOUD_BY_QUESTIONS_STAGE_COMPLETE)

    # logger.info(f"Wordcloud by questions processing completed for: {file_path}")

    await process_treemap(df, file_path, email, task_id)



async def process_wordcloud(
    df: pd.DataFrame = None,
    file_path: str = None,
    email: str = None,
    task_id: str = None,
):
    logger.info(f"Processing wordcloud for file: {file_path}, email: {email}")
    
    if task_id:
        await update_task_stage(task_id, TaskStage.WORDCLOUD_STAGE_START)

    
    # Generate the wordcloud image and get its path
    wordcloud_path = overall_wordcloud(df=df, file_path=file_path)

    if task_id:
        # Save the path to the DB (as a list, per ARRAY(String) schema)
        # async with AsyncSessionLocal() as session:
        #     task = await session.get(Task, task_id)
        #     if task:
        #         task.wordcloud = [wordcloud_path]  # Store as list
        #         await session.commit()
        #         logger.info(f"Saved wordcloud path to DB: {wordcloud_path}")
        #     else:
        #         logger.error(f"Task with id {task_id} not found for wordcloud update.")
        #         raise ValueError(f"Task {task_id} not found")

        await save_task_attribute(task_id, "wordcloud", [wordcloud_path])

    if task_id:
        await update_task_stage(task_id, TaskStage.WORDCLOUD_STAGE_COMPLETE)

    logger.info(f"Wordcloud processing completed for: {file_path}")

    await process_wordcloud_by_questions(df, file_path, email, task_id)

    
