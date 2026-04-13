import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pickle
import time
import random

from delhi_traffic import (generate_traffic, get_traffic_label,
                            get_junction_info, JUNCTIONS)
from signal_optimizer import optimize_signals, get_dynamic_cycle_time
from traffic_flow import (apply_junction_flow, split_by_direction,
                           optimize_signals_by_direction,
                           get_current_green_direction,
                           get_flow_explanation)

st.set_page_config(
    page_title="Smart Traffic Light Digital Twin — Delhi",
    page_icon="🚦",
    layout="wide"
)

# ============================================================
# LOAD DATA
# ============================================================
@st.cache_resource
def load_model():
    with open('data/traffic_model.pkl', 'rb') as f:
        return pickle.load(f)

@st.cache_data
def load_stats():
    with open('data/model_stats.pkl', 'rb') as f:
        return pickle.load(f)

@st.cache_data
def load_historical():
    hour_avg    = pd.read_csv('data/hourly_avg.csv', index_col=0)['Vehicles']
    junc_avg    = pd.read_csv('data/junction_avg.csv', index_col=0)['Vehicles']
    hourday_avg = pd.read_csv('data/hourday_avg.csv')
    return hour_avg, junc_avg, hourday_avg

@st.cache_data
def load_traffic_data():
    df = pd.read_csv('data/traffic.csv')
    df['DateTime']    = pd.to_datetime(df['DateTime'])
    df['hour']        = df['DateTime'].dt.hour
    df['day_of_week'] = df['DateTime'].dt.dayofweek
    df['month']       = df['DateTime'].dt.month
    df['is_weekend']  = (df['day_of_week'] >= 5).astype(int)
    return df

model                           = load_model()
stats                           = load_stats()
hour_avg, junc_avg, hourday_avg = load_historical()
df                              = load_traffic_data()

# ============================================================
# HELPERS
# ============================================================
def build_time_features(hour, day_of_week):
    hist_hour = hour_avg.get(hour, hour_avg.mean())
    match = hourday_avg[
        (hourday_avg['hour'] == hour) &
        (hourday_avg['day_of_week'] == day_of_week)
    ]['Vehicles'].values
    hist_hourday = match[0] if len(match) > 0 else hist_hour
    hist_junc    = junc_avg.mean()
    day_avg      = hour_avg.mean()
    hour_ratio   = hist_hour / day_avg if day_avg > 0 else 1.0
    is_weekend   = 1 if day_of_week >= 5 else 0
    return [[hour, day_of_week, 6, is_weekend,
             hist_hour, hist_hourday, hist_junc, hour_ratio]]

def get_ml_prediction(hour, day_of_week):
    features = build_time_features(hour, day_of_week)
    pred     = model.predict(features)[0]
    proba    = model.predict_proba(features)[0][1]
    return pred, round(proba, 4)

def get_level_emoji(level):
    return {'HIGH': '🔴', 'MEDIUM': '🟡', 'LOW': '🟢'}[level]

def get_bar_color(level):
    return {'HIGH': '#e74c3c', 'MEDIUM': '#f39c12', 'LOW': '#2ecc71'}[level]

def get_peak_status(hour):
    if 8 <= hour <= 10:
        return "🚨 Morning Rush Hour", True
    elif 17 <= hour <= 20:
        return "🚨 Evening Peak Hour", True
    else:
        return "🙂 Normal Traffic Hours", False

def draw_history_graph(hour):
    hourly = df.groupby(['hour', 'Junction'])['Vehicles'].mean().reset_index()
    fig, ax = plt.subplots(figsize=(12, 3))
    colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12']
    jnames = ['ITO', 'Connaught Place', 'Lajpat Nagar', 'NH-48']
    for junc, col, name in zip([1, 2, 3, 4], colors, jnames):
        d = hourly[hourly['Junction'] == junc]
        ax.plot(d['hour'], d['Vehicles'], marker='o', label=name,
                color=col, linewidth=2, markersize=3)
    ax.axvspan(8,  10, alpha=0.1, color='red',    label='Morning rush')
    ax.axvspan(17, 20, alpha=0.1, color='orange', label='Evening peak')
    ax.axvline(hour, color='purple', linestyle='--',
               linewidth=2, label=f'Current ({hour:02d}:00)')
    ax.set_xlabel('Hour of Day')
    ax.set_ylabel('Average Vehicles')
    ax.set_title('Historical Traffic Pattern by Hour — Delhi Junctions')
    ax.legend(fontsize=7, ncol=4)
    ax.set_xticks(range(0, 24))
    ax.grid(True, alpha=0.3)
    st.pyplot(fig)
    plt.close()

