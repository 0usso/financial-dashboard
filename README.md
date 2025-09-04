# 📊 Tableau de Bord Financier Avancé

Dashboard interactif développé avec **Streamlit** pour analyser des transactions de change (ou tout flux de trades similaires) stockées dans une base **PostgreSQL (Supabase)**. Il permet d'uploader des fichiers Excel, de nettoyer/valider automatiquement les données, de les stocker en base, puis d'explorer :

- KPIs (montant, taux, etc.)
- Séries temporelles et distributions
- Répartition des volumes par Market Maker / Taker
- Evolution journalière, par minute et taux min/max
- Heatmaps (Maker x Heure, Maker ↔ Taker, Taux Heure x Minute)
- Intégration de dashboards **Grafana** via liens enregistrés
- Réinitialisation (TRUNCATE) de la table `trades`
- Nettoyage avancé des données (valeurs manquantes, normalisation banques, filtrage heures/minutes)

---
## 📁 Structure Simplifiée
```
financial_dashboard.py   # Application Streamlit (UI + visualisations)
db_manager_new.py        # Accès base, traitement & persistance des données
config.py                # URI PostgreSQL (Supabase)
requirements.txt         # Dépendances Python
README.md                # (ce fichier)
```

---
## ⚙️ Pré-requis
- Python 3.9+
- Compte Supabase (ou autre instance PostgreSQL) + chaîne de connexion
- Accès internet (pour déploiement ou Grafana public)

### Installation locale
```powershell
# Cloner le repo
git clone https://github.com/0usso/financial-dashboard.git
cd financial-dashboard

# Créer un venv (optionnel mais conseillé)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Installer dépendances
pip install -r requirements.txt
```

### Variable de configuration
Dans `config.py` (déjà présent) ou via variable d'environnement :
```python
POSTGRES_CONNECTION_URI = "postgresql://<user>:<password>@<host>:5432/<database>"
```
Si vous préférez utiliser une variable d'environnement :
```powershell
$env:POSTGRES_CONNECTION_URI = "postgresql://..."
```
(Et adapter `config.py` pour la lire depuis `os.getenv`).

---
## ▶️ Lancer l'application
```powershell
streamlit run financial_dashboard.py
```
Ouvrir ensuite le lien local (souvent http://localhost:8501).

---
## 📤 Chargement des Données
1. Préparez un fichier Excel avec au moins les colonnes (ou équivalents mappés) :
   - `Trade Date` / `Date`
   - `Montant` / `Amount` / `Volume`
   - `Taux` / `Rate`
   - `Market Maker` / `Maker Bank`
   - `Market Taker` / `Taker Bank`
   - Optionnel : `Date/Time` (pour extraire heure & minute automatiquement)
2. Déposez le fichier dans la sidebar.
3. Le pipeline : validation → traitement (`process_trading_data`) → insertion en base → affichage.

### Règles de validation principales
- Dates converties en `trade_date` (type date)
- `amount` et `rate` numériques (virgule ou point acceptés)
- `hour` 0–23 / `minute` 0–59 (remplis par 0 si absent)
- Noms de banques normalisés MAJUSCULES; valeurs vides → `UNKNOWN BANK`
- Lignes avec date / amount / rate manquants supprimées

---
## 📊 Visualisations
| Bloc | Description |
|------|-------------|
| KPIs | Dernières valeurs + delta % |
| Evolution temporelle | Courbes multi-métriques sur la période filtrée |
| Distribution | Boxplots des métriques sélectionnées |
| Pie Makers/Takers | Part de volume par banque (Maker puis Taker) |
| Evolution journalière | Barres volume + courbe nombre de transactions |
| Evolution minute | Volume et nombre de transactions minute par minute |
| Taux minute | Taux moyen + bande min/max |
| Heatmaps | Activité volumique et structure relationnelle |
| Données détaillées | Table filtrable (gradient) |

---
## 🔥 Heatmaps Ajoutées
1. **Maker x Heure** : où chaque maker concentre son volume.
2. **Matrix Maker ↔ Taker** : flux de volume entre paires (filtré Top N).
3. **Taux Moyen (Heure x Minute)** : microstructure intrajournalière.
Options configurables dans la sidebar.

---
## 📈 Grafana Intégré
- Ajoutez des liens (URL publiques / snapshots / kiosks) dans l'expander "Liens Grafana".
- Sélectionnez un lien pour l'embarquer (iframe).
- Les URLs `localhost` ne fonctionneront pas depuis d'autres appareils ou le cloud.

---
## 🧹 Maintenance / Réinitialisation
- Bouton TRUNCATE pour vider complètement `trades`.
- Invalide automatiquement le cache côté UI (pas de `@st.cache_data` sur le chargement principal pour éviter l'obsolescence).

---
## 🧪 Qualité & Idées d'Amélioration
Idées futures :
- Authentification utilisateur (Streamlit + JWT / Supabase Auth)
- Rôles & permissions (lecture seule vs admin)
- Export CSV / Excel des filtres appliqués
- Alertes (ex: taux > seuil) + notifications
- Benchmarks de latence d'insertion
- Tests unitaires pour `process_trading_data`
- Cache intelligent basé sur `COUNT(*)` + `MAX(trade_date)`

---
## 🚀 Déploiement (Streamlit Cloud)
1. Pousser le code sur GitHub.
2. Créer l'app sur share.streamlit.io.
3. Définir la variable secrète `POSTGRES_CONNECTION_URI` dans les Settings.
4. (Optionnel) Activer un thème personnalisé via `st.set_page_config` (déjà fait).
5. Si modifications de dépendances : mettre à jour `requirements.txt` et redéployer.

---
## 🛠 Dépannage Rapide
| Problème | Piste |
|----------|-------|
| Aucune donnée après upload | Vérifier colonnes mappées et messages d'erreur validation |
| KPIs / Graphiques vides | Table `trades` réellement vide ou filtres date trop restrictifs |
| Grafana ne s'affiche pas | URL locale, utiliser snapshot ou instance publique |
| Erreur connexion DB | Vérifier URI Supabase / IP autorisées / mot de passe |
| Valeurs bizarres dans heatmap | Vérifier montants dupliqués ou fuseaux horaires |

---
## 🔐 Sécurité
- Ne pas committer l'URI brute (utiliser secrets). 
- Eviter d'afficher le code source complet avec credentials dans le panneau debug en production.
- Ajouter plus tard : limitations sur les actions destructrices (confirmations multi-étapes / auth).

---
## 🤝 Contribution
1. Créer une branche feature: `git checkout -b feat/ma-fonction`
2. Commit clair: `git commit -m "feat: ajoute heatmap X"`
3. Push & PR.

---
## 📄 Licence
(Si besoin) Ajouter une licence open-source (ex: MIT) ou préciser usage interne.

---
## 🙋 Support
Questions / améliorations : ouvrir une *issue* GitHub ou contacter l'auteur du repo.

---
Bonnes analyses ! 🎯
