import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Fresh Food Access Dashboard",
    layout="wide",
)

st.markdown("""
<style>
.stApp {
    background: linear-gradient(180deg, #0b1220 0%, #111827 100%);
    color: #e5efe9;
    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
}

h1, h2, h3 {
    color: #ecfdf5;
    font-weight: 650;
    letter-spacing: -0.02em;
}

p, div, label, span {
    color: #d1d5db;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #111827 100%);
    border-right: 1px solid rgba(74, 222, 128, 0.12);
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] label {
    color: #ecfdf5;
}

[data-testid="metric-container"] {
    background: rgba(17, 24, 39, 0.82);
    border: 1px solid rgba(74, 222, 128, 0.14);
    padding: 14px;
    border-radius: 16px;
    box-shadow: 0 8px 22px rgba(0, 0, 0, 0.28);
}

.stSelectbox > div > div {
    background-color: #111827;
    border-radius: 12px;
    border: 1px solid rgba(74, 222, 128, 0.16);
    color: #e5efe9;
}

.stDataFrame, [data-testid="stDataFrame"] {
    border-radius: 14px;
    overflow: hidden;
}

.block-container {
    padding-top: 1.8rem;
    padding-bottom: 2rem;
}

.soft-card {
    background: rgba(17, 24, 39, 0.82);
    border: 1px solid rgba(74, 222, 128, 0.14);
    border-radius: 18px;
    padding: 18px;
    box-shadow: 0 8px 22px rgba(0, 0, 0, 0.24);
}

.small-note {
    color: #9ca3af;
    font-size: 0.95rem;
}

hr {
    border: none;
    border-top: 1px solid rgba(74, 222, 128, 0.12);
    margin: 1rem 0 1.25rem 0;
}
</style>
""", unsafe_allow_html=True)

st.title("Fresh Food Access Dashboard")
st.caption("Neighborhood-level decision support for identifying communities facing elevated barriers to fresh food access in Atlanta.")

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "tract_level_food_access.geojson"
st.write("Reading data from:", DATA_PATH)

#@st.cache_data
def load_data(path: Path):
    gdf = gpd.read_file(path)

    numeric_cols = [
        "need_score",
        "TrcSNAP",
        "PvrtyRt",
        "LAhalf10",
        "food_business_count",
        "marta_access_count",
        "has_lila",
        "total_snap_stores",
        "high_access_count",
        "moderate_access_count",
        "specialty_access_count",
        "low_access_count",
        "other_snap_count",
        "low_access_ratio",
        "fresh_access_ratio"  
    ]

    for col in numeric_cols:
        if col in gdf.columns:
            gdf[col] = pd.to_numeric(gdf[col], errors="coerce")

    if "priority_level" not in gdf.columns and "priority_label" in gdf.columns:
        gdf["priority_level"] = gdf["priority_label"]

    if "priority_level" not in gdf.columns:
        gdf["priority_level"] = pd.qcut(
            gdf["need_score"].rank(method="first"),
            q=4,
            labels=["Low", "Moderate", "High", "Very High"],
        )

    if "need_score" in gdf.columns:
        gdf["need_score"] = gdf["need_score"].round(3)
    
    #if "access_problem_type" not in gdf.columns:
       # gdf["access_problem_type"] = "Not classified"

   # if "recommended_solution" not in gdf.columns:
    #    gdf["recommended_solution"] = "No recommendation available."

    if "reason" not in gdf.columns:
        def explain(row: pd.Series) -> str:
            reasons = []
            if row.get("TrcSNAP", 0) > 0.30:
                reasons.append("higher SNAP reliance")
            if row.get("PvrtyRt", 0) > 0.25:
                reasons.append("higher poverty burden")
            if row.get("food_business_count", 999) < 2:
                reasons.append("limited nearby food retail")
            if row.get("marta_access_count", 999) < 2:
                reasons.append("weaker transit connectivity")
            if not reasons:
                reasons.append("mixed access conditions")
            return ", ".join(reasons)

        gdf["reason"] = gdf.apply(explain, axis=1)

    return gdf


def build_hover_fields(df: pd.DataFrame, color_col: str) -> dict:
    base_fields = [
        "tract_id",
        "need_score",
        "priority_level",
        "TrcSNAP",
        "PvrtyRt",
        "LAhalf10",
        "food_business_count",
        "marta_access_count",
        "reason",
        "access_problem_type",
        "recommended_solution",
        "total_snap_stores",
        "low_access_ratio",
        "fresh_access_ratio",
        "low_access_count",
        "high_access_count"
    ]
    hover = {}
    for col in base_fields:
        if col in df.columns:
            hover[col] = True
    if color_col in hover:
        hover[color_col] = True
    return hover


if not DATA_PATH.exists():
    st.error(f"Processed file not found: {DATA_PATH}")
    st.stop()