def draw_over_time_graph():
    df_sample = (df[df['Junction'] == 1]
                   .sort_values('DateTime')
                   .iloc[::24].copy())
    fig, ax = plt.subplots(figsize=(12, 3))
    ax.plot(df_sample['DateTime'], df_sample['Vehicles'],
            color='#e74c3c', linewidth=1, alpha=0.8, label='ITO Junction')
    ax.fill_between(df_sample['DateTime'], df_sample['Vehicles'],
                    alpha=0.15, color='#e74c3c')
    ax.set_xlabel('Date')
    ax.set_ylabel('Vehicles')
    ax.set_title('Traffic Volume Over Time — ITO Junction (daily sample)')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=30)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

def render_core(j1, j2, j3, j4, hour, day_of_week, placeholders=None, sim_label=None):
    """Core render — metrics, ML, signals, explanation, profiles."""
    use_ph = placeholders is not None
    congestion_pred, congestion_proba = get_ml_prediction(hour, day_of_week)
    vehicle_counts = [j1, j2, j3, j4]
    opt = optimize_signals(vehicle_counts, congestion_proba)
    traffic_label       = get_traffic_label(hour)
    peak_label, is_peak = get_peak_status(hour)
    junction_names_list = [JUNCTIONS[f'junction_{i+1}']['name'] for i in range(4)]

    def draw_peak():
        if is_peak:
            st.warning(f"**{peak_label}** — {traffic_label}")
        else:
            st.info(f"**{peak_label}** — {traffic_label}")

    if use_ph:
        with placeholders['peak'].container():
            draw_peak()
    else:
        draw_peak()

    def draw_metrics():
        cols = st.columns(6)
        for i, (col, name, count) in enumerate(
                zip(cols[:4], junction_names_list, [j1,j2,j3,j4])):
            col.metric(name, f"{count} vehicles")
        cols[4].metric("Total", f"{j1+j2+j3+j4}")
        cols[5].metric("Hour",  f"{hour:02d}:00")

    if use_ph:
        with placeholders['metrics'].container():
            draw_metrics()
    else:
        draw_metrics()

    if use_ph:
        signal_con = placeholders['signals'].container()
    else:
        signal_con = st.container()

    with signal_con:
        left, right = st.columns([1, 2])
        with left:
            st.subheader("🤖 ML Prediction")
            proba_pct = round(congestion_proba * 100, 1)
            if congestion_pred == 1:
                if proba_pct >= 70:
                    st.error(f"🔴 CONGESTED — HIGH confidence ({proba_pct}%)")
                else:
                    st.warning(f"🟡 LIKELY CONGESTED — MODERATE ({proba_pct}%)")
            else:
                if proba_pct < 30:
                    st.success(f"🟢 NORMAL — HIGH confidence ({100-proba_pct:.1f}%)")
                else:
                    st.info(f"🟡 LIKELY NORMAL — MODERATE ({100-proba_pct:.1f}%)")
            st.markdown("**Congestion probability:**")
            st.progress(int(proba_pct))
            st.caption(f"{proba_pct}% chance of congestion at hour {hour:02d}:00")
            st.markdown("---")
            st.markdown(f"**Cycle:** `{opt['cycle_label']}` — `{opt['cycle_time']}s`")
            st.markdown("---")
            st.markdown("**Junction breakdown:**")
            for i, (name, lvl, cnt, gt) in enumerate(zip(
                    junction_names_list, opt['levels'], vehicle_counts, opt['green_times'])):
                emoji = get_level_emoji(lvl)
                jtype = JUNCTIONS[f'junction_{i+1}']['type']
                st.write(f"{emoji} **{name}** ({jtype}) — {cnt} veh → **{gt}s**")

        with right:
            st.subheader("🚦 Optimized Signal Timings")
            bar_colors = [get_bar_color(l) for l in opt['levels']]
            fig, ax = plt.subplots(figsize=(9, 4))
            bars = ax.bar(junction_names_list, opt['green_times'],
                          color=bar_colors, edgecolor='white', linewidth=1.5)
            for bar, val, lvl, cnt in zip(
                    bars, opt['green_times'], opt['levels'], vehicle_counts):
                ax.text(bar.get_x() + bar.get_width()/2,
                        bar.get_height() + 0.5,
                        f'{val}s\n{cnt} veh\n({lvl})',
                        ha='center', va='bottom', fontsize=9, fontweight='bold')
            ax.set_ylabel('Green light duration (seconds)')
            ax.set_title(
                f'Delhi Signal Optimization | Hour {hour:02d}:00 | '
                f'Cycle: {opt["cycle_time"]}s [{opt["cycle_label"]}]')
            ax.set_ylim(0, 80)
            ax.axhline(30, color='gray', linestyle='--', alpha=0.4)
            ax.set_facecolor('#f8f9fa')
            fig.patch.set_facecolor('#ffffff')
            st.pyplot(fig)
            plt.close()

    if use_ph:
        exp_con = placeholders['explanation'].container()
    else:
        exp_con = st.container()

    with exp_con:
        st.markdown("---")
        st.subheader("📐 Optimization Logic")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.markdown("**Cycle time:**")
            st.caption("• > 300 veh → 160s EXTENDED")
            st.caption("• > 200 veh → 120s NORMAL")
            st.caption("• > 100 veh → 100s MODERATE")
            st.caption("• ≤ 100 veh →  80s REDUCED")
        with col_b:
            st.markdown("**Green time formula:**")
            st.caption("green = (my veh / total) × cycle")
            if opt['ml_adjustment']:
                st.caption("🤖 ML bonus applied to busiest junction")
        with col_c:
            st.markdown("**Current decision:**")
            for line in opt['explanation']:
                st.caption(line)

    if use_ph:
        info_con = placeholders['info'].container()
    else:
        info_con = st.container()

    with info_con:
        st.markdown("---")
        st.subheader("🗺️ Delhi Junction Profiles")
        cols = st.columns(4)
        for i, (col, (key, junc)) in enumerate(zip(cols, JUNCTIONS.items())):
            with col:
                emoji = get_level_emoji(opt['levels'][i])
                st.markdown(f"**{junc['name']}**")
                st.caption(f"Type: {junc['type']}")
                st.caption(junc['description'])
                st.markdown(f"{emoji} {vehicle_counts[i]} vehicles")

    if use_ph and sim_label:
        placeholders['siminfo'].info(f"🔄 Simulating: **{sim_label}**")

