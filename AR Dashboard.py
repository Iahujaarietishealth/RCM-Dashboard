"""
RCM Note Intelligence Dashboard v2
====================================
Reads v8 analyzer output.

Pages (tabs at top):
  1. Overview — KPIs, outcome distribution, team donut, outcome×team matrix
  2. Team Analysis — team workload, heatmap, clickable team flow patterns with raw data
  3. Drill-Through — search by IncID, full claim journey

Run:  streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="RCM Note Intelligence", page_icon="📊", layout="wide")

TEAM_COLORS = {
    "AR Team": "#4A90D9", "Billing Team": "#7B68EE", "Coding Team": "#E8913A",
    "Payment Posting Team": "#2EAD6B", "PP Team": "#D94A7A", "EDI Team": "#5BC0BE",
    "Call Center": "#8B6DB0", "No Action": "#A0A0A0",
}
OUTCOME_COLORS = {
    "Claim billed/rebilled": "#4A90D9", "Claim billed to patient": "#2C6FAC",
    "Sent to PE team": "#D94A7A", "Sent to AR team": "#5B8BD4",
    "Sent to coding team": "#E8913A", "Sent for review": "#B07CD8",
    "Information request": "#7B68EE", "Appeal/inquiry sent": "#3AADE8",
    "Payment posted": "#2EAD6B", "Adjustment applied": "#43C47F",
    "Refund issued": "#1B8A54", "Writeoff applied": "#8B4513",
    "No action/allow time": "#A0A0A0", "Data/demo updated": "#9B8EC4",
    "Patient contacted": "#8B6DB0", "Info/data entry note": "#C0C0C0",
    "Untouched": "#D3D3D3",
}
KPI_COLORS = ["#4A90D9", "#2EAD6B", "#E8913A", "#D94A7A", "#7B68EE"]


# ═══════════════════════════════════════════════════════════
#  DATA
# ═══════════════════════════════════════════════════════════

@st.cache_data
def load_data(file):
    df = pd.read_excel(file, dtype=str) if hasattr(file, 'read') else pd.read_excel(file, dtype=str)
    for col in ["SLChg", "SLBal", "SLpmts", "SLadjs", "Total Touches", "TouchCount"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    for j in range(1, 8):
        if f"FinalOutcome{j}" not in df.columns: df[f"FinalOutcome{j}"] = "Untouched"
        if f"Category{j}" not in df.columns: df[f"Category{j}"] = "No Action"
    for col, default in [("CurrentOutcome", "Untouched"), ("CurrentCategory", "No Action"),
                          ("JourneyPath", "No activity"), ("CategoryPath", "No activity"), ("TouchCount", 0)]:
        if col not in df.columns: df[col] = default
    df["TouchCount"] = pd.to_numeric(df["TouchCount"], errors='coerce').fillna(0).astype(int)
    return df


def kpi_card(label, value, color="#4A90D9"):
    st.markdown(f"""
    <div style="background:linear-gradient(135deg, {color}22, {color}11);
                border:1px solid {color}44; border-radius:12px; padding:18px 14px;
                text-align:center; min-height:90px;">
        <div style="font-size:11px; color:{color}; font-weight:600; text-transform:uppercase;
                    letter-spacing:0.5px; margin-bottom:6px;">{label}</div>
        <div style="font-size:28px; font-weight:700; color:{color};">{value}</div>
    </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
#  LOAD & FILTER
# ═══════════════════════════════════════════════════════════

st.sidebar.title("🔍 Filters")
uploaded = st.sidebar.file_uploader("Upload v8 Output", type=["xlsx", "csv"])
uploaded="Output.xlsx"
if uploaded:
    df = load_data(uploaded)
else:
    st.info("👈 Upload your v8 output Excel file to begin")
    st.stop()

# Filters in sidebar
facilities = sorted([v for v in df["Facility"].dropna().unique() if v]) if "Facility" in df.columns and df["Facility"].notna().any() else []
fac_filter = st.sidebar.selectbox("Facility", ["All"] + facilities)

payers = sorted([v for v in df["PrimIns"].dropna().unique() if v]) if "PrimIns" in df.columns and df["PrimIns"].notna().any() else []
pay_filter = st.sidebar.selectbox("Payer", ["All"] + payers)

