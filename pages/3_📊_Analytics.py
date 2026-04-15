"""
📊 Analytics — Job Search Funnel Visualization
Issue #29: Sankey flow diagram + supplementary charts.
"""
import os
import sys

# Add parent directory for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from utils.data_manager import JobDataService, JOB_DATA_FILE, TRACKING_FILE
from utils.ui_utils import inject_custom_css

# --- Page Config ---
st.set_page_config(page_title="Analytics | Job Hunter", layout="wide")

# --- Theme-Aware CSS ---
analytics_css = """
/* Analytics-specific spacing */
div[data-testid="stPlotlyChart"] {
    border-radius: 12px;
    overflow: hidden;
}

/* KPI card hover effect */
div[data-testid="stMetric"] {
    transition: transform 0.2s ease;
}
div[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
}
"""
inject_custom_css(analytics_css)

# --- Color Palette (Complementary to primaryColor #6200EA) ---
COLORS = {
    "total":        "#6200EA",   # Deep purple (primary)
    "saved":        "#7C4DFF",   # Lighter purple
    "applied":      "#00BFA5",   # Teal
    "interviewing": "#FFD600",   # Amber
    "offer":        "#00E676",   # Green
    "rejected":     "#FF1744",   # Red
    "unsaved":      "#455A64",   # Blue-grey (muted)
    "not_applied":  "#78909C",   # Lighter blue-grey
    "no_response":  "#90A4AE",   # Very muted grey
}

# Node colors for Sankey (indexed by sankey_nodes order)
NODE_COLORS = [
    COLORS["total"],         # 0: Total Scraped
    COLORS["saved"],         # 1: Saved
    COLORS["applied"],       # 2: Applied
    COLORS["interviewing"],  # 3: Interviewing
    COLORS["offer"],         # 4: Offer
    COLORS["unsaved"],       # 5: Unsaved
    COLORS["not_applied"],   # 6: Not Applied
    COLORS["rejected"],      # 7: Rejected
    COLORS["no_response"],   # 8: No Response
]


# --- Fetch Data (Cached) ---
def _get_combined_mtime():
    """Cache-busting key: combined mtime of both data files."""
    t1 = os.path.getmtime(JOB_DATA_FILE) if os.path.exists(JOB_DATA_FILE) else 0
    t2 = os.path.getmtime(TRACKING_FILE) if os.path.exists(TRACKING_FILE) else 0
    return (t1, t2)


data = JobDataService.get_analytics_summary(file_mtime=_get_combined_mtime())

# --- Empty State ---
if data["total_scraped"] == 0:
    st.title("📊 Job Search Analytics")
    st.info("🚀 **No data yet.** Head to the Scraper page to start collecting job listings, then come back here to see your funnel.")
    if st.button("🚀 Go to Scraper", width="stretch"):
        st.switch_page("pages/2_🚀_Scraper.py")
    st.stop()


# =====================================================================
# 1. KPI SUMMARY ROW
# =====================================================================
st.title("📊 Job Search Analytics")
st.caption("Your complete job search funnel — inspired by r/csmajors Sankey diagrams.")

kpi_cols = st.columns(6)
kpi_data = [
    ("Total Scraped", data["total_scraped"], "🔍", None),
    ("Saved",         data["num_saved"],     "⭐", None),
    ("Applied",       data["num_applied"],    "📝", None),
    ("Interviewing",  data["num_interviewing"], "🎤", None),
    ("Offers",        data["num_offer"],      "🎉", None),
    ("Rejected",      data["num_rejected"],   "❌", None),
]

for col, (label, value, icon, delta) in zip(kpi_cols, kpi_data):
    with col:
        with st.container(border=True):
            st.metric(f"{icon} {label}", value, delta=delta)


# =====================================================================
# 2. SANKEY FLOW DIAGRAM (Hero Visual)
# =====================================================================
st.divider()
sankey_header_col, sankey_toggle_col = st.columns([3, 1])
with sankey_header_col:
    st.subheader("🌊 Application Funnel")
with sankey_toggle_col:
    show_full_funnel = st.toggle("Show Total Scraped", value=False,
                                  help="Include the full scrape pool. Off by default to focus on your active pipeline.")

