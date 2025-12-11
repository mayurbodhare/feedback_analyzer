import plotly.express as px
import pandas as pd


def preprocess_for_treemap(df, group_cols):
    df_copy = df.copy()
    default_cols = ['Depute Geography', 'Depute Country', 'Depute Branch', 'Depute DC']
    for col in default_cols:
        if col not in df_copy.columns:
            df_copy[col] = "Unknown"

    grouped = df_copy.groupby(group_cols + ['Sentiment']).size().unstack(fill_value=0).reset_index()
    for sent in ['Positive', 'Negative', 'Neutral']:
        if sent not in grouped.columns:
            grouped[sent] = 0
    grouped['Total'] = grouped[['Positive', 'Negative', 'Neutral']].sum(axis=1)
    grouped = grouped[grouped['Total'] > 0]

    for sent in ['Positive', 'Negative', 'Neutral']:
        grouped[f'{sent} %'] = (grouped[sent] / grouped['Total']) * 100

    def build_hover(row):
        rows = [f"<b>{col}:</b> {row[col]}" for col in group_cols]
        rows.append(f"<br><b>Total:</b> {row['Total']}")
        rows.append(f"🟢 Positive: {row['Positive']} ({row['Positive %']:.1f}%)")
        rows.append(f"🔴 Negative: {row['Negative']} ({row['Negative %']:.1f}%)")
        rows.append(f"🟡 Neutral: {row['Neutral']} ({row['Neutral %']:.1f}%)")
        return "<br>".join(rows)

    grouped['Hover Info'] = grouped.apply(build_hover, axis=1)
    return grouped

# sample data
# df = pd.DataFrame({
#     "category": ["A", "A", "B", "B", "C"],
#     "sub": ["A1", "A2", "B1", "B2", "C1"],
#     "value": [10, 20, 15, 25, 30]
# })


df = pd.read_csv("uploads/test_intent_done.csv")

df = preprocess_for_treemap(df, ['Depute Geography', 'Depute Country', 'Depute Branch', 'Depute DC'])


fig = px.treemap(
    df,
    path=["category", "sub"],  # hierarchy
    values="value"
)

# Save as interactive HTML
obj = fig.write_html("treemap_3.html", full_html=False, include_plotlyjs='cdn')

with open("treemap_2.json", "w") as f:
    f.write(fig.to_json())

print(obj)





# def build_treemap_figure(df, level_options):
#     fig = go.Figure()
#     buttons = []
#     for i, (label, group_cols) in enumerate(level_options.items()):
#         grouped = preprocess_for_treemap(df, group_cols)
#         tree = px.treemap(
#             grouped,
#             path=[px.Constant(label)] + group_cols,
#             values="Total",
#             color="Total",
#             color_continuous_scale="plasma",
#             custom_data=["Hover Info"]
#         )
#         trace = tree.data[0]
#         trace.hovertemplate = "%{customdata[0]}<extra></extra>"
#         trace.marker.coloraxis = 'coloraxis'
#         trace.visible = (i == len(level_options) - 1)

#         fig.add_trace(trace)

#         visibility = [False] * len(level_options)
#         visibility[i] = True

#         buttons.append(dict(
#             label=label,
#             method="update",
#             args=[{"visible": visibility}, {"title": f"Sentiment Treemap: {label} Level"}]
#         ))

    # fig.update_layout(
    #     updatemenus=[dict(
    #         buttons=buttons,
    #         active=len(level_options) - 1,
    #         direction="down",
    #         showactive=True,
    #         x=0.01,
    #         y=1.1,
    #         xanchor="left",
    #         yanchor="top",
    #         font=dict(size=13)
    #     )],
    #     height=680,
    #     coloraxis=dict(colorscale="plasma"),
    #     coloraxis_colorbar=dict(title="📊Count"),
    #     margin=dict(t=10, l=10, r=10, b=10),
    #     paper_bgcolor="white"
    # )
    # return fig
