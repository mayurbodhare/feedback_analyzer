
import os
import plotly.graph_objects as go
import plotly.express as px  
from utils.file_utils import read_file
from utils.db import update_task_stage, save_task_attribute
from utils.sunburst import process_sunburst
from db.models import TaskStage, Task
from db.config import AsyncSessionLocal
import pandas as pd
import logging

# logger = logging.get# logger(__name__)

def preprocess_for_treemap(df, group_cols):

    # Ensure default columns exist
    default_cols = ['depute geography', 'depute country', 'depute branch', 'depute datacenter']
    for col in default_cols:
        if col not in df.columns:
            df[col] = "Unknown"

    # Group by group_cols + sentiment and pivot
    grouped = df.groupby(group_cols + ['sentiment']).size().unstack(fill_value=0).reset_index()


    # Ensure all sentiment columns exist
    for sent in ['POSITIVE', 'NEGATIVE', 'NEUTRAL']:
        if sent not in grouped.columns:
            grouped[sent] = 0

    # Calculate total and filter
    grouped['Total'] = grouped[['POSITIVE', 'NEGATIVE', 'NEUTRAL']].sum(axis=1)
    grouped = grouped[grouped['Total'] > 0]

    # Calculate percentages
    for sent in ['POSITIVE', 'NEGATIVE', 'NEUTRAL']:
        grouped[f'{sent} %'] = (grouped[sent] / grouped['Total']) * 100

    # Build hover info
    def build_hover(row):
        rows = [f"<b>{col}:</b> {row[col]}" for col in group_cols]
        rows.append(f"<b>Total:</b> {row['Total']}")
        rows.append(f"POSITIVE: {row['POSITIVE']} ({row['POSITIVE %']:.1f}%)")
        rows.append(f"NEGATIVE: {row['NEGATIVE']} ({row['NEGATIVE %']:.1f}%)")
        rows.append(f"NEUTRAL: {row['NEUTRAL']} ({row['NEUTRAL %']:.1f}%)")
        return "<br>".join(rows)

    grouped['Hover Info'] = grouped.apply(build_hover, axis=1)

    return grouped


def build_treemap_figure(df: pd.DataFrame = None, file_path :str = None):
    if df is None:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        df = read_file(file_path)

    level_options = {
        "Region": ["depute geography"],
        "Country": ["depute geography", "depute country"],
        "Branch": ["depute geography", "depute country", "depute branch"],
        "DC": ["depute geography", "depute country", "depute branch", "depute datacenter"]
    }
    fig = go.Figure()

    buttons = []

    for i, (label, group_cols) in enumerate(level_options.items()):
        # Assuming `preprocess_for_treemap` is a function you defined to prepare the grouped data
        grouped = preprocess_for_treemap(df, group_cols)

        # Create treemap
        tree = px.treemap(
            grouped,
            path=[px.Constant(label)] + group_cols,
            values="Total",
            color="Total",
            color_continuous_scale="plasma",
            custom_data=["Hover Info"]
        )

        # Extract the trace from the plotly figure
        trace = tree.data[0]

        # Set hover template
        trace.hovertemplate = "%{customdata[0]}<extra></extra>"  # Ensure indexing is correct for custom data

        # Set color axis for treemap
        trace.marker.coloraxis = 'coloraxis'

        # Set visibility for different treemaps
        trace.visible = (i == len(level_options) - 1)

        # Add the trace to the figure
        fig.add_trace(trace)

        # Manage visibility for buttons
        visibility = [False] * len(level_options)
        visibility[i] = True

        buttons.append(dict(
            label=label,
            method="update",
            args=[{"visible": visibility}, {"title": f"Sentiment Treemap: {label} Level"}]
        ))

    # Update layout with buttons for level switching
    fig.update_layout(
        updatemenus=[dict(
            buttons=buttons,
            active=len(level_options) - 1,  # Initially show the last treemap
            direction="down",
            showactive=True,
            x=0.01,
            y=1.1,
            xanchor="left",
            yanchor="top",
            font=dict(size=13)
        )],
        height=680,
        coloraxis=dict(colorscale="plasma"),
        coloraxis_colorbar=dict(title="Count"),
        margin=dict(t=18, l=10, r=18, b=10),
        paper_bgcolor="white"
    )

    # folder, filename = os.path.split(file_path)
    # name, ext = os.path.splitext(filename)
    # output_path = os.path.join(folder, f"{name}_treemap.html")
    # fig.write_html(output_path, full_html =True, include_plotlyjs ='cdn')

    return fig.to_json()


async def process_treemap(
    df: pd.DataFrame = None,
    file_path: str = None,
    email: str = None,
    task_id: str = None,
):
    # logger.info(f"Processing treemap for file: {file_path}, email: {email}, task_id: {task_id}")
    
    if task_id:
        await update_task_stage(task_id, TaskStage.TREEMAP_STAGE_START)

    # Generate treemap as JSON string
    treemap_json = build_treemap_figure(df=df, file_path=file_path)

    if task_id:
        # async with AsyncSessionLocal() as session:
        #     task = await session.get(Task, task_id)
        #     if task:
        #         task.treemap = treemap_json  # Store JSON string directly in JSONB column
        #         await session.commit()
        #         # logger.info(f"Saved treemap JSON to DB for task {task_id}")
        #     else:
        #         # logger.error(f"Task {task_id} not found for treemap update.")
        #         raise ValueError(f"Task {task_id} not found")

        await save_task_attribute(task_id, "treemap", treemap_json)

    if task_id:
        await update_task_stage(task_id, TaskStage.TREEMAP_STAGE_COMPLETE)

    # logger.info(f"Treemap processing completed for: {file_path}")
    
    await process_sunburst(df, file_path, email, task_id)