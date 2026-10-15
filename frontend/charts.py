"""Plotly chart helpers shared by all pages.

Why shared helpers? So every chart in the app looks and reads the same way:
same colors for the same roles, thin bars, labels where they help.
"""
from collections import Counter
from typing import Dict, List, Optional

import plotly.graph_objects as go

# Fixed categorical order (colorblind-checked). Series 1 is always blue,
# series 2 always orange, and so on, never shuffled.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
MUTED = "#8a8985"


def _base_layout(fig: go.Figure, title: str, height: int) -> go.Figure:
    fig.update_layout(
        title=title,
        height=height,
        margin=dict(l=10, r=40, t=50, b=10),
        bargap=0.35,
        showlegend=False,
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(128,128,128,0.15)", zeroline=False)
    fig.update_yaxes(showgrid=False)
    return fig


def frequency_bars(counts: Counter, title: str, color: str = SERIES[0], top: int = 12) -> go.Figure:
    """Horizontal bars of how often each item appeared, most common on top.

    Horizontal, so long token labels stay readable.
    """
    total = sum(counts.values()) or 1
    items = counts.most_common(top)[::-1]  # reversed: plotly draws bottom-up
    labels = [k for k, _ in items]
    shares = [v / total for _, v in items]
    fig = go.Figure(
        go.Bar(
            x=shares,
            y=labels,
            orientation="h",
            marker_color=color,
            text=[f"{s:.0%}" for s in shares],
            textposition="outside",
            customdata=[v for _, v in items],
            hovertemplate="%{y}: %{customdata} of " + str(total) + " samples (%{x:.0%})<extra></extra>",
        )
    )
    fig.update_xaxes(tickformat=".0%", range=[0, 1.15])
    return _base_layout(fig, title, height=max(220, 40 * len(items) + 80))


def grouped_bars(
    groups: Dict[str, Counter], title: str, x_title: str = "", colors: Optional[List[str]] = None
) -> go.Figure:
    """Side-by-side bars comparing answer counts across conditions."""
    colors = colors or SERIES
    categories = sorted({k for c in groups.values() for k in c})
    fig = go.Figure()
    for i, (name, counts) in enumerate(groups.items()):
        fig.add_bar(
            name=name,
            x=categories,
            y=[counts.get(c, 0) for c in categories],
            marker_color=colors[i % len(colors)],
            hovertemplate=name + "<br>%{x}: %{y}<extra></extra>",
        )
    fig = _base_layout(fig, title, height=360)
    fig.update_layout(barmode="group", showlegend=True, legend=dict(orientation="h", y=-0.2))
    fig.update_xaxes(title=x_title, showgrid=False)
    fig.update_yaxes(title="count", showgrid=True, gridcolor="rgba(128,128,128,0.15)")
    return fig
