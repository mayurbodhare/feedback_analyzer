import torch
from transformers import pipeline

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
