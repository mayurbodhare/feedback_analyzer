import os
import matplotlib.pyplot as plt

from utils.file_utils import read_file

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

def sentiment_intent_donut_charts(file_path:str):

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    df = read_file(file_path)

    sentiment_counts = compute_distribution(df,"sentiment")
    sentiment_chart = generate_donut_chart(sentiment_counts)

    intent_counts = compute_distribution(df,"intent")
    intent_chart = generate_donut_chart(intent_counts)

    folder, filename = os.path.split(file_path)
    name, ext = os.path.splitext(filename)

    output_path = os.path.join(folder, f"{name}_sentiment_donut.jpeg")
    sentiment_chart.savefig(output_path,  bbox_inches="tight", dpi=300)
    plt.close(sentiment_chart)

    output_path = os.path.join(folder, f"{name}_intent_donut.jpeg")
    intent_chart.savefig(output_path,  bbox_inches="tight", dpi=300)
    plt.close(intent_chart)

    