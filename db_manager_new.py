# Fonction pour vider la table trades
def clear_trades_table():
    """Vide la table trades dans la base Supabase."""
    try:
        conn = get_pg_conn()
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE trades")
        conn.commit()
        conn.close()
        st.success("✅ Table trades vidée avec succès !")
    except Exception as e:
        st.error(f"❌ Erreur lors du vidage de la table : {e}")
        if conn:
            conn.close()
        raise

import pandas as pd
from sqlalchemy import create_engine, text
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import streamlit as st
from datetime import datetime
from config import POSTGRES_CONNECTION_URI

def process_trading_data(df):
    """Traite les données de trading pour les préparer pour la base de données"""
    try:
        # Copie du DataFrame pour éviter de modifier l'original
        df_processed = df.copy()
        
        # Extraction de l'heure et des minutes depuis Date/Time
        if 'Date/Time' in df_processed.columns:
            df_processed['datetime'] = pd.to_datetime(df_processed['Date/Time'])
            df_processed['hour'] = df_processed['datetime'].dt.hour
            df_processed['minute'] = df_processed['datetime'].dt.minute
            
        # Traitement de la date
        if 'Trade Date' in df_processed.columns:
            # Conversion explicite en date (sans composante heure) pour cohérence avec la colonne DATE
            df_processed['trade_date'] = pd.to_datetime(df_processed['Trade Date']).dt.date
            
        # Traitement des banques
        if 'Market Taker' in df_processed.columns:
            df_processed['taker_bank'] = df_processed['Market Taker']
        if 'Market Maker' in df_processed.columns:
            df_processed['maker_bank'] = df_processed['Market Maker']
            
        # Conversion des montants et taux
        if 'Montant' in df_processed.columns:
            df_processed['amount'] = pd.to_numeric(df_processed['Montant'])
        if 'Taux' in df_processed.columns:
            df_processed['rate'] = pd.to_numeric(df_processed['Taux'])
            
        # Nettoyage des colonnes temporaires
        cols_to_keep = ['trade_date', 'hour', 'minute', 'amount', 'rate', 'maker_bank', 'taker_bank']
        df_final = pd.DataFrame()
        
        for col in cols_to_keep:
            if col in df_processed.columns:
                df_final[col] = df_processed[col]
                
        # Validation finale
        required_cols = ['trade_date', 'hour', 'minute', 'amount', 'rate', 'maker_bank', 'taker_bank']
        for col in required_cols:
            if col not in df_final.columns:
                raise ValueError(f"Colonne manquante : {col}")
                
        return df_final
        
    except Exception as e:
        st.error(f"Erreur lors du traitement des données : {str(e)}")
        raise
    
    return df


# --- Configuration de la base de données Supabase ---


def get_pg_conn():
    """Retourne une connexion à la base de données Supabase"""
    return psycopg2.connect(POSTGRES_CONNECTION_URI)


def get_db_engine():
    """Retourne un moteur SQLAlchemy pour la base de données Supabase"""
    try:
        engine = create_engine(POSTGRES_CONNECTION_URI)
        return engine
    except Exception as e:
        st.error(f"Erreur de connexion à la base de données: {e}")
        raise

def create_tables(df):
    """Crée et remplit la table trades"""
    try:
        conn = get_pg_conn()
        cur = conn.cursor()
        
        # Création de la table PostgreSQL avec uniquement les colonnes nécessaires
        cur.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id SERIAL PRIMARY KEY,
            trade_date DATE,
            hour INTEGER,
            minute INTEGER,
            amount DOUBLE PRECISION,
            rate DOUBLE PRECISION,
            maker_bank TEXT,
            taker_bank TEXT
        )
        """)
        conn.commit()
        
        # Suppression des données existantes
        cur.execute("DELETE FROM trades")
        conn.commit()
        
        # Insertion des nouvelles données
        # Préparation des lignes pour insertion en lot (plus performant et atomique)
        rows = [
            (
                row['trade_date'],
                int(row['hour']),
                int(row['minute']),
                float(row['amount']),
                float(row['rate']),
                str(row['maker_bank']),
                str(row['taker_bank'])
            ) for _, row in df.iterrows()
        ]
        if rows:
            cur.executemany(
                """INSERT INTO trades (trade_date, hour, minute, amount, rate, maker_bank, taker_bank)
                VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                rows
            )
        
        conn.commit()
        # Vérification du nombre total de lignes après insertion
        cur2 = conn.cursor()
        cur2.execute("SELECT COUNT(*) FROM trades")
        total = cur2.fetchone()[0]
        cur2.close()
        cur.close()
        conn.close()
        st.success(f"✅ Données stockées avec succès ({total} lignes).")
    except Exception as e:
        st.error(f"❌ Erreur lors du stockage : {str(e)}")
        if conn:
            conn.close()
        raise

def store_data(df, engine):
    """Stocke les données dans la table trades"""
    try:
        # Traitement des données
        df_processed = process_trading_data(df)
        
        # Création/mise à jour de la table et insertion des données
        create_tables(df_processed)
        st.success(f"Données stockées avec succès!")
            
    except Exception as e:
        st.error(f"Erreur lors du stockage des données: {e}")
        raise

def load_data_from_db(engine):
    """Charge les données depuis PostgreSQL"""
    try:
        query = "SELECT * FROM trades"
        df = pd.read_sql(query, engine)
        
        # Conversion des colonnes de date/heure
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
        if 'trade_date' in df.columns:
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            
        return df
    except Exception as e:
        st.error(f"Erreur lors du chargement des données: {e}")
        raise

# ---------------------- Gestion des liens Grafana ----------------------
def ensure_grafana_table():
    """Crée la table grafana_links si elle n'existe pas."""
    try:
        conn = get_pg_conn()
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS grafana_links (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
            """
        )
        conn.commit()
        cur.close(); conn.close()
    except Exception as e:
        st.error(f"Erreur création table grafana_links: {e}")

def add_grafana_link(name: str, url: str):
    """Ajoute un lien Grafana."""
    ensure_grafana_table()
    if not (url.startswith("http://") or url.startswith("https://")):
        raise ValueError("URL invalide (doit commencer par http:// ou https://)")
    conn = get_pg_conn(); cur = conn.cursor()
    cur.execute("INSERT INTO grafana_links (name, url) VALUES (%s, %s)", (name.strip(), url.strip()))
    conn.commit(); cur.close(); conn.close()

def list_grafana_links():
    """Retourne les liens Grafana sous forme de liste de dict."""
    ensure_grafana_table()
    conn = get_pg_conn(); cur = conn.cursor()
    cur.execute("SELECT id, name, url, created_at FROM grafana_links ORDER BY created_at DESC")
    rows = cur.fetchall(); cur.close(); conn.close()
    return [
        {"id": r[0], "name": r[1], "url": r[2], "created_at": r[3]} for r in rows
    ]

def delete_grafana_link(link_id: int):
    """Supprime un lien Grafana par id."""
    conn = get_pg_conn(); cur = conn.cursor()
    cur.execute("DELETE FROM grafana_links WHERE id=%s", (link_id,))
    conn.commit(); cur.close(); conn.close()
