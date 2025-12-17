import os
from PIL import Image, ImageDraw, ImageFont
from utils.file_utils import read_file
from utils.sentiment import load_sentiment_model
from utils.word_cloud import generate_wordcloud_freq, generate_wordcloud_image
import re

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
def save_question_wordclouds(file_path: str):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    df = read_file(file_path)
    question_col = "question"
    output_dir = "question_wordclouds"
    sentiment_model = load_sentiment_model()

    os.makedirs(output_dir, exist_ok=True)
    sentiment_cache = {}

    top_questions = df[question_col].value_counts().index.tolist()

    for question in top_questions:
        # Get sentiment and colormap for current question
        sentiment = get_sentiment_label_from_text(question, sentiment_model, sentiment_cache)
        label, colormap = sentiment_map.get(sentiment, sentiment_map["NEUTRAL"])

        # Filter data based on sentiment
        if sentiment in ["POSITIVE", "NEGATIVE"]:
            filtered = df[(df[question_col] == question) & (df["sentiment"] == sentiment)]
        else:
            filtered = df[df[question_col] == question]

        # Generate wordcloud
        text_blob = "".join(filtered["translated_text"].dropna().astype(str))
        freq_dict = generate_wordcloud_freq(text_blob) if text_blob else {"No Words Found": 1}
        wordcloud_image = generate_wordcloud_image(freq_dict, colormap)

        count = len(filtered)
        total = len(df[df[question_col] == question])
        pct = round((count / total) * 100, 2) if total else 0

        # Sanitize question to create valid filename
        sanitized_question = sanitize_filename(question)

        # Directly create the final image without storing the temporary wordcloud
        wordcloud_image = wordcloud_image.to_image()

        # Get the width and height of the wordcloud image for final image canvas size
        wc_img = wordcloud_image.convert("RGB")
        width = wc_img.width
        header_height = 220

        # Create a final image canvas
        final_img = Image.new("RGB", (width, wc_img.height + header_height), "white")
        draw = ImageDraw.Draw(final_img)
        font = ImageFont.load_default()

        # Overlay text on final image
        y = 20
        draw.text((20, y), f"Question: {question}", fill="black", font=font)
        y += 30
        draw.text((20, y), f"Detected Sentiment: {sentiment}", fill="black", font=font)
        y += 30
        draw.text((20, y), f"Answers Matching Sentiment: {count} / {total}", fill="black", font=font)
        y += 30
        draw.text((20, y), f"Sentiment Coverage: {pct}%", fill="black", font=font)

        # Paste wordcloud image onto the final canvas
        final_img.paste(wc_img, (0, header_height))

        # Save the final image with overlayed text
        final_image_path = os.path.join(output_dir, f"{sanitized_question}.jpg")
        final_img.save(final_image_path, "JPEG", quality=95)

    return output_dir
