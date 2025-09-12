"""Validation et nettoyage de données côté UI (complément du backend)."""
import pandas as pd
import streamlit as st

COLUMN_MAPPINGS = {
    'trade_date': ['Trade Date', 'Date'],
    'amount': ['Montant', 'Amount', 'Volume'],
    'rate': ['Taux', 'Rate'],
    'maker_bank': ['Market Maker', 'Maker Bank'],
    'taker_bank': ['Market Taker', 'Taker Bank']
}

def validate_data(df):
    try:
        dfp = df.copy()
        if 'Date/Time' in dfp.columns:
            try:
                dt = pd.to_datetime(dfp['Date/Time'])
                dfp['hour'] = dt.dt.hour
                dfp['minute'] = dt.dt.minute
            except Exception as e:
                st.error(f"Extraction heure impossible: {e}")
                return False
        for tgt, opts in COLUMN_MAPPINGS.items():
            for src in opts:
                if src in dfp.columns:
                    dfp[tgt] = dfp[src]
                    break
            if tgt not in dfp:
                st.error(f"Colonne manquante: {tgt}")
                return False
        dfp['trade_date'] = pd.to_datetime(dfp['trade_date']).dt.date
        def conv(v):
            return pd.to_numeric(v.astype(str).str.replace(',', '.'), errors='coerce')
        dfp['amount'] = conv(dfp['amount'])
        dfp['rate'] = conv(dfp['rate'])
        if dfp['amount'].isna().any() or dfp['rate'].isna().any():
            st.error("Valeurs numériques invalides")
            return False
        if 'hour' not in dfp: dfp['hour']=0
        if 'minute' not in dfp: dfp['minute']=0
        dfp['hour'] = dfp['hour'].astype(int); dfp['minute']=dfp['minute'].astype(int)
        if dfp['hour'].max()>23 or dfp['minute'].max()>59:
            st.error("Heures ou minutes hors plage")
            return False
        dfp['maker_bank'] = dfp['maker_bank'].fillna('UNKNOWN BANK')
        dfp['taker_bank'] = dfp['taker_bank'].fillna('UNKNOWN BANK')
        for c in dfp.columns:
            df[c] = dfp[c]
        return True
    except Exception as e:
        st.error(f"Erreur validation: {e}")
        return False
