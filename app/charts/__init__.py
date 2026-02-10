"""Chart builders for F1 Race Decoder dashboard."""

from ._shared import (
    COMPOUND_COLORS,
    _hex_to_rgba,
    _normalize_team_color,
    format_lap_time_ms,
)
from .comparison import (
    build_driver_narrative_chart,
    build_driver_sector_heatmap,
    build_gap_to_leader_chart,
    build_lap_delta_chart,
    build_sector_comparison_chart,
)
from .pace import (
    build_lap_distribution_chart,
    build_race_pace_chart,
    build_sector_heatmap,
)
from .race_story import (
    build_gap_timeline_chart,
    build_position_chart,
)
from .results import build_grid_finish_chart
from .strategy import (
    build_stint_chart,
    build_tyre_degradation_chart,
)

__all__ = [
    "COMPOUND_COLORS",
    "_hex_to_rgba",
    "_normalize_team_color",
    "build_driver_narrative_chart",
    "build_driver_sector_heatmap",
    "build_gap_timeline_chart",
    "build_gap_to_leader_chart",
    "build_grid_finish_chart",
    "build_lap_delta_chart",
    "build_lap_distribution_chart",
    "build_position_chart",
    "build_race_pace_chart",
    "build_sector_comparison_chart",
    "build_sector_heatmap",
    "build_stint_chart",
    "build_tyre_degradation_chart",
    "format_lap_time_ms",
]