cat_options = sorted(df["CurrentCategory"].unique().tolist())
cat_filter = st.sidebar.multiselect("Team", cat_options, default=cat_options)

outcome_options = sorted(df["CurrentOutcome"].unique().tolist())
oc_filter = st.sidebar.multiselect("Outcome", outcome_options, default=outcome_options)

# Apply
mask = df["CurrentCategory"].isin(cat_filter) & df["CurrentOutcome"].isin(oc_filter)
if fac_filter != "All" and "Facility" in df.columns: mask &= df["Facility"] == fac_filter
if pay_filter != "All" and "PrimIns" in df.columns: mask &= df["PrimIns"] == pay_filter
df_f = df[mask]
st.sidebar.markdown(f"**{len(df_f)} / {len(df)} claims**")


# ═══════════════════════════════════════════════════════════
#  TABS AT TOP
# ═══════════════════════════════════════════════════════════

tab1, tab2, tab3 = st.tabs(["📊 Overview", "👥 Team Analysis", "🔎 Drill-Through"])


# ═══════════════════════════════════════════════════════════
#  TAB 1: OVERVIEW
# ═══════════════════════════════════════════════════════════

with tab1:
    st.markdown("### Overview")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: kpi_card("Total Claims", f"{len(df_f):,}", KPI_COLORS[0])
    with c2:
        bal = df_f["SLBal"].sum() if "SLBal" in df_f.columns and df_f["SLBal"].sum() > 0 else 0
        kpi_card("AR Balance", f"${bal:,.0f}" if bal else "N/A", KPI_COLORS[1])
    with c3: kpi_card("Avg Touches", f"{df_f['TouchCount'].mean():.1f}", KPI_COLORS[2])
    with c4:
        active=len(df_f)
        #active = len(df_f[~df_f["CurrentOutcome"].isin(["Untouched", "Payment posted", "Writeoff applied"])])
        kpi_card("Active Claims", f"{active:,}", KPI_COLORS[3])
    with c5:
        errs = len(df_f[df_f["CurrentOutcome"].str.startswith("Error", na=False)])
        kpi_card("Errors", f"{errs}", "#D94A4A" if errs > 0 else KPI_COLORS[4])

    st.markdown("")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Current Outcome Distribution")
        oc = df_f["CurrentOutcome"].value_counts().reset_index()
        oc.columns = ["Outcome", "Count"]
        oc = oc[~oc["Outcome"].isin(["Untouched", ""])]
        if not oc.empty:
            fig = px.bar(oc, y="Outcome", x="Count", orientation='h',
                         color="Outcome", color_discrete_map=OUTCOME_COLORS)
            fig.update_layout(showlegend=False, height=400, margin=dict(l=10,r=10,t=10,b=10),
                              yaxis=dict(categoryorder='total ascending'), plot_bgcolor="rgba(0,0,0,0)")
            fig.update_traces(texttemplate='%{x}', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("#### Current Team Distribution")
        tc = df_f["CurrentCategory"].value_counts().reset_index()
        tc.columns = ["Team", "Count"]
        tc = tc[tc["Team"] != "No Action"]
        if not tc.empty:
            fig2 = px.pie(tc, values="Count", names="Team", hole=0.5,
                          color="Team", color_discrete_map=TEAM_COLORS)
            fig2.update_layout(height=400, margin=dict(l=10,r=10,t=10,b=10))
            fig2.update_traces(textinfo='label+value', textfont_size=12)
            st.plotly_chart(fig2, use_container_width=True)

    # Outcome × Team Matrix
    st.markdown("#### Outcome × Team Matrix")
    merged = []
    for j in range(1, 8):
        for _, row in df_f.iterrows():
            oc_val = row.get(f"FinalOutcome{j}", "Untouched")
            cat_val = row.get(f"Category{j}", "No Action")
            if oc_val != "Untouched" and cat_val != "No Action":
                merged.append({"Outcome": oc_val, "Team": cat_val})
    if merged:
        m_df = pd.DataFrame(merged)
        cross = m_df.groupby(["Outcome", "Team"]).size().reset_index(name="Count")
        cross_pivot = cross.pivot_table(index="Outcome", columns="Team", values="Count", fill_value=0)
        fig3 = px.imshow(cross_pivot, color_continuous_scale="Blues", text_auto=True, aspect="auto",
                         labels=dict(x="Team", y="Outcome", color="Count"))
        fig3.update_layout(height=450, margin=dict(l=10,r=10,t=10,b=10))
        st.plotly_chart(fig3, use_container_width=True)
    
    # Touch count distribution
    st.markdown("#### Claim Complexity (Touches)")
    touch_df = df_f[df_f["TouchCount"] > 0]["TouchCount"].value_counts().sort_index().reset_index()
    touch_df.columns = ["Touches", "Claims"]
    if not touch_df.empty:
        fig3 = px.bar(touch_df, x="Touches", y="Claims", color_discrete_sequence=["#4A90D9"])
        fig3.update_layout(height=300, margin=dict(l=10,r=10,t=10,b=10), plot_bgcolor="rgba(0,0,0,0)",
                           xaxis=dict(dtick=1))
        st.plotly_chart(fig3, use_container_width=True)


# ═══════════════════════════════════════════════════════════
#  TAB 2: TEAM ANALYSIS
# ═══════════════════════════════════════════════════════════

with tab2:
    st.markdown("### Team Workload Analysis")

    all_cats = []
    for j in range(1, 8):
        vals = df_f[f"Category{j}"][df_f[f"Category{j}"] != "No Action"].tolist()
        all_cats.extend([(j, v) for v in vals])

    if all_cats:
        cat_df = pd.DataFrame(all_cats, columns=["NotePosition", "Team"])

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Total Work by Team")
            team_counts = cat_df["Team"].value_counts().reset_index()
            team_counts.columns = ["Team", "Actions"]
            fig = px.bar(team_counts, y="Team", x="Actions", orientation='h',
                         color="Team", color_discrete_map=TEAM_COLORS)
            fig.update_layout(showlegend=False, height=350, margin=dict(l=10,r=10,t=10,b=10),
                              yaxis=dict(categoryorder='total ascending'), plot_bgcolor="rgba(0,0,0,0)")
            fig.update_traces(texttemplate='%{x}', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("#### Team by Note Position")
            heat = cat_df.groupby(["NotePosition", "Team"]).size().reset_index(name="Count")
            heat_pivot = heat.pivot_table(index="Team", columns="NotePosition", values="Count", fill_value=0)
            heat_pivot.columns = [f"Note{c}" for c in heat_pivot.columns]
            fig2 = px.imshow(heat_pivot, color_continuous_scale="Purples", text_auto=True, aspect="auto")
            fig2.update_layout(height=350, margin=dict(l=10,r=10,t=10,b=10))
            st.plotly_chart(fig2, use_container_width=True)

    # ── Clickable Team Flow Patterns ──
    st.markdown("#### Team Flow Patterns")
    st.caption("Click a row to see the raw claims below")

    if "CategoryPath" in df_f.columns:
        active_paths = df_f[df_f["CategoryPath"] != "No activity"]
        paths = active_paths["CategoryPath"].value_counts().reset_index()
        paths.columns = ["Team Flow", "Count"]
        paths = paths.head(20)

        if not paths.empty:
            # Show clickable table
            selected_path = None
            for idx, row in paths.iterrows():
                col_a, col_b, col_c = st.columns([6, 1, 1])
                with col_a:
                    st.markdown(f"**{row['Team Flow']}**")
                with col_b:
                    st.markdown(f"`{row['Count']}`")
                with col_c:
                    if st.button("View", key=f"path_{idx}"):
                        selected_path = row["Team Flow"]

            # Show raw data for selected path
            if selected_path:
                st.markdown(f"---")
                st.markdown(f"##### Claims with flow: **{selected_path}**")
                matched = active_paths[active_paths["CategoryPath"] == selected_path]

                # Build display columns
                display_cols = []
                for c in ["AccountNum", "IncID", "PatientID", "Facility", "PrimIns",
                           "CPT", "ServiceDt", "CurrentOutcome", "CurrentCategory",
                           "TouchCount", "SLBal"]:
                    if c in matched.columns:
                        display_cols.append(c)
                # Add note columns
                for j in range(1, 8):
                    oc_col = f"FinalOutcome{j}"
                    cat_col = f"Category{j}"
                    if oc_col in matched.columns:
                        display_cols.extend([oc_col, cat_col])

                st.dataframe(
                    matched[display_cols],
                    use_container_width=True, hide_index=True,
                    height=min(500, 35 * len(matched) + 38)
                )
                st.markdown(f"**{len(matched)} claims** match this pattern")
    else:
        st.info("No CategoryPath data. Run v8 analyzer first.")


# ═══════════════════════════════════════════════════════════
#  TAB 3: DRILL-THROUGH
# ═══════════════════════════════════════════════════════════

with tab3:
    st.markdown("### Claim Drill-Through")

    # Search by IncID
    search_col = "IncID" if "IncID" in df_f.columns else "AccountNum" if "AccountNum" in df_f.columns else df_f.columns[0]
    search_options = sorted(df_f[search_col].dropna().unique().tolist())
    selected = st.selectbox(f"Search by {search_col}", [""] + search_options)

    if not selected:
        st.info(f"Select a {search_col} to view claim details")
        st.stop()

    row = df_f[df_f[search_col] == selected].iloc[0]

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Current Outcome", str(row.get("CurrentOutcome", "N/A")), "#4A90D9")
    with c2: kpi_card("Current Team", str(row.get("CurrentCategory", "N/A")), "#7B68EE")
    with c3: kpi_card("Touches", str(row.get("TouchCount", 0)), "#E8913A")
    with c4:
        bal = row.get("SLBal", 0)
        kpi_card("Balance", f"${float(bal):,.2f}" if bal else "N/A", "#2EAD6B")

    st.markdown("")

    # Claim details
    st.markdown("#### Claim Details")
    detail_map = {
        "Account": "AccountNum", "Incident": "IncID", "Patient": "PatientID",
        "Facility": "Facility", "Provider": "Rendering Provder", "Payer": "PrimIns",
        "CPT": "CPT", "DOS": "ServiceDt", "State": "State", "Charges": "SLChg",
    }
    details = {k: str(row.get(v, "")) for k, v in detail_map.items() if v in df_f.columns and str(row.get(v, "")) not in ["", "nan", "None"]}
    if details:
        st.dataframe(pd.DataFrame([details]), use_container_width=True, hide_index=True)

    # Journey timeline
    st.markdown("#### Claim Journey (Oldest → Newest)")
    note_col_map = {}
    for j in range(1, 8):
        if f"Note{j}" in df_f.columns: note_col_map[j] = f"Note{j}"
        elif j == 7:
            for fb in ["Note1.1", "Note 7"]:
                if fb in df_f.columns: note_col_map[j] = fb

    journey = []
    for j in range(7, 0, -1):
        ncol = note_col_map.get(j, f"Note{j}")
        note = str(row.get(ncol, ""))
        date = str(row.get(f"Note{j}Date", "")) if f"Note{j}Date" in df_f.columns else ""
        oc = row.get(f"FinalOutcome{j}", "Untouched")
        cat = row.get(f"Category{j}", "No Action")
        if note and note not in ["", "nan", "None"]:
            journey.append({
                "Step": f"Note {j}",
                "Date": date if date not in ["", "nan", "None"] else "-",
                "Outcome": oc,
                "Team": cat,
                "Note": note[:300],
            })

    if journey:
        st.dataframe(pd.DataFrame(journey), use_container_width=True, hide_index=True,
                      height=min(400, 35 * len(journey) + 38))

    # Paths
    col1, col2 = st.columns(2)
    with col1:
        jp = row.get('JourneyPath', 'N/A')
        st.markdown(f"**Outcome Path:** {jp}")
    with col2:
        cp = row.get('CategoryPath', 'N/A')
        st.markdown(f"**Team Path:** {cp}")


# ═══════════════════════════════════════════════════════════
st.sidebar.markdown("---")
st.sidebar.markdown("RCM Note Intelligence v8 · Arietis Health")
