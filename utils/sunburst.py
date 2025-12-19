import os
import plotly.graph_objects as go
import plotly.express as px  
from utils.file_utils import read_file
from utils.db import update_task_stage, save_task_attribute
from db.models import TaskStage, Task, TaskStatus
from db.config import AsyncSessionLocal
import pandas as pd
import logging
from email_sender import send_confirmation_email

# logger = logging.get# logger(__name__)

def build_sunburst_figure(df: pd.DataFrame = None, file_path: str = None):
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

    for i, (label, cols) in enumerate(level_options.items()):
        
        # Group by all path columns
        grouped = df.groupby(cols + ['intent']).size().reset_index(name="Count")

        sb = px.sunburst(grouped,
                         path=cols + ['intent'],
                         values="Count",
                         color="Count",
                         color_continuous_scale="plasma")
        
        sb_trace = sb.data[0]
        sb_trace.textinfo = "label+percent entry"
        sb_trace.marker.coloraxis = "coloraxis"
        sb_trace.visible = i == len(level_options) - 1
        fig.add_trace(sb_trace)
           
        visibility = [False] * len(level_options)
        visibility[i] = True

        buttons.append(dict(
            label=label,
            method="update",
            args=[{"visible": visibility},
                  {"title": f"Sunburst - {label} View"}]
        ))

    fig.update_layout(
        updatemenus=[dict(
            buttons=buttons,
            active=len(level_options) - 1,
            direction="down",
            x=0.0, y=1.1,
            showactive=True
        )],
        height=680,
        coloraxis=dict(colorscale="plasma"),  # Fixed typo
        coloraxis_colorbar=dict(title="Intent Count"),
        margin=dict(t=30, b=10),
        paper_bgcolor="white"
    )

    # # Save in same folder
    # folder, filename = os.path.split(file_path)
    # name, ext = os.path.splitext(filename)
    # output_path = os.path.join(folder, f"{name}_sunburst.html")
    # fig.write_html(output_path, full_html =True, include_plotlyjs ="cdn")

    return fig.to_json()


async def process_sunburst(
    df: pd.DataFrame = None,
    file_path: str = None,
    email: str = None,
    task_id: str = None,
):
    # logger.info(f"Processing sunburst for file: {file_path}, email: {email}, task_id: {task_id}")
    
    if task_id:
        await update_task_stage(task_id, TaskStage.SUNBURST_STAGE_START)

    
    # Generate sunburst figure as JSON string
    sunburst_json = build_sunburst_figure(df=df, file_path=file_path)

    if task_id:
        async with AsyncSessionLocal() as session:
            # task = await session.get(Task, task_id)
            # if task:
            #     task.sunburst = sunburst_json  # Store JSON string in JSONB column
            #     await session.commit()
            #     # logger.info(f"Saved sunburst JSON to DB for task {task_id}")
            # else:
            #     # logger.error(f"Task {task_id} not found for sunburst update.")
            #     raise ValueError(f"Task {task_id} not found")

            await save_task_attribute(task_id, "sunburst", sunburst_json)

    if task_id:
        await update_task_stage(task_id, TaskStage.SUNBURST_STAGE_COMPLETE, TaskStatus.COMPLETED)

    # logger.info(f"Sunburst processing completed for: {file_path}")

    if task_id and email:
        await send_confirmation_email(email=email, file_path=file_path)

    

