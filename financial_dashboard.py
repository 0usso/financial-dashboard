import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import os, sys
import streamlit.components.v1 as components

# Debug import db_manager_new pour afficher l'erreur réelle sur Streamlit Cloud
try:
    import db_manager_new as dbm
    get_pg_conn = dbm.get_pg_conn
    get_db_engine = dbm.get_db_engine
    create_tables = dbm.create_tables
    store_data = dbm.store_data
    # process_trading_data est utilisé côté backend (store_data) pour le nettoyage
    # clear_trades_table peut ne pas encore être présent sur le déploiement cloud
    if hasattr(dbm, "clear_trades_table"):
        clear_trades_table = dbm.clear_trades_table
    else:
        def clear_trades_table():
            st.info("Fallback: tentative de vidage direct de la table trades (fonction clear_trades_table absente dans db_manager_new).")
            try:
                conn = get_pg_conn()
                with conn.cursor() as cur:
                    cur.execute("TRUNCATE TABLE trades")
                conn.commit()
                conn.close()
                st.success("Table 'trades' vidée (fallback). Mettez à jour db_manager_new.py pour la fonction native.")
            except Exception as e:
                st.error(f"Échec du fallback TRUNCATE : {e}")

    # Fonctions Grafana (optionnelles)
    list_grafana_links = getattr(dbm, 'list_grafana_links', lambda: [])
    add_grafana_link = getattr(dbm, 'add_grafana_link', None)
    delete_grafana_link = getattr(dbm, 'delete_grafana_link', None)

    # Fallback en mémoire si les fonctions Grafana ne sont pas présentes dans le module (déploiement pas à jour)
    if add_grafana_link is None:
        if 'grafana_links_mem' not in st.session_state:
            st.session_state.grafana_links_mem = []  # liste de dict {id,name,url}
        def list_grafana_links():
            return st.session_state.grafana_links_mem
        def add_grafana_link(name, url):
            new_id = (max([l['id'] for l in st.session_state.grafana_links_mem]) + 1) if st.session_state.grafana_links_mem else 1
            st.session_state.grafana_links_mem.append({'id': new_id, 'name': name, 'url': url, 'created_at': None})
        def delete_grafana_link(link_id:int):
            st.session_state.grafana_links_mem = [l for l in st.session_state.grafana_links_mem if l['id'] != link_id]
        st.warning("Fonctions Grafana en base absentes : fallback mémoire (non persistant) utilisé.")
except Exception as e:
    st.error("⚠️ Erreur d'import de db_manager_new. Détails affichés ci-dessous.")
    import traceback
    st.code("\n".join([
        f"Working dir: {os.getcwd()}",
        f"Python: {sys.version}",
        f"Fichiers présents: {', '.join(os.listdir())}",
        "Traceback:",
        traceback.format_exc()
    ]))
    st.stop()

# Wrapper de rerun compatible versions Streamlit
def _safe_rerun():
    for attr in ("rerun", "experimental_rerun"):
        if hasattr(st, attr):
            try:
                getattr(st, attr)()
                return
            except Exception:
                continue
    st.warning("Impossible de relancer automatiquement l'application.")

