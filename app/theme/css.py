"""Phosphor Icons CDN + Custom CSS — F1-inspired dark theme."""

from __future__ import annotations

import streamlit as st

_PHOSPHOR_CDN = "https://unpkg.com/@phosphor-icons/web@2.0.3/src"


def inject_theme() -> None:
    """Inject Phosphor icon CDN links and all custom CSS into the Streamlit page."""
    # Load Phosphor Icons from CDN
    st.markdown(
        f"""
        <link rel="stylesheet" href="{_PHOSPHOR_CDN}/regular/style.css" />
        <link rel="stylesheet" href="{_PHOSPHOR_CDN}/bold/style.css" />
        """,
        unsafe_allow_html=True,
    )

    # Custom CSS styles
    st.markdown(
        """
    <style>
    /* ---- Page background ---- */
    .stApp {
        background: linear-gradient(135deg, #0F1117 0%, #131720 40%, #0D0F14 100%);
        color: #E5E7EB;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        max-width: 1500px;
    }

    /* ---- Hide default Streamlit header/footer ---- */
    header[data-testid="stHeader"] { background: transparent; }
    footer { display: none; }

    /* ---- Hide blinking cursor in dropdowns ---- */
    div[data-baseweb="select"] input {
        caret-color: transparent !important;
    }

    /* ---- Race header banner ---- */
    .race-banner {
        background: linear-gradient(90deg, #E10600 0%, #8B0000 60%, #1A1D26 100%);
        border-radius: 12px;
        padding: 1rem 1.5rem;
        margin-bottom: 1rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .race-banner h1 {
        color: #FFFFFF;
        font-size: 1.75rem;
        margin: 0 0 0.2rem 0;
        font-weight: 800;
        letter-spacing: 0.02em;
    }
    .race-banner p {
        color: #E0D8D8;
        font-size: 0.95rem;
        margin: 0;
        letter-spacing: 0.03em;
    }
    .banner-links {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        flex-shrink: 0;
    }
    .banner-link {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        padding: 0.5rem 1.1rem;
        border-radius: 8px;
        background: rgba(255,255,255,0.15);
        color: #FFFFFF !important;
        text-decoration: none !important;
        font-size: 0.85rem;
        font-weight: 600;
        transition: background 0.2s ease, transform 0.15s ease;
        white-space: nowrap;
        backdrop-filter: blur(4px);
        border: 1px solid rgba(255,255,255,0.15);
    }
    .banner-link:hover {
        background: rgba(255,255,255,0.25);
        color: #FFFFFF !important;
        transform: translateY(-1px);
    }
    .banner-link i {
        font-size: 1rem;
        color: #FFFFFF !important;
    }

    /* ---- Podium cards with medal glow effects (used in Driver Deep Dive) ---- */
    .podium-card {
        background: linear-gradient(180deg, #1E2130 0%, #1A1D26 100%);
        border-radius: 12px;
        padding: 1rem 1.2rem;
        text-align: center;
        position: relative;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,0.06);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .podium-card:hover {
        transform: translateY(-2px);
    }
    .podium-card .position-badge {
        font-size: 2rem;
        font-weight: 900;
        line-height: 1;
        margin-bottom: 0.4rem;
    }
    .podium-card .driver-name {
        font-size: 1rem;
        font-weight: 700;
        color: #F0F0F0;
        margin-bottom: 0.15rem;
    }
    .podium-card .team-name {
        font-size: 0.8rem;
        color: #9CA3AF;
    }
    .podium-card .color-bar {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
    }
    /* P1 - Gold glow */
    .podium-p1 {
        box-shadow: 0 0 20px rgba(255, 215, 0, 0.15), 0 4px 12px rgba(0,0,0,0.3);
        border: 1px solid rgba(255, 215, 0, 0.25);
    }
    .podium-p1 .position-badge {
        color: #FFD700;
        text-shadow: 0 0 12px rgba(255, 215, 0, 0.5);
    }
    /* P2 - Silver glow */
    .podium-p2 {
        box-shadow: 0 0 15px rgba(192, 192, 192, 0.12), 0 3px 10px rgba(0,0,0,0.25);
        border: 1px solid rgba(192, 192, 192, 0.2);
    }
    .podium-p2 .position-badge {
        color: #C0C0C0;
        text-shadow: 0 0 10px rgba(192, 192, 192, 0.4);
    }
    /* P3 - Bronze glow */
    .podium-p3 {
        box-shadow: 0 0 15px rgba(205, 127, 50, 0.12), 0 3px 10px rgba(0,0,0,0.25);
        border: 1px solid rgba(205, 127, 50, 0.2);
    }
    .podium-p3 .position-badge {
        color: #CD7F32;
        text-shadow: 0 0 10px rgba(205, 127, 50, 0.4);
    }

    /* ---- Compact combined dashboard summary ---- */
    .dashboard-summary {
        display: flex;
        gap: 0.75rem;
        margin: 0.5rem 0 1.5rem 0;
        align-items: stretch;
    }
    .summary-section-title {
        font-size: 0.6rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #6B7280;
        padding-left: 0.2rem;
        flex-shrink: 0;
        height: 1rem;
        line-height: 1rem;
    }
    .summary-podium {
        flex: 0 0 22%;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }
    .summary-stats {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }
    .summary-kpis {
        flex: 1;
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        grid-template-rows: 1fr 1fr;
        gap: 0.5rem;
    }
    /* Compact podium cards for the sidebar */
    .compact-podium {
        background: linear-gradient(180deg, #1E2130 0%, #1A1D26 100%);
        border-radius: 10px;
        padding: 0.55rem 0.7rem 0.55rem 1rem;
        display: flex;
        align-items: center;
        gap: 0.6rem;
        border: 1px solid rgba(255,255,255,0.06);
        position: relative;
        overflow: hidden;
        flex: 1;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .compact-podium:hover {
        transform: translateX(2px);
    }
    .compact-podium::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 4px;
        border-radius: 4px 0 0 4px;
    }
    .compact-podium.cp-p1::before {
        background: linear-gradient(180deg, #FFD700, #B8860B);
    }
    .compact-podium.cp-p1 {
        box-shadow: 0 0 10px rgba(255,215,0,0.08);
        border-color: rgba(255,215,0,0.15);
    }
    .compact-podium.cp-p2::before {
        background: linear-gradient(180deg, #E0E0E0, #A0A0A0);
    }
    .compact-podium.cp-p2 {
        border-color: rgba(192,192,192,0.12);
    }
    .compact-podium.cp-p3::before {
        background: linear-gradient(180deg, #CD7F32, #8B5A2B);
    }
    .compact-podium.cp-p3 {
        border-color: rgba(205,127,50,0.12);
    }
    .compact-podium .cp-badge {
        font-size: 1.05rem;
        font-weight: 800;
        min-width: 26px;
        line-height: 1;
    }
    .compact-podium.cp-p1 .cp-badge {
        color: #FFD700;
        text-shadow: 0 0 8px rgba(255,215,0,0.35);
    }
    .compact-podium.cp-p2 .cp-badge {
        color: #C0C0C0;
        text-shadow: 0 0 6px rgba(192,192,192,0.25);
    }
    .compact-podium.cp-p3 .cp-badge {
        color: #CD7F32;
        text-shadow: 0 0 6px rgba(205,127,50,0.25);
    }
    .compact-podium .cp-info {
        display: flex;
        flex-direction: column;
        min-width: 0;
    }
    .compact-podium .cp-driver {
        font-size: 0.78rem;
        font-weight: 700;
        color: #F0F0F0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        line-height: 1.2;
    }
    .compact-podium .cp-team {
        font-size: 0.6rem;
        color: #9CA3AF;
        line-height: 1.3;
    }
    .compact-podium .cp-color-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 0.3rem;
        vertical-align: middle;
    }

    /* ---- Metric cards with icon support ---- */
    .metric-card {
        background: linear-gradient(180deg, #1E2130 0%, #1A1D26 100%);
        border-radius: 10px;
        padding: 0.7rem 0.9rem;
        border: 1px solid rgba(255,255,255,0.05);
        transition: border-color 0.2s ease, transform 0.15s ease;
        min-height: 72px;
        height: 100%;
        display: flex;
        flex-direction: row;
        align-items: center;
        gap: 0.75rem;
    }
    .metric-card:hover {
        border-color: rgba(255,255,255,0.12);
        transform: translateY(-1px);
    }
    .metric-card .metric-icon {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 40px;
        height: 40px;
        border-radius: 10px;
        background: rgba(255,255,255,0.04);
        flex-shrink: 0;
        font-size: 1.15rem;
    }
    .metric-card .metric-body {
        display: flex;
        flex-direction: column;
        min-width: 0;
    }
    .metric-card .metric-label {
        font-size: 0.6rem;
        color: #9CA3AF;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 0.1rem;
        text-align: left;
    }
    .metric-card .metric-value {
        font-size: 1.1rem;
        font-weight: 700;
        color: #FFFFFF;
        text-align: left;
        line-height: 1.2;
    }
    .metric-card .metric-sub {
        font-size: 0.65rem;
        color: #6B7280;
        margin-top: 0.1rem;
        text-align: left;
    }
    /* Color-coded metric card variants */
    .metric-card.timing .metric-icon {
        color: #60A5FA; background: rgba(96, 165, 250, 0.1);
    }
    .metric-card.timing .metric-value { color: #93C5FD; }
    .metric-card.count .metric-icon {
        color: #A78BFA; background: rgba(167, 139, 250, 0.1);
    }
    .metric-card.incident .metric-icon {
        color: #FBBF24; background: rgba(251, 191, 36, 0.1);
    }
    .metric-card.incident .metric-value { color: #FCD34D; }
    .metric-card.weather .metric-icon {
        color: #34D399; background: rgba(52, 211, 153, 0.1);
    }
    .metric-card.movement .metric-icon {
        color: #F472B6; background: rgba(244, 114, 182, 0.1);
    }
    /* High incident variant - for exceptional safety car counts */
    .metric-card.incident-high {
        border: 1px solid rgba(251, 191, 36, 0.4);
        box-shadow: 0 0 12px rgba(251, 191, 36, 0.15);
    }
    .metric-card.incident-high .metric-icon {
        color: #F59E0B; background: rgba(245, 158, 11, 0.15);
    }
    .metric-card.incident-high .metric-value {
        color: #FCD34D; font-weight: 800;
    }

    /* Metric card tooltips */
    .metric-card.has-tooltip {
        position: relative;
        cursor: help;
    }
    .metric-tooltip {
        visibility: hidden;
        opacity: 0;
        position: absolute;
        bottom: 100%;
        left: 50%;
        transform: translateX(-50%);
        background: #2A2F3F;
        color: #E5E7EB;
        padding: 0.5rem 0.75rem;
        border-radius: 6px;
        font-size: 0.75rem;
        white-space: nowrap;
        z-index: 1000;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        transition: opacity 0.2s ease, visibility 0.2s ease;
        margin-bottom: 0.5rem;
    }
    .metric-tooltip::after {
        content: '';
        position: absolute;
        top: 100%;
        left: 50%;
        transform: translateX(-50%);
        border-width: 5px;
        border-style: solid;
        border-color: #2A2F3F transparent transparent transparent;
    }
    .metric-card.has-tooltip:hover .metric-tooltip {
        visibility: visible;
        opacity: 1;
    }

    /* ---- Tab styling with better states ---- */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.4rem;
        background: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        background: #1A1D26;
        border-radius: 8px 8px 0 0;
        color: #6B7280;
        padding: 0.6rem 1.3rem;
        font-weight: 600;
        font-size: 0.9rem;
        border: 1px solid transparent;
        border-bottom: none;
        transition: all 0.15s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #D1D5DB;
        background: #232736;
    }
    .stTabs [aria-selected="true"] {
        background: #E10600 !important;
        color: #FFFFFF !important;
        border-color: #E10600;
    }

    /* ---- Chart caption (slightly smaller) ---- */
    .chart-caption {
        color: #9CA3AF;
        font-size: 0.88rem;
        margin-bottom: 0.4rem;
        line-height: 1.5;
    }

    /* ---- Section sub-header ---- */
    .section-header {
        color: #E5E7EB;
        font-size: 1.05rem;
        font-weight: 700;
        margin-top: 1.5rem;
        margin-bottom: 0.3rem;
        padding-bottom: 0.3rem;
        border-bottom: 1px solid rgba(255,255,255,0.08);
    }

    /* ---- Footer ---- */
    .app-footer {
        text-align: center;
        color: #4B5563;
        font-size: 0.75rem;
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid #1F2937;
    }

    /* ---- Dark theme for dropdown selectors ---- */
    div[data-baseweb="select"] {
        background: #1A1D26 !important;
    }
    div[data-baseweb="select"] > div {
        background: #1A1D26 !important;
        border-color: rgba(255,255,255,0.1) !important;
        color: #E5E7EB !important;
    }
    div[data-baseweb="select"] > div:hover {
        border-color: rgba(255,255,255,0.2) !important;
    }
    div[data-baseweb="select"] svg {
        fill: #9CA3AF !important;
    }
    /* Dropdown menu styling */
    div[data-baseweb="popover"] {
        background: #1A1D26 !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
    }
    div[data-baseweb="popover"] ul {
        background: #1A1D26 !important;
    }
    div[data-baseweb="popover"] li {
        background: #1A1D26 !important;
        color: #E5E7EB !important;
    }
    div[data-baseweb="popover"] li:hover {
        background: #2A2F3F !important;
    }
    /* Selectbox label styling */
    .stSelectbox label {
        color: #9CA3AF !important;
    }

    /* ---- Dark theme for dataframe/tables ---- */
    .stDataFrame {
        background: #1A1D26 !important;
        border-radius: 8px;
        overflow: hidden;
    }
    .stDataFrame > div {
        background: #1A1D26 !important;
    }
    .stDataFrame [data-testid="stDataFrameResizable"] {
        background: #1A1D26 !important;
    }
    /* GlideDataEditor - Streamlit's underlying data grid */
    [data-testid="stDataFrame"] > div > div {
        background: #1A1D26 !important;
    }
    [data-testid="stDataFrame"] canvas {
        background: #1A1D26 !important;
    }
    /* Override embedded iframe styles */
    .stDataFrame iframe {
        background: #1A1D26 !important;
    }
    /* glideDataEditor theming */
    [class*="glideDataEditor"] {
        background: #1A1D26 !important;
        --gdg-bg-cell: #1A1D26 !important;
        --gdg-bg-header: #252A3A !important;
        --gdg-text-dark: #E5E7EB !important;
        --gdg-text-header: #9CA3AF !important;
        --gdg-border-color: rgba(255,255,255,0.08) !important;
    }
    /* Table header */
    .stDataFrame th {
        background: #252A3A !important;
        color: #9CA3AF !important;
        border-bottom: 1px solid rgba(255,255,255,0.1) !important;
        font-weight: 600;
    }
    /* Table cells */
    .stDataFrame td {
        background: #1A1D26 !important;
        color: #E5E7EB !important;
        border-bottom: 1px solid rgba(255,255,255,0.05) !important;
    }
    /* Table row hover */
    .stDataFrame tr:hover td {
        background: #232736 !important;
    }
    /* Scrollbar styling for tables */
    .stDataFrame ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    .stDataFrame ::-webkit-scrollbar-track {
        background: #1A1D26;
    }
    .stDataFrame ::-webkit-scrollbar-thumb {
        background: #3B4252;
        border-radius: 4px;
    }

    /* ---- Dark theme for download button ---- */
    .stDownloadButton > button {
        background: #1A1D26 !important;
        color: #E5E7EB !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 8px !important;
        transition: all 0.2s ease !important;
    }
    .stDownloadButton > button:hover {
        background: #2A2F3F !important;
        border-color: rgba(255,255,255,0.2) !important;
        color: #FFFFFF !important;
    }

    /* ---- Regular buttons dark theme ---- */
    .stButton > button {
        background: #1A1D26 !important;
        color: #E5E7EB !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
    }
    .stButton > button:hover {
        background: #2A2F3F !important;
        border-color: rgba(255,255,255,0.2) !important;
    }

    /* ---- External link cards ---- */
    .ext-links-row {
        display: flex;
        gap: 0.75rem;
        margin-bottom: 1rem;
    }
    .ext-link-card {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        background: linear-gradient(135deg, #1E2130 0%, #1A1D26 100%);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 10px;
        padding: 0.6rem 1rem;
        text-decoration: none;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
        min-width: 200px;
    }
    .ext-link-card:hover {
        border-color: rgba(225, 6, 0, 0.5);
        box-shadow: 0 0 12px rgba(225, 6, 0, 0.15);
    }
    .ext-link-card .link-icon {
        font-size: 1.3rem;
        color: #9CA3AF;
        flex-shrink: 0;
    }
    .ext-link-card:hover .link-icon {
        color: #E10600;
    }
    .ext-link-card .link-text .link-source {
        font-size: 0.65rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #6B7280;
    }
    .ext-link-card .link-text .link-title {
        font-size: 0.85rem;
        font-weight: 600;
        color: #E5E7EB;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )
