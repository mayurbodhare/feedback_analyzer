import os
import plotly.graph_objects as go
import plotly.express as px  # Fixed typo
from utils.file_utils import read_file

def build_sunburst_figure(file_path: str):
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

    # Save in same folder
    folder, filename = os.path.split(file_path)
    name, ext = os.path.splitext(filename)
    output_path = os.path.join(folder, f"{name}_sunburst.html")
    fig.write_html(output_path, full_html =True, include_plotlyjs ="cdn")

    return output_path