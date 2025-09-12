"""Accès base de données et chargement des données."""
import pandas as pd
import streamlit as st
from typing import Optional
from db_manager_new import get_pg_conn, get_db_engine, store_data

REQUIRED_COLS = ['trade_date', 'hour', 'minute', 'amount', 'rate', 'maker_bank', 'taker_bank']

def load_and_store_data(uploaded_file=None):
    """Charge éventuellement un fichier uploadé, le stocke et retourne les données courantes.
    Retourne None si échec.
    """
    engine = get_db_engine()
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            st.sidebar.success(f"✅ Fichier lu ({len(df)} lignes)")
            st.sidebar.dataframe(df.head(3))
            from .validation import validate_data
            if not validate_data(df):
                return None
            if not all(c in df.columns for c in REQUIRED_COLS):
                st.error("❌ Colonnes manquantes après validation")
                return None
            try:
                store_data(df, engine)
                st.sidebar.success("✅ Données stockées en base")
            except Exception as e:
                st.error(f"❌ Stockage impossible : {e}")
                return None
        except Exception as e:
            st.error(f"❌ Lecture fichier: {e}")
            return None
    # Charger depuis DB
    try:
        conn = get_pg_conn()
        df_db = pd.read_sql_query("SELECT trade_date, hour, minute, amount, rate, maker_bank, taker_bank FROM trades", conn)
        conn.close()
        if df_db.empty:
            st.warning("⚠️ Base vide.")
            return None
        df_db['trade_date'] = pd.to_datetime(df_db['trade_date']).dt.date
        return df_db
    except Exception as e:
        st.error(f"❌ Lecture base : {e}")
        return None

def summary_by_date():
    try:
        conn = get_pg_conn()
        q = """
        SELECT trade_date, COUNT(*) transactions, SUM(amount) volume_total,
               COUNT(DISTINCT maker_bank) nb_makers, COUNT(DISTINCT taker_bank) nb_takers
        FROM trades GROUP BY trade_date ORDER BY trade_date DESC
        """
        df = pd.read_sql_query(q, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Résumé impossible : {e}")
        return None