# Configuration de la page avec un thème moderne
st.set_page_config(
    page_title="Analyse Financière Avancée",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Style CSS amélioré pour un look professionnel
st.markdown("""
    <style>
        .main {
            padding: 2rem;
            background-color: #f8f9fa;
        }
        .stPlot {
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            padding: 1.5rem;
            margin-bottom: 2rem;
        }
        h1 {
            color: #2c3e50;
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 2rem;
            text-align: center;
        }
        h2 {
            color: #34495e;
            font-size: 1.8rem;
            font-weight: 600;
            margin-top: 2rem;
        }
        h3 {
            color: #487eb0;
            font-size: 1.4rem;
        }
        .metric-card {
            background-color: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }
        .metric-value {
            font-size: 2rem;
            font-weight: bold;
            color: #2c3e50;
        }
        .metric-label {
            font-size: 1rem;
            color: #7f8c8d;
        }
        .stDataFrame {
            background-color: white;
            padding: 1rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
    </style>
""", unsafe_allow_html=True)

# Sidebar pour les filtres et le chargement de fichiers
st.sidebar.title("📊 Filtres et Options")

# Section liens Grafana
with st.sidebar.expander("📈 Liens Grafana"):
    existing = list_grafana_links()
    if existing:
        for item in existing:
            col_a, col_b, col_c = st.columns([4,1,1])
            with col_a:
                if st.button(f"▶ {item['name']}", key=f"sel_graf_{item['id']}"):
                    st.session_state['selected_grafana_url'] = item['url']
            with col_b:
                st.markdown(f"<a href='{item['url']}' target='_blank'>🌐</a>", unsafe_allow_html=True)
            with col_c:
                if delete_grafana_link and st.button("✖", key=f"del_graf_{item['id']}"):
                    try:
                        delete_grafana_link(item['id'])
                        # Nettoyer sélection si on supprime le lien actif
                        if 'selected_grafana_url' in st.session_state and st.session_state['selected_grafana_url'] == item['url']:
                            st.session_state.pop('selected_grafana_url')
                        _safe_rerun()
                    except Exception as e:
                        st.error(f"Suppression impossible: {e}")
    else:
        st.caption("Aucun lien enregistré.")

    if add_grafana_link:
        with st.form("add_grafana_link_form", clear_on_submit=True):
            name = st.text_input("Nom", placeholder="Ex: Dashboard Latence")
            url = st.text_input("URL Grafana", placeholder="https://...")
            submitted = st.form_submit_button("Ajouter")
            if submitted:
                try:
                    if not name or not url:
                        st.warning("Nom et URL requis.")
                    else:
                        add_grafana_link(name, url)
                        st.success("Lien ajouté.")
                        _safe_rerun()
                except Exception as e:
                    st.error(f"Erreur ajout: {e}")
    else:
        st.info("Fonctions Grafana non disponibles (mettez à jour db_manager_new.py).")

# Panneau debug Grafana (optionnel)
with st.sidebar.expander("🔧 Debug Grafana"):
    if 'dbm' in globals():
        if st.checkbox("Afficher les attributs de db_manager_new"):
            st.write(sorted([a for a in dir(dbm) if not a.startswith('_')]))
        if st.checkbox("Afficher le code source db_manager_new (attention aux infos sensibles)"):
            import inspect
            try:
                src = inspect.getsource(dbm)
                # Masquer éventuelle URI contenant mot de passe
                src = src.replace('postgresql://', 'postgresql://***masqué***@')
                st.code(src[:8000])  # tronquer pour éviter trop long
            except Exception as e:
                st.error(f"Impossible de lire le code: {e}")
    else:
        st.warning("Module db_manager_new non importé.")

# Zone principale d'affichage du dashboard Grafana sélectionné
if 'selected_grafana_url' in st.session_state:
    st.markdown("### 📺 Dashboard Grafana Intégré")
    raw_url = st.session_state['selected_grafana_url']
    # Tentative d'ajout param embed si absent
    embed_url = raw_url
    if ('embed' not in raw_url) and ('kiosk' not in raw_url):
        sep = '&' if '?' in raw_url else '?'
        embed_url = f"{raw_url}{sep}kiosk"
    height = st.sidebar.number_input("Hauteur iframe Grafana (px)", min_value=300, max_value=2000, value=800, step=50, key="grafana_iframe_height")
    st.caption(f"Affichage de : {embed_url}")
    # Détection URL locale non accessible depuis le cloud
    if any(host in embed_url for host in ["localhost", "127.0.0.1", "0.0.0.0"]):
        st.warning("L'URL pointe vers un Grafana local (localhost). Depuis un autre appareil ou le cloud, cette adresse n'est pas accessible.\n" 
                   "Solutions : 1) Utiliser l'URL publique de votre Grafana, 2) Créer un snapshot (Share > Snapshot), 3) Exposer Grafana via un tunnel (ngrok) ou hébergement public, 4) Activer une organisation avec partage anonyme.")
    else:
        try:
            components.iframe(embed_url, height=int(height), scrolling=True)
        except Exception as e:
            st.error(f"Impossible d'embarquer le dashboard. Ouvrez-le dans un nouvel onglet. Erreur: {e}")

# Section de chargement de fichier
st.sidebar.header("📂 Chargement des Données")
uploaded_file = st.sidebar.file_uploader(
    "Déposer votre fichier Excel",
    type=['xlsx', 'xls'],
    help="Formats acceptés : Excel (.xlsx, .xls)"
)

# Fonction de validation du fichier
def validate_data(df):
    try:
        # Faire une copie du DataFrame pour les transformations
        df_processed = df.copy()
        
        # Vérifier la présence de Date/Time pour extraire hour et minute
        if 'Date/Time' in df_processed.columns:
            try:
                df_processed['datetime'] = pd.to_datetime(df_processed['Date/Time'])
                df_processed['hour'] = df_processed['datetime'].dt.hour
                df_processed['minute'] = df_processed['datetime'].dt.minute
            except Exception as e:
                st.error(f"❌ Erreur lors de l'extraction de l'heure : {str(e)}")
                return None

        # Colonnes requises avec leur mappage
        column_mappings = {
            'trade_date': ['Trade Date', 'Date'],
            'amount': ['Montant', 'Amount', 'Volume'],
            'rate': ['Taux', 'Rate'],
            'maker_bank': ['Market Maker', 'Maker Bank'],
            'taker_bank': ['Market Taker', 'Taker Bank']
        }
        
        # Mappage des colonnes
        for target_col, possible_names in column_mappings.items():
            found = False
            for source_col in possible_names:
                if source_col in df_processed.columns:
                    df_processed[target_col] = df_processed[source_col]
                    found = True
                    break
            if not found:
                st.error(f"❌ Colonne manquante : {target_col}")
                st.write(f"Alternatives cherchées : {', '.join(possible_names)}")
                st.write(f"Colonnes disponibles : {', '.join(df_processed.columns)}")
                return None
        
        # Conversion des types
        try:
            # Conversion des dates
            df_processed['trade_date'] = pd.to_datetime(df_processed['trade_date']).dt.date
            
            # Conversion des valeurs numériques
            def convert_numeric(series):
                if series.dtype == object:  # Si c'est une chaîne de caractères
                    return pd.to_numeric(series.astype(str).str.replace(',', '.'), errors='coerce')
                return pd.to_numeric(series, errors='coerce')  # Sinon, conversion directe
            
            df_processed['amount'] = convert_numeric(df_processed['amount'])
            df_processed['rate'] = convert_numeric(df_processed['rate'])
            
            # Vérifier si la conversion a réussi
            if df_processed['amount'].isna().any():
                st.error("❌ Certaines valeurs de 'amount' ne sont pas des nombres valides")
                return None
            if df_processed['rate'].isna().any():
                st.error("❌ Certaines valeurs de 'rate' ne sont pas des nombres valides")
                return None
            
            # Gestion des colonnes hour et minute
            if 'hour' not in df_processed.columns:
                df_processed['hour'] = 0
            if 'minute' not in df_processed.columns:
                df_processed['minute'] = 0
                
            df_processed['hour'] = df_processed['hour'].astype(int)
            df_processed['minute'] = df_processed['minute'].astype(int)
            
            # Validation des plages
            if not (0 <= df_processed['hour'].max() <= 23):
                st.error("❌ Les heures doivent être entre 0 et 23")
                return None
            if not (0 <= df_processed['minute'].max() <= 59):
                st.error("❌ Les minutes doivent être entre 0 et 59")
                return None
            
            # Nettoyage des banques
            df_processed['maker_bank'] = df_processed['maker_bank'].fillna('UNKNOWN BANK')
            df_processed['taker_bank'] = df_processed['taker_bank'].fillna('UNKNOWN BANK')
            
            if not df_processed['maker_bank'].str.contains('BANK', case=False).all():
                st.error("❌ Certains Market Makers ne contiennent pas 'BANK'")
                return None
            if not df_processed['taker_bank'].str.contains('BANK', case=False).all():
                st.error("❌ Certains Market Takers ne contiennent pas 'BANK'")
                return None
            
            # Remplacer le DataFrame original
            for col in df_processed.columns:
                df[col] = df_processed[col]
            
            return True
            
        except Exception as e:
            st.error(f"❌ Erreur lors de la conversion des données : {str(e)}")
            st.write("Formats attendus :")
            st.write("- trade_date : date (YYYY-MM-DD)")
            st.write("- amount, rate : nombres décimaux (utiliser le point ou la virgule)")
            st.write("- hour : entier entre 0 et 23")
            st.write("- minute : entier entre 0 et 59")
            return None
    except Exception as e:
        st.error(f"❌ Erreur générale : {str(e)}")
        return None

# Fonction de chargement et stockage des données
def load_and_store_data(uploaded_file=None):
    engine = get_db_engine()
    
    # Si un fichier est uploadé
    if uploaded_file is not None:
        try:
            # Lecture du fichier
            df = pd.read_excel(uploaded_file)
            st.sidebar.success(f"✅ Fichier lu avec succès ({len(df)} lignes)")
            st.sidebar.write("🔍 Aperçu des données brutes :")
            st.sidebar.dataframe(df.head(3))
            
            # Debug des colonnes
            st.sidebar.write("📋 Colonnes trouvées :")
            st.sidebar.write(", ".join(df.columns))
            
            # Valider et transformer les données
            if not validate_data(df):
                return None
                
            # S'assurer que toutes les colonnes nécessaires sont présentes
            required_cols = ['trade_date', 'hour', 'minute', 'amount', 'rate', 'maker_bank', 'taker_bank']
            if not all(col in df.columns for col in required_cols):
                st.error("❌ Certaines colonnes sont manquantes après la validation")
                return None
                
            # Stocker dans la base
            try:
                store_data(df, engine)
                st.sidebar.success("✅ Données chargées avec succès dans la base de données!")
            except Exception as e:
                st.error(f"❌ Erreur lors du stockage : {str(e)}")
                return None
        except Exception as e:
            st.error(f"❌ Erreur lors du traitement du fichier : {str(e)}")
            return None
    
    # Dans tous les cas, on charge depuis la base
    try:
        conn = get_pg_conn()
        df = pd.read_sql_query("""
            SELECT trade_date, hour, minute, amount, rate, maker_bank, taker_bank 
            FROM trades
        """, conn)
        conn.close()
        
        if df.empty:
            st.warning("⚠️ Aucune donnée trouvée dans la base de données.")
            return None
        
        df['trade_date'] = pd.to_datetime(df['trade_date']).dt.date
        return df
        
    except Exception as e:
        st.error(f"❌ Erreur lors de la lecture depuis la base de données : {str(e)}")
        return None

# Chargement des données
df = load_and_store_data(uploaded_file)

# Affichage des informations sur les données
if df is not None and len(df) > 0:
    try:
        st.sidebar.info(f"📊 Nombre total de transactions : {len(df):,}")
        
        # Vérifier si la colonne trade_date existe
        if 'trade_date' in df.columns:
            min_date = df['trade_date'].min()
            max_date = df['trade_date'].max()
            st.sidebar.info(f"📅 Période : du {min_date} au {max_date}")
        else:
            st.sidebar.warning("⚠️ La colonne trade_date n'est pas disponible")

        # Section pour gérer l'historique des données
        st.sidebar.markdown("---")
        st.sidebar.header("🗄️ Gestion des Données")
    except Exception as e:
        st.error(f"Erreur lors de l'affichage des informations : {str(e)}")
else:
    st.warning("Aucune donnée n'a été chargée. Veuillez uploader un fichier.")

    # Afficher un résumé des données par date
    conn = get_pg_conn()
    summary_query = """
    SELECT 
        trade_date,
        COUNT(*) as transactions,
        SUM(amount) as volume_total,
        COUNT(DISTINCT maker_bank) as nb_makers,
        COUNT(DISTINCT taker_bank) as nb_takers
    FROM trades 
    GROUP BY trade_date 
    ORDER BY trade_date DESC
    """
    summary_df = pd.read_sql_query(summary_query, conn)
    conn.close()

    # Afficher le résumé
    if not summary_df.empty:
        st.sidebar.subheader("📅 Données stockées par date")
        for _, row in summary_df.iterrows():
            with st.sidebar.expander(f"📊 {row['trade_date'].strftime('%d/%m/%Y')}"):
                st.write(f"Transactions : {row['transactions']:,}")
                st.write(f"Volume total : {row['volume_total']:,.2f}")
                st.write(f"Nombre de makers : {row['nb_makers']}")
                st.write(f"Nombre de takers : {row['nb_takers']}")

    # Option pour réinitialiser la base de données (utilise clear_trades_table)
    with st.sidebar.expander("🧹 Maintenance / Réinitialisation"):
        st.write("Vider complètement la table 'trades'. Action irréversible.")
        confirm_reset = st.checkbox("Je confirme vouloir supprimer toutes les données", key="confirm_reset_empty_state")
        if st.button("🗑️ Vider la base (TRUNCATE)", help="Supprime toutes les lignes de la table trades"):
            if confirm_reset:
                try:
                    clear_trades_table()
                    # Nettoyage du cache de load_and_store_data si présent
                    if 'load_and_store_data' in globals():
                        try:
                            load_and_store_data.clear()
                        except Exception:
                            pass
                    _safe_rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")
            else:
                st.warning("Cochez la case de confirmation avant de lancer la suppression.")

if df is not None:
    # Titre principal
    st.markdown("<h1>📊 Tableau de Bord Financier Avancé</h1>", unsafe_allow_html=True)
    
    # Préparation des données
    # Définition des métriques disponibles (colonnes numériques de la table trades)
    available_metrics = ['amount', 'rate', 'hour', 'minute']
    
    # Sélection des colonnes à analyser dans la sidebar
    selected_metrics = st.sidebar.multiselect(
        "Sélectionner les métriques à analyser",
        options=available_metrics,
        default=['amount', 'rate']  # Métriques par défaut
    )
    
    # Vérification que des métriques sont sélectionnées
    if not selected_metrics:
        st.warning("Veuillez sélectionner au moins une métrique à analyser.")
        st.stop()  # Arrête l'exécution si aucune métrique n'est sélectionnée
    
    # Filtres temporels
    df['trade_date'] = pd.to_datetime(df['trade_date']).dt.date
    min_date = df['trade_date'].min()
    max_date = df['trade_date'].max()
    date_range = st.sidebar.date_input(
        "Sélectionner la période",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    # Filtrage des données selon la période sélectionnée
    if len(date_range) == 2:
        df_filtered = df[(df['trade_date'] >= date_range[0]) & 
                        (df['trade_date'] <= date_range[1])]
    else:
        df_filtered = df

    # KPIs dans des cartes élégantes
    st.markdown("### 📊 Indicateurs Clés de Performance")
    kpi_cols = st.columns(4)
    
    for idx, metric in enumerate(selected_metrics):
        if idx < 4:  # Limiter à 4 métriques pour l'affichage
            with kpi_cols[idx]:
                current_value = df_filtered[metric].iloc[-1]
                previous_value = df_filtered[metric].iloc[-2] if len(df_filtered) > 1 else current_value
                delta = ((current_value - previous_value) / previous_value * 100) if previous_value != 0 else 0
                # Format spécifique selon la métrique
                if metric == 'rate':
                    value_str = f"{current_value:,.6f}"  # 6 décimales demandées
                elif metric in ('hour', 'minute'):
                    try:
                        value_str = f"{int(current_value)}"
                    except Exception:
                        value_str = str(current_value)
                else:  # amount ou autre numérique
                    value_str = f"{current_value:,.2f}"  # défaut 2 décimales

                st.metric(label=metric, value=value_str, delta=f"{delta:.1f}%")

    # Graphiques avancés
    st.markdown("### 📈 Analyse Détaillée")
    
    # Première ligne de graphiques
    col1, col2 = st.columns(2)
    
    with col1:
        if 'trade_date' in df_filtered.columns:
            fig_line = go.Figure()
            for metric in selected_metrics:
                fig_line.add_trace(go.Scatter(
                    x=df_filtered['trade_date'],
                    y=df_filtered[metric],
                    name=metric,
                    mode='lines+markers'
                ))
            fig_line.update_layout(
                title="Évolution Temporelle",
                template="plotly_white",
                height=400
            )
            st.plotly_chart(fig_line, use_container_width=True)
    
    with col2:
        if len(selected_metrics) > 0:
            fig_box = go.Figure()
            for metric in selected_metrics:
                fig_box.add_trace(go.Box(
                    y=df_filtered[metric],
                    name=metric,
                    boxpoints='outliers'
                ))
            fig_box.update_layout(
                title="Distribution et Outliers",
                template="plotly_white",
                height=400
            )
            st.plotly_chart(fig_box, use_container_width=True)

    # Analyse des Market Makers et Market Takers
    st.markdown("### 📊 Analyse des Market Makers et Market Takers")
    col1, col2 = st.columns(2)

    # Distribution des Market Makers
    with col1:
        st.subheader("Répartition des Market Makers")
        maker_data = df_filtered.groupby('maker_bank')['amount'].sum().sort_values(ascending=False)
        maker_total = maker_data.sum()
        maker_pct = (maker_data / maker_total * 100).round(1)
        
        fig_maker = go.Figure(data=[go.Pie(
            labels=maker_data.index,
            values=maker_data,
            hole=0.3,
            textinfo='percent+label'
        )])
        
        fig_maker.update_layout(
            title="Distribution du Volume par Market Maker",
            showlegend=True,
            height=500,
            template="plotly_white"
        )
        
        st.plotly_chart(fig_maker, use_container_width=True)
        
        # Tableau des Market Makers
        maker_stats = pd.DataFrame({
            'Volume': maker_data,
            'Pourcentage': maker_pct
        })
        st.dataframe(maker_stats.style.format({
            'Volume': '{:,.0f}',
            'Pourcentage': '{:.1f}%'
        }))

    # Distribution des Market Takers
    with col2:
        st.subheader("Répartition des Market Takers")
        taker_data = df_filtered.groupby('taker_bank')['amount'].sum().sort_values(ascending=False)
        taker_total = taker_data.sum()
        taker_pct = (taker_data / taker_total * 100).round(1)
        
        fig_taker = go.Figure(data=[go.Pie(
            labels=taker_data.index,
            values=taker_data,
            hole=0.3,
            textinfo='percent+label'
        )])
        
        fig_taker.update_layout(
            title="Distribution du Volume par Market Taker",
            showlegend=True,
            height=500,
            template="plotly_white"
        )
        
        st.plotly_chart(fig_taker, use_container_width=True)
        
        # Tableau des Market Takers
        taker_stats = pd.DataFrame({
            'Volume': taker_data,
            'Pourcentage': taker_pct
        })
        st.dataframe(taker_stats.style.format({
            'Volume': '{:,.0f}',
            'Pourcentage': '{:.1f}%'
        }))

    # Évolution temporelle des transactions par jour
    st.markdown("### 📈 Évolution Temporelle des Transactions")
    
    # Agrégation par jour
    daily_volume = df_filtered.groupby('trade_date')['amount'].agg(['sum', 'count']).reset_index()
    daily_volume.columns = ['Date', 'Volume', 'Nombre de Transactions']
    
    # Création du graphique d'évolution journalière
    fig_evolution_daily = go.Figure()
    
    # Barres pour le volume
    fig_evolution_daily.add_trace(go.Bar(
        x=daily_volume['Date'],
        y=daily_volume['Volume'],
        name='Volume',
        marker_color='#60a5fa'
    ))
    
    # Ligne pour le nombre de transactions
    fig_evolution_daily.add_trace(go.Scatter(
        x=daily_volume['Date'],
        y=daily_volume['Nombre de Transactions'],
        name='Nombre de Transactions',
        yaxis='y2',
        line=dict(color='#f87171', width=2)
    ))
    
    # Mise en forme du graphique journalier
    fig_evolution_daily.update_layout(
        title="Évolution Journalière des Transactions",
        xaxis_title="Date",
        yaxis_title="Volume",
        yaxis2=dict(
            title="Nombre de Transactions",
            overlaying='y',
            side='right'
        ),
        template="plotly_white",
        showlegend=True,
        height=400
    )
    
    st.plotly_chart(fig_evolution_daily, use_container_width=True, key="daily_evolution")
    
    # Évolution par minute
    st.markdown("### 📈 Évolution des Transactions par Minute")
    
    # Préparation des données par minute
    df_filtered['minute_key'] = df_filtered['hour'].astype(str).str.zfill(2) + ':' + df_filtered['minute'].astype(str).str.zfill(2)
    
    # Agrégation par minute pour le volume et les transactions
    minute_volume = df_filtered.groupby(['trade_date', 'minute_key'])['amount'].agg(['sum', 'count']).reset_index()
    minute_volume.columns = ['Date', 'Minute', 'Volume', 'Nombre de Transactions']
    
    # Création du graphique d'évolution par minute (Volume et Transactions)
    fig_evolution_minute = go.Figure()
    
    # Ligne pour le volume
    fig_evolution_minute.add_trace(go.Scatter(
        x=minute_volume['Minute'],
        y=minute_volume['Volume'],
        name='Volume',
        mode='lines+markers',
        line=dict(color='#60a5fa', width=2)
    ))
    
    # Ligne pour le nombre de transactions
    fig_evolution_minute.add_trace(go.Scatter(
        x=minute_volume['Minute'],
        y=minute_volume['Nombre de Transactions'],
        name='Nombre de Transactions',
        yaxis='y2',
        mode='lines+markers',
        line=dict(color='#f87171', width=2)
    ))
    
    # Mise en forme du graphique par minute
    fig_evolution_minute.update_layout(
        title="Évolution du Volume par Minute",
        xaxis_title="Heure",
        yaxis_title="Volume",
        yaxis2=dict(
            title="Nombre de Transactions",
            overlaying='y',
            side='right'
        ),
        template="plotly_white",
        showlegend=True,
        height=400,
        xaxis=dict(
            tickangle=-45,
            tickmode='array',
            ticktext=minute_volume['Minute'].unique(),
            tickvals=minute_volume['Minute'].unique()
        )
    )
    
    st.plotly_chart(fig_evolution_minute, use_container_width=True, key="minute_evolution")
    
    # Évolution du taux par minute
    st.markdown("### 📈 Évolution du Taux par Minute")
    
    # Agrégation des taux par minute
    minute_rates = df_filtered.groupby(['trade_date', 'minute_key'])['rate'].agg(['mean', 'min', 'max']).reset_index()
    minute_rates.columns = ['Date', 'Minute', 'Taux Moyen', 'Taux Min', 'Taux Max']
    
    # Création du graphique d'évolution des taux
    fig_rate_minute = go.Figure()
    
    # Ligne pour le taux moyen
    fig_rate_minute.add_trace(go.Scatter(
        x=minute_rates['Minute'],
        y=minute_rates['Taux Moyen'],
        name='Taux Moyen',
        mode='lines+markers',
        line=dict(color='#60a5fa', width=2)
    ))
    
    # Zone pour min/max
    fig_rate_minute.add_trace(go.Scatter(
        x=minute_rates['Minute'],
        y=minute_rates['Taux Max'],
        name='Taux Max',
        mode='lines',
        line=dict(width=0),
        showlegend=False
    ))
    
    fig_rate_minute.add_trace(go.Scatter(
        x=minute_rates['Minute'],
        y=minute_rates['Taux Min'],
        name='Plage Min-Max',
        mode='lines',
        fill='tonexty',
        fillcolor='rgba(96, 165, 250, 0.2)',
        line=dict(width=0)
    ))
    
    # Mise en forme du graphique des taux
    fig_rate_minute.update_layout(
        title="Évolution du Taux par Minute",
        xaxis_title="Heure",
        yaxis_title="Taux",
        template="plotly_white",
        showlegend=True,
        height=400,
        xaxis=dict(
            tickangle=-45,
            tickmode='array',
            ticktext=minute_rates['Minute'].unique(),
            tickvals=minute_rates['Minute'].unique()
        )
    )
    
    st.plotly_chart(fig_rate_minute, use_container_width=True, key="rate_evolution")

    # ===================== HEATMAPS =====================
    st.markdown("### 🔥 Heatmaps")
    st.caption("Visualisation des concentrations d'activité et des relations entre banques.")

    # Paramètres optionnels dans la sidebar
    with st.sidebar.expander("⚙️ Options Heatmaps"):
        top_n_banks = st.slider("Top N banques (par volume)", 5, 30, 15, 1)
        show_rate_heatmap = st.checkbox("Afficher Heatmap Taux (Heure x Minute)", value=True)
        show_pair_heatmap = st.checkbox("Afficher Matrix Maker vs Taker", value=True)
        show_hour_maker_heatmap = st.checkbox("Afficher Volume (Maker x Heure)", value=True)

    # Helper pour limiter aux top N banques selon volume total
    def _limit_top_banks(df_in, top_n):
        vols = df_in.groupby('maker_bank')['amount'].sum().sort_values(ascending=False)
        keep = vols.head(top_n).index
        return df_in[df_in['maker_bank'].isin(keep) & df_in['taker_bank'].isin(keep)]

    limited_df = _limit_top_banks(df_filtered, top_n_banks)

    # 1. Heatmap Volume par Maker (lignes) et Heure (colonnes)
    if show_hour_maker_heatmap:
        st.subheader("Volume par Maker et Heure")
        try:
            pivot_vm = (df_filtered.groupby(['maker_bank','hour'])['amount']
                                   .sum().reset_index())
            table_vm = pivot_vm.pivot(index='maker_bank', columns='hour', values='amount').fillna(0)
            # Ordonner makers par volume total
            order = table_vm.sum(axis=1).sort_values(ascending=False).index
            table_vm = table_vm.loc[order]
            fig_vm = go.Figure(data=go.Heatmap(
                z=table_vm.values,
                x=table_vm.columns,
                y=table_vm.index,
                colorscale='Viridis',
                colorbar=dict(title='Volume')
            ))
            fig_vm.update_layout(height=500, xaxis_title='Heure', yaxis_title='Maker Bank', template='plotly_white')
            st.plotly_chart(fig_vm, use_container_width=True)
        except Exception as e:
            st.error(f"Erreur heatmap Maker x Heure : {e}")

    # 2. Heatmap Volume par paire Maker/Taker (matrix)
    if show_pair_heatmap:
        st.subheader("Matrix Volume Maker ↔ Taker (Top banques)")
        try:
            pair = (limited_df.groupby(['maker_bank','taker_bank'])['amount']
                               .sum().reset_index())
            table_pair = pair.pivot(index='maker_bank', columns='taker_bank', values='amount').fillna(0)
            # Réordonner l'axe selon volume total
            order_rows = table_pair.sum(axis=1).sort_values(ascending=False).index
            order_cols = table_pair.sum(axis=0).sort_values(ascending=False).index
            table_pair = table_pair.loc[order_rows, order_cols]
            fig_pair = go.Figure(data=go.Heatmap(
                z=table_pair.values,
                x=table_pair.columns,
                y=table_pair.index,
                colorscale='Blues',
                colorbar=dict(title='Volume')
            ))
            fig_pair.update_layout(height=600, xaxis_title='Taker Bank', yaxis_title='Maker Bank', template='plotly_white')
            st.plotly_chart(fig_pair, use_container_width=True)
        except Exception as e:
            st.error(f"Erreur heatmap paire Maker/Taker : {e}")

    # 3. Heatmap Taux moyen (Heure x Minute)
    if show_rate_heatmap:
        st.subheader("Taux Moyen par Heure et Minute")
        try:
            # Limiter nombre de minutes affichées si dataset très grand (sinon 24x60 stable)
            pivot_rate = (df_filtered.groupby(['hour','minute'])['rate']
                                       .mean().reset_index())
            table_rate = pivot_rate.pivot(index='hour', columns='minute', values='rate')
            fig_rate_hm = go.Figure(data=go.Heatmap(
                z=table_rate.values,
                x=table_rate.columns,
                y=table_rate.index,
                colorscale='RdYlGn',
                reversescale=True,
                colorbar=dict(title='Taux moyen')
            ))
            fig_rate_hm.update_layout(height=500, xaxis_title='Minute', yaxis_title='Heure', template='plotly_white')
            st.plotly_chart(fig_rate_hm, use_container_width=True)
        except Exception as e:
            st.error(f"Erreur heatmap taux heure/minute : {e}")
    # =================== FIN HEATMAPS ===================
    
    # Statistiques descriptives
    st.markdown("### 📊 Statistiques Descriptives")
    if len(selected_metrics) > 0:
        stats_df = df_filtered[selected_metrics].describe()
        
        # Formater chaque colonne en fonction de son type
        formatter = {
            'amount': '{:,.6f}',  # Format pour les montants
            'rate': '{:,.6f}',    # Format pour les taux
            'hour': '{:,.0f}',    # Format pour les heures (pas de décimales)
            'minute': '{:,.0f}'   # Format pour les minutes (pas de décimales)
        }
        
        # N'appliquer le format 6 décimales qu'aux colonnes sélectionnées
        format_dict = {col: formatter[col] for col in selected_metrics}
        
        st.dataframe(stats_df.style.format(format_dict), use_container_width=True)
    
    # Données brutes avec filtres
    # Bloc maintenance accessible même quand des données existent
    with st.sidebar.expander("🧹 Maintenance / Réinitialisation (en ligne)"):
        st.write("Vider la table 'trades' (irréversible).")
        confirm_reset_loaded = st.checkbox("Confirmer la suppression totale", key="confirm_reset_loaded_state")
        if st.button("🗑️ Vider la base maintenant", key="reset_loaded_btn"):
            if confirm_reset_loaded:
                try:
                    clear_trades_table()
                    if 'load_and_store_data' in globals():
                        try:
                            load_and_store_data.clear()
                        except Exception:
                            pass
                    _safe_rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")
            else:
                st.warning("Cochez la confirmation avant la suppression.")
    st.markdown("### 📋 Données Détaillées")
    st.dataframe(
        df_filtered.style.background_gradient(subset=selected_metrics, cmap='YlOrRd'),
        use_container_width=True
    )

else:
    st.error("Impossible de charger les données. Veuillez vérifier le chemin du fichier Excel.")
