import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from nltk.tokenize import sent_tokenize

async def load_encoder_model():
    """Loads the sentence transformer model for embedding sentences."""
    return SentenceTransformer(r"./models_dir/all-MiniLM-L6-v2")

async def load_text_gen_model():
    """Loads the text generation model for summary generation."""
    from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer
    import torch
    model_path = r"./models_dir/gemma-1.1-2b-it"
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        # device_map={"": "cpu"}
    )
    return pipeline("text-generation", model=model, tokenizer=tokenizer)

async def generate_executive_summary(path:str , selected_level: str, selected_entity: str):
    """
    Generates an executive summary of negative feedback for a selected level and entity.

    Args:
        df (pd.DataFrame): DataFrame containing feedback data.
        selected_level (str): Column name for the hierarchy level (e.g., "Depute Branch").
        selected_entity (str): The specific entity (e.g., "Mumbai Branch").

    Returns:
        dict: A dictionary containing the extracted themes and the generated summary.
    """

    df = pd.read_csv(path)
    # Step 1: Filter for negative feedback at the selected level/entity
    filtered_df = df[
        (df[selected_level] == selected_entity) &
        (df['sentiment'].str.lower() == 'negative') &
        (~df['intent'].str.lower().isin(['no feedback', 'irrelevant']))
    ]

    

    if filtered_df.empty:
        return {"error": "No negative feedback found for the selected entity."}

    # Step 2: Extract and clean sentences
    all_texts = filtered_df['translated_text'].dropna().astype(str).tolist()
    sentences = [
        sent.strip() for fb in all_texts
        for sent in sent_tokenize(fb)
        if len(sent.strip()) > 5
    ]

    if not sentences:
        return {"error": "No valid sentences found after filtering."}

    # Step 3: Encode sentences and cluster
    encoder = await load_encoder_model()
    embeddings = encoder.encode(sentences, batch_size=64, show_progress_bar=True)

    n_clusters = min(20, len(sentences))
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    kmeans.fit(embeddings)


    # Step 4: Extract key themes
    cluster_themes = []
    for cluster_id in range(n_clusters):
        indices = [i for i, label in enumerate(kmeans.labels_) if label == cluster_id]
        if not indices:
            continue
        center = kmeans.cluster_centers_[cluster_id]
        cluster_embeds = embeddings[indices]
        distances = ((cluster_embeds - center) ** 2).sum(axis=1)
        closest_idx = indices[distances.argmin()]
        cluster_themes.append(sentences[closest_idx])

    formatted_themes = ", ".join(
        [theme.strip().capitalize() for theme in cluster_themes]
    )

    # Step 5: Generate summary using LLM
    prompt = f"""
    You are a professional communication assistant.

    Area Selected: {selected_level} = {selected_entity}

    Below are the key feedback themes from employees, separated by commas:
    {formatted_themes}

    Please write a clear and concise executive summary capturing the key concerns and suggestions.
    Avoid repeating exact phrasing or including vague entries.
    """

    text_generator = await load_text_gen_model()
    result =  text_generator(prompt, max_new_tokens=400, do_sample=True, temperature=0.7)
    final_summary = result[0]['generated_text'].replace(prompt, '').strip()

    return final_summary

    # return {
    #     "themes": cluster_themes,
    #     "summary": final_summary,
    #     "filtered_data": filtered_df
    # }
