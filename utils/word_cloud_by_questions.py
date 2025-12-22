# import os
# from PIL import Image, ImageDraw, ImageFont
# from utils.file_utils import read_file
# from utils.load_sentiment_model import load_sentiment_model
# from utils.word_cloud import generate_wordcloud_freq, generate_wordcloud_image
# import re
# from db.config import AsyncSessionLocal
# from db.models import Task, TaskStage
# from utils.db import update_task_stage,  save_task_attribute
# import pandas as pd
# import logging
# from utils.treemap import process_treemap

# # logger = logging.get# logger(__name__)


# # Sentiment mapping
# sentiment_map = {
#     "POSITIVE": ("Positive sentiment", "Greens"),
#     "NEGATIVE": ("Negative sentiment", "Reds"),
#     "NEUTRAL": ("Neutral / Mixed sentiment", "Blues"),
# }

# # Sanitize filenames by replacing invalid characters
# def sanitize_filename(filename: str) -> str:
#     return re.sub(r'[\\/*?:"<>|]', '_', filename)

# # Get sentiment label from text
# def get_sentiment_label_from_text(text: str, model, cache: dict) -> str:
#     key = f"question_sentiment::{text}"

#     if key not in cache:
#         result = model(text.strip().rstrip("?") + "?")[0]
#         label = max(result, key=lambda x: x["score"])["label"].upper()
#         cache[key] = label

#     return cache[key]

# # Function to save wordclouds for top questions
# def save_question_wordclouds(df: pd.DataFrame = None, file_path: str = None, job_id: str = None):
#     if df is None:
#         if not os.path.exists(file_path):
#             raise FileNotFoundError(f"File not found: {file_path}")
#         df = read_file(file_path)

#     question_col = "question"
#     output_dir = f"uploads/{job_id}"
#     sentiment_model = load_sentiment_model()

#     os.makedirs(output_dir, exist_ok=True)
#     sentiment_cache = {}

#     top_questions = df[question_col].value_counts().index.tolist()

#     # This will be the JSON-compatible list: [{"question": "path"}, ...]
#     wordcloud_mapping = []

#     for question in top_questions:
#         # Get sentiment and colormap
#         sentiment = get_sentiment_label_from_text(question, sentiment_model, sentiment_cache)
#         label, colormap = sentiment_map.get(sentiment, sentiment_map["NEUTRAL"])

#         # Filter answers
#         if sentiment in ["POSITIVE", "NEGATIVE"]:
#             filtered = df[(df[question_col] == question) & (df["sentiment"] == sentiment)]
#         else:
#             filtered = df[df[question_col] == question]

#         # Generate wordcloud frequency
#         text_blob = "".join(filtered["translated_text"].dropna().astype(str))
#         freq_dict = generate_wordcloud_freq(text_blob) if text_blob else {"No Words Found": 1}
#         wordcloud_image = generate_wordcloud_image(freq_dict, colormap)

#         count = len(filtered)
#         total = len(df[df[question_col] == question])
#         pct = round((count / total) * 100, 2) if total else 0

#         # Sanitize filename
#         sanitized_question = sanitize_filename(question)

#         # Create final image with header
#         wc_img = wordcloud_image.to_image().convert("RGB")
#         width = wc_img.width
#         header_height = 220
#         final_img = Image.new("RGB", (width, wc_img.height + header_height), "white")
#         draw = ImageDraw.Draw(final_img)
#         font = ImageFont.load_default()

#         y = 20
#         draw.text((20, y), f"Question: {question}", fill="black", font=font)
#         y += 30
#         draw.text((20, y), f"Detected Sentiment: {sentiment}", fill="black", font=font)
#         y += 30
#         draw.text((20, y), f"Answers Matching Sentiment: {count} / {total}", fill="black", font=font)
#         y += 30
#         draw.text((20, y), f"Sentiment Coverage: {pct}%", fill="black", font=font)

#         final_img.paste(wc_img, (0, header_height))

#         # Save image
#         final_image_path = os.path.join(output_dir, f"{sanitized_question}.jpg")
#         final_img.save(final_image_path, "JPEG", quality=95)

#         # Append mapping: one dict per question
#         wordcloud_mapping.append({question: final_image_path})

#     return wordcloud_mapping  


# async def process_wordcloud_by_questions(
#     df: pd.DataFrame = None,
#     file_path: str = None,
#     email: str = None,
#     task_id: str = None,
# ):
#     # logger.info(f"Processing wordcloud by questions for file: {file_path}, email: {email}, task_id: {task_id}")
    
#     if task_id:
#         await update_task_stage(task_id, TaskStage.WORDCLOUD_BY_QUESTIONS_STAGE_START)

#     # Generate wordclouds and get JSON mapping
#     wordcloud_by_questions = save_question_wordclouds(df=df, file_path=file_path)

#     if task_id:
#         # async with AsyncSessionLocal() as session:
#         #     task = await session.get(Task, task_id)
#         #     if task:
#         #         task.wordcloud_by_questions = wordcloud_by_questions  # Directly assign list of dicts
#         #         await session.commit()
#         #         # logger.info(f"Saved wordcloud_by_questions to DB for task {task_id}")
#         #     else:
#         #         # logger.error(f"Task {task_id} not found for wordcloud_by_questions update.")
#         #         raise ValueError(f"Task {task_id} not found")

#         await save_task_attribute(task_id, "wordcloud_by_questions", wordcloud_by_questions)
#     if task_id:
#         await update_task_stage(task_id, TaskStage.WORDCLOUD_BY_QUESTIONS_STAGE_COMPLETE)

#     # logger.info(f"Wordcloud by questions processing completed for: {file_path}")

#     await process_treemap(df, file_path, email, task_id)