if data["sankey_values"]:
    # Filter out Total Scraped → Saved/Unsaved links when toggle is off
    # Node indices: 0=Total Scraped, 1=Saved, 5=Unsaved
    sources = data["sankey_sources"]
    targets = data["sankey_targets"]
    values  = data["sankey_values"]

    if not show_full_funnel:
        # Remove links from Total Scraped (node 0), and links to
        # dead-end nodes: Unsaved (5), Not Applied (6), No Response (8)
        hidden_sources = {0}
        hidden_targets = {5, 6, 8}
        filtered = [(s, t, v) for s, t, v in zip(sources, targets, values)
                     if s not in hidden_sources and t not in hidden_targets]
        if filtered:
            sources, targets, values = zip(*filtered)
        else:
            sources, targets, values = [], [], []

    if values:
        # Build link colors with opacity
        link_colors = []
        for src, tgt in zip(sources, targets):
            base_color = NODE_COLORS[tgt]
            r, g, b = int(base_color[1:3], 16), int(base_color[3:5], 16), int(base_color[5:7], 16)
            link_colors.append(f"rgba({r},{g},{b},0.4)")

        fig_sankey = go.Figure(data=[go.Sankey(
            arrangement="snap",
            node=dict(
                pad=20,
                thickness=25,
                line=dict(color="rgba(255,255,255,0.3)", width=1),
                label=data["sankey_nodes"],
                color=NODE_COLORS,
                hovertemplate="%{label}: %{value} jobs<extra></extra>",
            ),
            link=dict(
                source=list(sources),
                target=list(targets),
                value=list(values),
                color=link_colors,
                hovertemplate="%{source.label} → %{target.label}: %{value} jobs<extra></extra>",
            ),
        )])

        fig_sankey.update_layout(
            font=dict(size=13, color="#E0E0E0", family="Inter, sans-serif"),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=420,
            margin=dict(t=20, b=20, l=30, r=30),
        )

        st.plotly_chart(fig_sankey, use_container_width=True)
    else:
        st.info("📝 **Start tracking jobs** — save, apply, and update statuses on the Dashboard to populate your funnel.")

    # Conversion metrics below the Sankey
    conv_cols = st.columns(4)
    with conv_cols[0]:
        rate = (data["num_saved"] / data["total_scraped"] * 100) if data["total_scraped"] else 0
        st.caption(f"**Save Rate:** {rate:.1f}%")
    with conv_cols[1]:
        total_acted = data["num_applied"] + data["num_interviewing"] + data["num_offer"] + data["num_rejected"]
        rate = (total_acted / data["num_saved"] * 100) if data["num_saved"] else 0
        st.caption(f"**Apply Rate:** {rate:.1f}%")
    with conv_cols[2]:
        rate = ((data["num_interviewing"] + data["num_offer"]) / total_acted * 100) if total_acted else 0
        st.caption(f"**Interview Rate:** {rate:.1f}%")
    with conv_cols[3]:
        rate = (data["num_offer"] / total_acted * 100) if total_acted else 0
        st.caption(f"**Offer Rate:** {rate:.1f}%")
else:
    st.info("📝 **Start tracking jobs** — save, apply, and update statuses on the Dashboard to populate your funnel.")


# =====================================================================
# 3. SUPPLEMENTARY CHARTS (Two-Column Layout)
# =====================================================================
st.divider()
chart_col1, chart_col2 = st.columns(2)

# --- 3a. Score Distribution ---
with chart_col1:
    st.subheader("📈 Score Distribution")
    
    if data["scores"]:
        fig_hist = go.Figure()
        
        # All jobs distribution
        fig_hist.add_trace(go.Histogram(
            x=data["scores"],
            name="All Jobs",
            marker_color=COLORS["unsaved"],
            opacity=0.6,
            nbinsx=30,
            hovertemplate="Score: %{x}<br>Count: %{y}<extra>All Jobs</extra>",
        ))

        # Saved jobs overlay
        if data["saved_scores"]:
            fig_hist.add_trace(go.Histogram(
                x=data["saved_scores"],
                name="Saved/Applied",
                marker_color=COLORS["saved"],
                opacity=0.8,
                nbinsx=30,
                hovertemplate="Score: %{x}<br>Count: %{y}<extra>Saved/Applied</extra>",
            ))

        fig_hist.update_layout(
            barmode="overlay",
            xaxis_title="Match Score",
            yaxis_title="Count",
            font=dict(color="#E0E0E0", family="Inter, sans-serif"),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=350,
            margin=dict(t=30, b=40, l=40, r=20),
            xaxis=dict(gridcolor="rgba(255,255,255,0.1)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.1)"),
        )
        st.plotly_chart(fig_hist, use_container_width=True)
        
        avg_all = sum(data["scores"]) / len(data["scores"])
        avg_saved = sum(data["saved_scores"]) / len(data["saved_scores"]) if data["saved_scores"] else 0
        if data["saved_scores"]:
            st.caption(f"Avg Score: **All {avg_all:.0f}** vs **Saved {avg_saved:.0f}** (+{avg_saved - avg_all:.0f} lift)")
        else:
            st.caption(f"Avg Score: **{avg_all:.0f}**")
    else:
        st.info("No score data available yet.")


