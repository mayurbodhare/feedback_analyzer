
from collections import Counter
import os
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

from utils.file_utils import read_file
from utils.sentiment import load_sentiment_model

WORDCLOUD_EXCLUDE_WORDS = set().union(
    ENGLISH_STOP_WORDS,
    {"na","n/a","nil","null","nan","none","","no","comments","no comments",
     "not","applicable","not applicable","ok"})

def generate_wordcloud_freq(text):
    words = [
        word.strip().lower()
        for word in text.split()
        if word.isalpha()
    ]
    return dict(
        Counter([w for w in words if w not in WORDCLOUD_EXCLUDE_WORDS])
    )


def generate_wordcloud_image(freq_dict, colormap):
    wc = WordCloud(
        width=680,
        height=480,
        background_color="white",
        colormap=colormap
    ).generate_from_frequencies(freq_dict)

    return wc


def overall_wordcloud(file_path :str):

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    df = read_file(file_path)

    pos_text = " ".join(
        df[df["sentiment"] == "POSITIVE"]["translated_text"]
        .dropna()
        .astype(str)
    )

    neg_text = " ".join(
        df[df["sentiment"] == "NEGATIVE"]["translated_text"]
        .dropna()
        .astype(str)
    )

    pos_freq = generate_wordcloud_freq(pos_text)
    neg_freq = generate_wordcloud_freq(neg_text)

    word_cloud_figs = {"positive": generate_wordcloud_image(
            pos_freq if pos_freq else {"No Positive Words Found": 1}, colormap="Greens"
        ),
        "negative": generate_wordcloud_image(
            neg_freq if neg_freq else {"No Negative Words Found": 1}, colormap="Reds"
        )
    }

    #Create a new figure with side-by-side subplots
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
    
    fig.savefig(output_path, format='jpg', bbox_inches="tight", dpi=300)
    plt.close(fig)

    return output_path