tracts = load_data(DATA_PATH)

if "tract_id" not in tracts.columns:
    st.error("The dataset is missing a tract_id column.")
    st.stop()

map_options = [
    col for col in [
        "need_score",
        "priority_level",
        "TrcSNAP",
        "PvrtyRt",
        "LAhalf10",
        "marta_access_count",
        "food_business_count",
        "has_lila",
        "access_problem_type",
        "low_access_ratio",
        "fresh_access_ratio",
        "total_snap_stores",
        "low_access_count",
        "high_access_count"
    ] if col in tracts.columns
]

priority_values = []
if "priority_level" in tracts.columns:
    priority_values = tracts["priority_level"].astype(str).dropna().unique().tolist()

priority_options = ["All"] + [x for x in ["Very High", "High", "Moderate", "Low"] if x in priority_values]
tract_ids = ["All"] + sorted(tracts["tract_id"].astype(str).dropna().unique().tolist())

friendly_map_labels = {
    "need_score": "Composite need score",
    "priority_level": "Priority tier",
    "TrcSNAP": "SNAP participation rate",
    "PvrtyRt": "Poverty rate",
    "LAhalf10": "Low-access share",
    "marta_access_count": "Transit access points",
    "food_business_count": "Nearby food businesses",
    "has_lila": "LILA tract flag",
    "access_problem_type": "Access problem type",
    "low_access_ratio": "Convenience-store dependence",
    "fresh_access_ratio": "Fresh food retailer share",
    "total_snap_stores": "SNAP retailers",
    "low_access_count": "Low-access SNAP retailers",
    "high_access_count": "High-access SNAP retailers",
    "TrcSNAP": "SNAP households / measure"
}

with st.sidebar:
    st.header("Explore neighborhoods")
    selected_map_var = st.selectbox(
        "Map layer",
        map_options,
        index=0,
        format_func=lambda x: friendly_map_labels.get(x, x)
    )
    selected_priority = st.selectbox("Priority filter", priority_options, index=0)
    problem_values = sorted(tracts["access_problem_type"].astype(str).dropna().unique().tolist())
    problem_options = ["All"] + problem_values
    selected_problem = st.selectbox("Access issue filter", problem_options, index=0)
    selected_tract = st.selectbox("Specific tract", tract_ids, index=0)

filtered = tracts.copy()

if selected_priority != "All" and "priority_level" in filtered.columns:
    filtered = filtered[filtered["priority_level"].astype(str) == selected_priority]
if selected_problem != "All" and "access_problem_type" in filtered.columns:
    filtered = filtered[filtered["access_problem_type"].astype(str) == selected_problem]
if selected_tract != "All":
    filtered = filtered[filtered["tract_id"].astype(str) == selected_tract]

total_tracts = len(filtered)
very_high_count = (filtered["priority_level"].astype(str) == "Very High").sum() if "priority_level" in filtered.columns else 0
avg_score = filtered["need_score"].mean() if "need_score" in filtered.columns and len(filtered) else 0
lila_count = filtered["has_lila"].sum() if "has_lila" in filtered.columns else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Census tracts shown", f"{total_tracts}")
c2.metric("Very high priority", f"{very_high_count}")
c3.metric("Average need score", f"{avg_score:.2f}" if pd.notna(avg_score) else "N/A")
low_quality_count = (
    filtered["access_problem_type"].astype(str).eq("Low-Quality Access").sum()
    if "access_problem_type" in filtered.columns else 0
)

c4.metric("Low-quality access tracts", f"{int(low_quality_count)}")

map_col, detail_col = st.columns([2.35, 1], gap="large")

with map_col:
    st.subheader("Atlanta tract map")

    if filtered.empty:
        st.warning("No tracts match the current filters.")
    else:
        plot_df = filtered.copy()

        if selected_map_var == "priority_level":
            category_order = {"priority_level": ["Low", "Moderate", "High", "Very High"]}
            color_discrete_map = {
                "Low": "#14532d",
                "Moderate": "#65a30d",
                "High": "#f59e0b",
                "Very High": "#ef4444",
            }

            fig = px.choropleth_map(
                plot_df,
                geojson=json.loads(plot_df.to_json()),
                locations="tract_id",
                featureidkey="properties.tract_id",
                color="priority_level",
                category_orders=category_order,
                color_discrete_map=color_discrete_map,
                hover_data=build_hover_fields(plot_df, selected_map_var),
                center={"lat": 33.7490, "lon": -84.3880},
                zoom=9.5,
                opacity=0.84,
            )
        else:
            fig = px.choropleth_map(
                plot_df,
                geojson=json.loads(plot_df.to_json()),
                locations="tract_id",
                featureidkey="properties.tract_id",
                color=selected_map_var,
                color_continuous_scale=[
                    "#052e16",
                    "#166534",
                    "#65a30d",
                    "#f59e0b",
                    "#dc2626",
                ],
                hover_data=build_hover_fields(plot_df, selected_map_var),
                center={"lat": 33.7490, "lon": -84.3880},
                zoom=9.5,
                opacity=0.84,
            )

        fig.update_geos(fitbounds="locations", visible=False)
        fig.update_layout(
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            height=650,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e5efe9"),
            coloraxis_colorbar=dict(
                title=friendly_map_labels.get(selected_map_var, selected_map_var)
            ),
        )
        st.plotly_chart(fig, use_container_width=True)