def render_extras(j1, j2, j3, j4, hour, day_of_week):
    """Extras — only in manual mode. Connected flow, directions, intersection."""
    vehicle_counts = [j1, j2, j3, j4]
    _, congestion_proba = get_ml_prediction(hour, day_of_week)
    opt = optimize_signals(vehicle_counts, congestion_proba)
    junction_names_list = [JUNCTIONS[f'junction_{i+1}']['name'] for i in range(4)]
    junction_keys       = ['junction_1', 'junction_2', 'junction_3', 'junction_4']

    # Connected junctions
    st.markdown("---")
    st.subheader("🔗 Connected Junction Traffic Flow")
    st.caption("Vehicles flow between connected junctions")

    original_counts = {
        'junction_1': j1, 'junction_2': j2,
        'junction_3': j3, 'junction_4': j4
    }
    updated_counts = apply_junction_flow(original_counts)
    updated_list   = [updated_counts[k] for k in junction_keys]

    flow_cols = st.columns(4)
    arrows    = ['→', '→', '→', '↩']
    for i, (col, key, name, arrow) in enumerate(zip(
            flow_cols, junction_keys, junction_names_list, arrows)):
        orig = original_counts[key]
        upd  = updated_counts[key]
        diff = upd - orig
        with col:
            st.markdown(f"**{name}**")
            st.markdown(f"Before: `{orig}` veh")
            if diff > 0:
                st.markdown(f"After: `{upd}` ▲ +{diff}")
            elif diff < 0:
                st.markdown(f"After: `{upd}` ▼ {diff}")
            else:
                st.markdown(f"After: `{upd}`")
            st.caption(f"{arrow} flows to next")

    with st.expander("📋 Flow explanation"):
        for exp in get_flow_explanation(original_counts, updated_counts):
            st.markdown(f"- {exp}")
        st.caption("ITO→CP: 30% | CP→LN: 20% | LN→NH48: 25% | NH48→ITO: 15%")

    # Direction-based traffic
    st.markdown("---")
    st.subheader("🧭 Direction-Based Traffic & Signal Timing")
    st.caption("N, S, E, W — each direction gets proportional green time")

    direction_emojis = {'N': '⬆️', 'S': '⬇️', 'E': '➡️', 'W': '⬅️'}
    dir_cols = st.columns(4)

    for i, (col, key, name) in enumerate(zip(
            dir_cols, junction_keys, junction_names_list)):
        total      = updated_list[i]
        directions = split_by_direction(key, total)
        dir_green  = optimize_signals_by_direction(directions, opt['cycle_time'])
        green_dir  = get_current_green_direction(dir_green)
        with col:
            st.markdown(f"**{name}**")
            st.caption(f"Total: {total} veh")
            for direction in ['N', 'S', 'E', 'W']:
                count  = directions[direction]
                green  = dir_green[direction]
                signal = "🟢" if direction == green_dir else "🔴"
                emoji  = direction_emojis[direction]
                st.markdown(f"{signal} {emoji} **{direction}**: {count} → {green}s")

    # Intersection diagrams
    st.markdown("---")
    st.subheader("🚦 Live Intersection Diagrams")
    st.caption("🟢 = green direction | 🔴 = red")

    diag_cols = st.columns(4)
    for i, (col, key, name) in enumerate(zip(
            diag_cols, junction_keys, junction_names_list)):
        total      = updated_list[i]
        directions = split_by_direction(key, total)
        dir_green  = optimize_signals_by_direction(directions, opt['cycle_time'])
        green_dir  = get_current_green_direction(dir_green)
        n_sig = "🟢" if green_dir == 'N' else "🔴"
        s_sig = "🟢" if green_dir == 'S' else "🔴"
        e_sig = "🟢" if green_dir == 'E' else "🔴"
        w_sig = "🟢" if green_dir == 'W' else "🔴"
        with col:
            st.markdown(f"**{name}**")
            st.text(f"      {n_sig} N")
            st.text(f"      |")
            st.text(f"{w_sig} W--+--E {e_sig}")
            st.text(f"      |")
            st.text(f"      {s_sig} S")
            st.caption(f"🟢 Green: **{green_dir}** ({dir_green[green_dir]}s)")

