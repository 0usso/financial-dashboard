"""Gestion des liens Grafana (extractions UI)."""
import streamlit as st
import os, sys, inspect
import db_manager_new as dbm

getattr(dbm, 'ensure_grafana_table', lambda: None)()
list_grafana_links = getattr(dbm, 'list_grafana_links', lambda: [])
add_grafana_link = getattr(dbm, 'add_grafana_link', None)
delete_grafana_link = getattr(dbm, 'delete_grafana_link', None)

def render_sidebar_block(rerun_func):
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
                            if 'selected_grafana_url' in st.session_state and st.session_state['selected_grafana_url']==item['url']:
                                st.session_state.pop('selected_grafana_url')
                            rerun_func()
                        except Exception as e:
                            st.error(f"Suppression impossible: {e}")
        else:
            st.caption("Aucun lien enregistré.")
        if add_grafana_link:
            with st.form("add_grafana_link_form", clear_on_submit=True):
                name = st.text_input("Nom", placeholder="Ex: Latence")
                url = st.text_input("URL Grafana", placeholder="https://...")
                if st.form_submit_button("Ajouter"):
                    if not name or not url:
                        st.warning("Nom et URL requis")
                    else:
                        try:
                            add_grafana_link(name, url)
                            st.success("Lien ajouté")
                            rerun_func()
                        except Exception as e:
                            st.error(f"Erreur ajout: {e}")
        else:
            st.info("Fonctions Grafana indisponibles")