with detail_col:
    st.subheader("Tract profile")

    if filtered.empty:
        st.info("No tract selected.")
    else:
        if selected_tract != "All" and len(filtered) == 1:
            tract_row = filtered.iloc[0]
        else:
            tract_row = filtered.sort_values("need_score", ascending=False).iloc[0]

        st.markdown('<div class="soft-card">', unsafe_allow_html=True)
        st.markdown("### Snapshot")

        st.markdown(f"**Tract ID:** {tract_row['tract_id']}")
        if "priority_level" in tract_row.index:
            st.markdown(f"**Priority tier:** {tract_row['priority_level']}")
        if "access_problem_type" in tract_row.index:
            st.markdown(f"**Access issue type:** {tract_row['access_problem_type']}")
        if "recommended_solution" in tract_row.index:
            st.markdown(f"**Recommended intervention:** {tract_row['recommended_solution']}")
        if "need_score" in tract_row.index and pd.notna(tract_row["need_score"]):
            st.markdown(f"**Composite need score:** {tract_row['need_score']:.3f}")
        if "TrcSNAP" in tract_row.index and pd.notna(tract_row["TrcSNAP"]):
            st.markdown(f"**SNAP participation rate:** {tract_row['TrcSNAP']:.3f}")
        if "PvrtyRt" in tract_row.index and pd.notna(tract_row["PvrtyRt"]):
            st.markdown(f"**Poverty rate:** {tract_row['PvrtyRt']:.3f}")
        if "total_snap_stores" in tract_row.index and pd.notna(tract_row["total_snap_stores"]):
            st.markdown(f"**SNAP retailers:** {int(tract_row['total_snap_stores'])}")
        if "low_access_ratio" in tract_row.index and pd.notna(tract_row["low_access_ratio"]):
            st.markdown(f"**Convenience-store dependence:** {tract_row['low_access_ratio']:.1%}")
        if "fresh_access_ratio" in tract_row.index and pd.notna(tract_row["fresh_access_ratio"]):
            st.markdown(f"**Fresh food retailer share:** {tract_row['fresh_access_ratio']:.1%}")
        if "food_business_count" in tract_row.index and pd.notna(tract_row["food_business_count"]):
            st.markdown(f"**Nearby food businesses:** {int(tract_row['food_business_count'])}")
        if "marta_access_count" in tract_row.index and pd.notna(tract_row["marta_access_count"]):
            st.markdown(f"**Transit access points:** {int(tract_row['marta_access_count'])}")
        if "reason" in tract_row.index:
            st.markdown(f"**Why this tract stands out:** {tract_row['reason']}")

        st.markdown('</div>', unsafe_allow_html=True)

st.subheader("Highest-priority tracts")

table_cols = [
    col for col in [
        "tract_id",
        "need_score",
        "priority_level",
        "TrcSNAP",
        "PvrtyRt",
        "LAhalf10",
        "food_business_count",
        "marta_access_count",
        "reason",
        "access_problem_type",
        "recommended_solution",
        "total_snap_stores",
        "low_access_ratio",
        "fresh_access_ratio",
        "low_access_count",
        "high_access_count",
    ] if col in filtered.columns
]

if not filtered.empty and "need_score" in filtered.columns:
    table_df = filtered[table_cols].sort_values("need_score", ascending=False).reset_index(drop=True)
    renamed_table_df = table_df.rename(columns={
        "tract_id": "Tract ID",
        "need_score": "Need Score",
        "priority_level": "Priority Tier",
        "TrcSNAP": "SNAP Rate",
        "PvrtyRt": "Poverty Rate",
        "LAhalf10": "Low Access",
        "food_business_count": "Food Businesses",
        "marta_access_count": "Transit Access",
        "reason": "Key Drivers",
        "access_problem_type": "Access Issue",
        "recommended_solution": "Recommended Intervention",
        "total_snap_stores": "SNAP Retailers",
        "low_access_ratio": "Convenience Dependence",
        "fresh_access_ratio": "Fresh Retail Share",
        "low_access_count": "Low Access Stores",
        "high_access_count": "High Access Stores",
    })
    st.dataframe(renamed_table_df, use_container_width=True, hide_index=True)
else:
    st.info("No table data to show for the current filters.")