# ============================================================
# HEADER — always visible
# ============================================================
st.title("🚦 Smart Traffic Light Digital Twin — Delhi")
st.markdown("### ML-driven congestion prediction with proportional signal optimization")

c1, c2, c3 = st.columns(3)
c1.metric("Model Accuracy",            f"{stats['model_acc']*100:.1f}%")
c2.metric("Baseline Accuracy",         f"{stats['baseline_acc']*100:.1f}%")
c3.metric("Improvement over baseline", f"+{stats['improvement']*100:.1f}%")
st.markdown("---")

# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.title("⚙️ Control Panel")

run_simulation = st.sidebar.checkbox("▶ Run Historical Simulation")
if run_simulation:
    sim_speed = st.sidebar.slider("Speed (seconds per step)", 0.05, 1.0, 0.15)

st.sidebar.markdown("---")
live_mode = st.sidebar.toggle("🔴 Enable Live Simulation Mode")
if live_mode:
    live_speed = st.sidebar.slider("Update interval (seconds)", 1, 5, 2)

st.sidebar.markdown("---")
st.sidebar.markdown("**Manual mode controls**")
if live_mode:
    st.sidebar.caption("⚠️ Disabled — Live mode active")
else:
    st.sidebar.caption("Adjust traffic at each Delhi junction")

hour = st.sidebar.slider("Hour of Day", 0, 23, 8)
day_of_week = st.sidebar.selectbox(
    "Day of Week", options=[0,1,2,3,4,5,6],
    format_func=lambda x: ['Monday','Tuesday','Wednesday',
                            'Thursday','Friday','Saturday','Sunday'][x]
)
st.sidebar.markdown("**Vehicle counts:**")
j1 = st.sidebar.slider("ITO",             0, 180, 80)
j2 = st.sidebar.slider("Connaught Place", 0, 180, 60)
j3 = st.sidebar.slider("Lajpat Nagar",    0, 180, 40)
j4 = st.sidebar.slider("NH-48",           0, 180, 30)

