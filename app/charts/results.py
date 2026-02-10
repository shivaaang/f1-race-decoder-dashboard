from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from ._shared import (
    _CHART_LAYOUT,
    _GRID,
    _H_LEGEND,
    _ZEROLINE,
    _driver_short,
)


# ---------------------------------------------------------------------------
# 5) Grid vs Finish — dumbbell chart
# ---------------------------------------------------------------------------
def build_grid_finish_chart(
    results_df: pd.DataFrame,
) -> go.Figure:
    figure = go.Figure()

    if results_df.empty:
        figure.update_layout(**_CHART_LAYOUT)
        return figure

    df = results_df.copy()
    df = df.dropna(subset=["grid_position", "finish_position"])
    df["grid_position"] = df["grid_position"].astype(int)
    df["finish_position"] = df["finish_position"].astype(int)
    df = df.sort_values("finish_position", ascending=False)  # P1 at top

    df["label"] = df.apply(_driver_short, axis=1)
    df["gained"] = df["grid_position"] - df["finish_position"]

    shown_legend = {"gained": False, "lost": False, "same": False}

    for _, row in df.iterrows():
        gained = int(row["gained"])
        if gained > 0:
            color = "#22C55E"
            cat = "gained"
            legend_name = "Gained positions"
        elif gained < 0:
            color = "#EF4444"
            cat = "lost"
            legend_name = "Lost positions"
        else:
            color = "#6B7280"
            cat = "same"
            legend_name = "Same position"

        show = not shown_legend[cat]
        shown_legend[cat] = True

        grid_pos = int(row["grid_position"])
        finish_pos = int(row["finish_position"])

        # Connecting line
        figure.add_trace(
            go.Scatter(
                x=[grid_pos, finish_pos],
                y=[row["label"], row["label"]],
                mode="lines",
                line={"color": color, "width": 2.5},
                showlegend=False,
                hoverinfo="skip",
            )
        )

        # Grid position (open marker)
        figure.add_trace(
            go.Scatter(
                x=[grid_pos],
                y=[row["label"]],
                mode="markers",
                marker={
                    "size": 9,
                    "color": "rgba(0,0,0,0)",
                    "line": {"width": 2, "color": color},
                    "symbol": "circle",
                },
                showlegend=False,
                hovertemplate=(f"<b>{row['label']}</b><br>" f"Grid: P{grid_pos}<extra></extra>"),
            )
        )

        # Finish position (filled marker)
        gained_str = f"+{gained}" if gained > 0 else str(gained) if gained < 0 else "0"
        figure.add_trace(
            go.Scatter(
                x=[finish_pos],
                y=[row["label"]],
                mode="markers",
                marker={"size": 10, "color": color, "symbol": "circle"},
                name=legend_name,
                showlegend=show,
                hovertemplate=(
                    f"<b>{row['label']}</b><br>"
                    f"Grid: P{grid_pos} \u2192 Finish: P{finish_pos}<br>"
                    f"Change: {gained_str}<extra></extra>"
                ),
            )
        )

    max_pos = max(df["grid_position"].max(), df["finish_position"].max())

    figure.update_layout(
        **_CHART_LAYOUT,
        xaxis_title="Position",
        xaxis={
            "range": [0.5, max_pos + 0.5],
            "dtick": 1,
            "gridcolor": _GRID,
            "zerolinecolor": _ZEROLINE,
            "autorange": "reversed",
        },
        yaxis={
            "gridcolor": _GRID,
            "zerolinecolor": _ZEROLINE,
            "automargin": True,
        },
        legend=_H_LEGEND,
        height=max(len(df) * 32 + 100, 450),
    )

    return figure
