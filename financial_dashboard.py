"""Entrée principale du tableau de bord financier (version modulaire)."""
import streamlit as st
import pandas as pd

from app.data_access import load_and_store_data, summary_by_date
from app.layout import render_kpis, line_and_box, makers_takers, daily_minute, heatmaps
from app.grafana import render_sidebar_block
from db_manager_new import clear_trades_table


def _safe_rerun():
    try:
        st.experimental_rerun()
    except Exception:
        pass


st.set_page_config(page_title="Dashboard Financier", layout="wide", page_icon="📊")

# -------------------- SIDEBAR: Upload & Grafana --------------------
st.sidebar.header("📥 Chargement des Données")
uploaded_file = st.sidebar.file_uploader("Fichier Excel (xlsx)", type=["xlsx","xls"], help="Les nouvelles données seront fusionnées dans la base.")

# Bloc liens Grafana
render_sidebar_block(_safe_rerun)

# -------------------- Chargement Données --------------------
df = load_and_store_data(uploaded_file)

if df is None:
    st.title("📊 Tableau de Bord Financier")
    st.info("Aucune donnée chargée. Uploade un fichier Excel pour commencer.")
    # Résumé historique si la base contient déjà des dates
    hist = summary_by_date()
    if hist is not None and not hist.empty:
        st.markdown("### 🗄️ Historique en Base")
        st.dataframe(hist, use_container_width=True)
    # Maintenance même si vide
    with st.sidebar.expander("🧹 Maintenance / Réinitialisation"):
        confirm_empty = st.checkbox("Confirmer suppression totale", key="confirm_reset_empty")
        if st.button("🗑️ Vider la base (TRUNCATE)"):
            if confirm_empty:
                try:
                    clear_trades_table(); _safe_rerun()
                except Exception as e:
                    st.error(e)
            else:
                st.warning("Coche la confirmation")
    st.stop()

# -------------------- En-tête --------------------
st.markdown("<h1>� Tableau de Bord Financier Avancé</h1>", unsafe_allow_html=True)
st.sidebar.success(f"✅ {len(df):,} transactions chargées")
st.sidebar.info(f"📅 Période: {df['trade_date'].min()} → {df['trade_date'].max()}")

# -------------------- Sélection métriques --------------------
available_metrics = ['amount','rate','hour','minute']
sel_metrics = st.sidebar.multiselect("Métriques", available_metrics, default=['amount','rate'])
if not sel_metrics:
    st.warning("Sélectionne au moins une métrique.")
    st.stop()

# -------------------- Visualisations --------------------
render_kpis(df, sel_metrics)
line_and_box(df, sel_metrics)
makers_takers(df)
daily_minute(df)
heatmaps(df)

# -------------------- Statistiques --------------------
st.markdown("### 📊 Statistiques Descriptives")
stats = df[sel_metrics].describe()
fmt = {'amount':'{:,.6f}','rate':'{:,.6f}','hour':'{:,.0f}','minute':'{:,.0f}'}
st.dataframe(stats.style.format({k:v for k,v in fmt.items() if k in sel_metrics}), use_container_width=True)

# -------------------- Données détaillées --------------------
st.markdown("### 📋 Données Détaillées")
st.dataframe(df.style.background_gradient(subset=sel_metrics, cmap='YlOrRd'), use_container_width=True)

# -------------------- Maintenance --------------------
with st.sidebar.expander("🧹 Maintenance / Réinitialisation (en ligne)"):
    confirm = st.checkbox("Confirmer suppression totale", key="confirm_reset_loaded")
    if st.button("🗑️ Vider la base maintenant"):
        if confirm:
            try:
                clear_trades_table(); _safe_rerun()
            except Exception as e:
                st.error(e)
        else:
            st.warning("Coche la confirmation")

st.caption("Version modulaire — code principal simplifié. ✨")