with st.expander("ℹ️ How this system works", expanded=False):
    st.markdown("""
    1. **ML (Random Forest)** — predicts congestion from time patterns
    2. **Dynamic Cycle Time** — total vehicles sets cycle length
    3. **Proportional Green Time** — each junction gets share of cycle
    4. **Connected Junctions** — vehicles flow ITO → CP → LN → NH48
    5. **Direction Signals** — N, S, E, W each get proportional green time
    """)

# ============================================================
# MODE DETECTION — strictly one mode at a time
# ============================================================
if run_simulation and not live_mode:
    mode = 'historical'
elif live_mode and not run_simulation:
    mode = 'live'
else:
    mode = 'manual'

# Store mode in session state — rerun when it changes
if 'current_mode' not in st.session_state:
    st.session_state.current_mode = mode

if st.session_state.current_mode != mode:
    st.session_state.current_mode = mode
    st.rerun()

# ============================================================
# MODE 1 — HISTORICAL SIMULATION
# ============================================================
main_container = st.empty()
if mode == 'historical':
    st.markdown("### 🔄 Simulation Mode — replaying historical data")

    df_sim = df.pivot_table(
        index=['DateTime','hour','day_of_week','month','is_weekend'],
        columns='Junction', values='Vehicles'
    ).reset_index().dropna()
    df_sim.columns = ['DateTime','hour','day_of_week','month',
                      'is_weekend','j1','j2','j3','j4']
    df_sim = df_sim.sort_values('DateTime').reset_index(drop=True)
    df_sim = df_sim.iloc[::6].reset_index(drop=True)

    progress_bar = st.progress(0)

    placeholders = {
        'peak':        st.empty(),
        'metrics':     st.empty(),
        'signals':     st.empty(),
        'explanation': st.empty(),
        'info':        st.empty(),
        'siminfo':     st.empty(),
    }

    for step, (_, row) in enumerate(df_sim.iterrows()):
        render_core(
            j1=int(row['j1']), j2=int(row['j2']),
            j3=int(row['j3']), j4=int(row['j4']),
            hour=int(row['hour']),
            day_of_week=int(row['day_of_week']),
            placeholders=placeholders,
            sim_label=str(row['DateTime'])
        )
        progress_bar.progress(min(int((step+1)/len(df_sim)*100), 100))
        time.sleep(sim_speed)

    st.success("✅ Simulation complete!")

# ============================================================
# MODE 2 — LIVE SIMULATION
# ============================================================
elif mode == 'live':
    st.markdown("### 🔴 Live Simulation Mode — Delhi Traffic")

    col_s, col_t = st.columns(2)
    with col_s:
        st.error(f"🔴 LIVE — Auto-updating every {live_speed} seconds")
    with col_t:
        st.info(f"🕐 Starting: **{hour:02d}:00** | "
                f"**{['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][day_of_week]}**")


    placeholders = {
        'peak':        st.empty(),
        'metrics':     st.empty(),
        'signals':     st.empty(),
        'explanation': st.empty(),
        'info':        st.empty(),
        'siminfo':     st.empty(),
    }

    live_step = 0
    while True:
        simulated_hour = (hour + live_step // 10) % 24
        traffic = generate_traffic(simulated_hour, day_of_week)
        lj1 = traffic['junction_1']['count']
        lj2 = traffic['junction_2']['count']
        lj3 = traffic['junction_3']['count']
        lj4 = traffic['junction_4']['count']

        render_core(
            j1=lj1, j2=lj2, j3=lj3, j4=lj4,
            hour=simulated_hour,
            day_of_week=day_of_week,
            placeholders=placeholders,
            sim_label=f"Live step {live_step+1} | Hour {simulated_hour:02d}:00"
        )
        live_step += 1
        time.sleep(live_speed)

# ============================================================
# MODE 3 — MANUAL MODE
# ============================================================
else:
    render_core(j1, j2, j3, j4, hour, day_of_week)
    render_extras(j1, j2, j3, j4, hour, day_of_week)
    st.markdown("---")
    st.subheader("📈 Historical Traffic Trend")
    tab1, tab2 = st.tabs(["By Hour of Day", "Over Time"])
    with tab1:
        draw_history_graph(hour)
    with tab2:
        draw_over_time_graph()

# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.caption(
    "Smart Traffic Light Digital Twin — Delhi | "
    "Python · Scikit-learn · Streamlit · Random Forest · "
    "Proportional Signal Optimization · Connected Junctions · Direction Signals"
)