import os
import matplotlib.pyplot as plt
from utils.file_utils import read_file, save_file
import pandas as pd
# import logging

from utils.db import update_task_stage, save_task_attribute
from db import TaskStage
from utils.file_utils import read_file

from db.config import AsyncSessionLocal
from db.models import Task

from utils.word_cloud import process_wordcloud

# # logger = logging.get# logger(__name__)

def compute_distribution(data, column_name, fillna_val=None):
    if fillna_val is not None:
        return data[column_name].fillna(fillna_val).value_counts()
    return data[column_name].value_counts()


def generate_donut_chart(data):
    # Create figure
    fig, ax = plt.subplots()

    # Percentages for legend
    percentages = (data.values / data.values.sum()) * 100

    # Function to show percentages only if >= 2%
    def autopct_format(pct):
        return f"{pct:.1f}%" if pct >= 2 else ""

    # Plot donut chart with conditional labels
    wedges, texts, autotexts = ax.pie(
        data.values,
        labels=None,                 # no category labels inside
        autopct=autopct_format,      # conditional percentages
        startangle=130,
        textprops={"fontsize": 10},
        pctdistance=0.85
    )

    # Add center white circle
    centre_circle = plt.Circle((0, 0), 0.70, fc="white")
    fig.gca().add_artist(centre_circle)

    # Equal aspect ratio
    ax.axis("equal")

    # Add legend with percentages
    legend_labels = [
        f"{cat} ({p:.1f}%)" for cat, p in zip(data.index, percentages)
    ]

    ax.legend(
        wedges,
        legend_labels,
        title="Categories",
        loc="center left",
        bbox_to_anchor=(1, 0, 0.5, 1)  # move legend outside
    )

    return fig

def sentiment_intent_donut_charts(df: pd.DataFrame = None, file_path: str = None):
    if df is None:
        df = read_file(file_path)
    
    sentiment_counts = compute_distribution(df, "sentiment")
    sentiment_chart = generate_donut_chart(sentiment_counts)

    intent_counts = compute_distribution(df, "intent")
    intent_chart = generate_donut_chart(intent_counts)

    folder, filename = os.path.split(file_path)
    name, _ = os.path.splitext(filename)

    sentiment_path = os.path.join(folder, f"{name}_sentiment_donut.jpeg")
    intent_path = os.path.join(folder, f"{name}_intent_donut.jpeg")

    sentiment_chart.savefig(sentiment_path, bbox_inches="tight", dpi=300)
    plt.close(sentiment_chart)

    intent_chart.savefig(intent_path, bbox_inches="tight", dpi=300)
    plt.close(intent_chart)

    

    return [sentiment_path, intent_path]

    
async def process_distribution_charts(
    df: pd.DataFrame = None,
    file_path: str = None,
    email: str = None,
    task_id: str = None
):
    # logger.info(f"Processing distribution charts for file: {file_path}, email: {email}")
    
    if task_id:
        await update_task_stage(task_id, TaskStage.DISTRIBUTION_CHART_STAGE_START)

    # Generate charts and get paths
    chart_paths = sentiment_intent_donut_charts(df, file_path)
    print("#" * 100)
    print(task_id)
    print(file_path)
    if task_id:
        # Save chart paths to DB
        # async with AsyncSessionLocal() as session:
        #     task = await session.get(Task, task_id)
        #     if task:
        #         task.distribution_chart = chart_paths
        #         session.add(task)
        #         await session.commit()
        #     else:
        #         pass
                # logger.warning(f"Task with id {task_id} not found for updating chart paths.")
        
        await save_task_attribute(task_id, "distribution_chart", chart_paths)
        print("*" * 100)
        await update_task_stage(task_id, TaskStage.DISTRIBUTION_CHART_STAGE_COMPLETE)
        print("$" * 100)
    # logger.info(f"Distribution charts processing completed for: {file_path}")
    print("Distribution charts processing completed\n" * 10)
    await process_wordcloud(df, file_path, email, task_id)
    