# --- 3b. Top Companies ---
with chart_col2:
    st.subheader("🏢 Top Companies")
    
    if data["company_status"]:
        # Flatten company_status dict into rows
        company_rows = []
        for company, statuses in data["company_status"].items():
            for status, count in statuses.items():
                company_rows.append({"Company": company, "Status": status, "Count": count})

        df_companies = pd.DataFrame(company_rows)
        
        # Get top 15 by total count
        company_totals = df_companies.groupby("Company")["Count"].sum().nlargest(15).index.tolist()
        df_top = df_companies[df_companies["Company"].isin(company_totals)]

        # Status color map
        status_color_map = {
            "Applied": COLORS["applied"],
            "Interviewing": COLORS["interviewing"],
            "Offer": COLORS["offer"],
            "Rejected": COLORS["rejected"],
            "Saved": COLORS["saved"],
            "New": COLORS["unsaved"],
        }

        fig_companies = px.bar(
            df_top, 
            x="Count", 
            y="Company", 
            color="Status",
            orientation="h",
            color_discrete_map=status_color_map,
            category_orders={"Company": company_totals[::-1]},  # Reverse for horizontal
        )
        fig_companies.update_layout(
            font=dict(color="#E0E0E0", family="Inter, sans-serif"),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=350,
            margin=dict(t=30, b=20, l=20, r=20),
            xaxis=dict(gridcolor="rgba(255,255,255,0.1)", title=""),
            yaxis=dict(gridcolor="rgba(255,255,255,0.1)", title=""),
        )
        st.plotly_chart(fig_companies, use_container_width=True)
    else:
        st.info("Save or apply to jobs on the Dashboard to see company breakdown.")


# =====================================================================
# 4. APPLICATION TIMELINE
# =====================================================================
st.divider()
st.subheader("📅 Application Timeline")

if data["timeline_data"]:
    df_timeline = pd.DataFrame(data["timeline_data"])
    df_timeline["date"] = pd.to_datetime(df_timeline["date"], errors="coerce", format="ISO8601")
    df_timeline = df_timeline.dropna(subset=["date"])

    if not df_timeline.empty:
        # Bucket by week
        df_timeline["week"] = df_timeline["date"].dt.to_period("W").apply(lambda r: r.start_time)

        df_weekly = df_timeline.groupby(["week", "status"]).size().reset_index(name="count")

        status_color_map = {
            "Applied": COLORS["applied"],
            "Interviewing": COLORS["interviewing"],
            "Offer": COLORS["offer"],
            "Rejected": COLORS["rejected"],
        }

        fig_timeline = px.bar(
            df_weekly,
            x="week",
            y="count",
            color="status",
            color_discrete_map=status_color_map,
            barmode="stack",
        )
        fig_timeline.update_layout(
            xaxis_title="Week",
            yaxis_title="Applications",
            font=dict(color="#E0E0E0", family="Inter, sans-serif"),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=320,
            margin=dict(t=30, b=40, l=40, r=20),
            xaxis=dict(gridcolor="rgba(255,255,255,0.1)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.1)"),
        )
        st.plotly_chart(fig_timeline, use_container_width=True)
    else:
        st.info("No timeline data available — dates couldn't be parsed.")
else:
    st.info("📝 Apply to jobs and update their status to populate your timeline.")


# --- Sidebar: Quick Navigation ---
with st.sidebar:
    st.subheader("📊 Analytics")
    st.caption("Visualize your job search funnel.")
    st.divider()

    if st.button("⬅️ Back to Dashboard", width="stretch"):
        st.switch_page("dashboard.py")
    
    st.divider()
    if st.button("🔄 Refresh Data", width="stretch"):
        st.cache_data.clear()
        st.rerun()
