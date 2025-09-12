"""Composants de mise en page et graphiques."""
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

def render_kpis(df, metrics):
    st.markdown("### 📊 Indicateurs Clés de Performance")
    cols = st.columns(4)
    for i, m in enumerate(metrics[:4]):
        cur = df[m].iloc[-1]
        prev = df[m].iloc[-2] if len(df)>1 else cur
        delta = ((cur-prev)/prev*100) if prev else 0
        if m=='rate':
            val = f"{cur:,.6f}"
        elif m in ('hour','minute'):
            val = f"{int(cur)}"
        else:
            val = f"{cur:,.2f}"
        cols[i].metric(m, val, f"{delta:.1f}%")

def line_and_box(df, metrics):
    st.markdown("### 📈 Analyse Détaillée")
    c1,c2 = st.columns(2)
    with c1:
        if 'trade_date' in df:
            fig = go.Figure()
            for m in metrics:
                fig.add_trace(go.Scatter(x=df['trade_date'], y=df[m], name=m, mode='lines+markers'))
            fig.update_layout(title="Évolution Temporelle", template='plotly_white', height=400)
            st.plotly_chart(fig, use_container_width=True)
    with c2:
        figb = go.Figure()
        for m in metrics:
            figb.add_trace(go.Box(y=df[m], name=m, boxpoints='outliers'))
        figb.update_layout(title="Distribution et Outliers", template='plotly_white', height=400)
        st.plotly_chart(figb, use_container_width=True)

def makers_takers(df):
    st.markdown("### 📊 Analyse des Market Makers et Market Takers")
    c1,c2 = st.columns(2)
    with c1:
        st.subheader("Répartition des Market Makers")
        mk = df.groupby('maker_bank')['amount'].sum().sort_values(ascending=False)
        fig = go.Figure(data=[go.Pie(labels=mk.index, values=mk, hole=0.3)])
        fig.update_layout(title="Distribution du Volume par Market Maker", template='plotly_white', height=500)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(pd.DataFrame({'Volume':mk,'Pourcentage':(mk/mk.sum()*100).round(1)}).style.format({'Volume':'{:,.0f}','Pourcentage':'{:.1f}%'}))
    with c2:
        st.subheader("Répartition des Market Takers")
        tk = df.groupby('taker_bank')['amount'].sum().sort_values(ascending=False)
        fig2 = go.Figure(data=[go.Pie(labels=tk.index, values=tk, hole=0.3)])
        fig2.update_layout(title="Distribution du Volume par Market Taker", template='plotly_white', height=500)
        st.plotly_chart(fig2, use_container_width=True)
        st.dataframe(pd.DataFrame({'Volume':tk,'Pourcentage':(tk/tk.sum()*100).round(1)}).style.format({'Volume':'{:,.0f}','Pourcentage':'{:.1f}%'}))

def daily_minute(df):
    st.markdown("### 📈 Évolution Temporelle des Transactions")
    daily = df.groupby('trade_date')['amount'].agg(['sum','count']).reset_index()
    daily.columns=['Date','Volume','Nombre de Transactions']
    fig=go.Figure()
    fig.add_trace(go.Bar(x=daily['Date'], y=daily['Volume'], name='Volume', marker_color='#60a5fa'))
    fig.add_trace(go.Scatter(x=daily['Date'], y=daily['Nombre de Transactions'], yaxis='y2', name='Nombre de Transactions', line=dict(color='#f87171')))
    fig.update_layout(title="Évolution Journalière", template='plotly_white', yaxis2=dict(overlaying='y', side='right'))
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("### 📈 Évolution des Transactions par Minute")
    df['minute_key']=df['hour'].astype(str).str.zfill(2)+':'+df['minute'].astype(str).str.zfill(2)
    minute = df.groupby(['trade_date','minute_key'])['amount'].agg(['sum','count']).reset_index()
    minute.columns=['Date','Minute','Volume','Nombre']
    figm=go.Figure()
    figm.add_trace(go.Scatter(x=minute['Minute'], y=minute['Volume'], name='Volume', mode='lines+markers'))
    figm.add_trace(go.Scatter(x=minute['Minute'], y=minute['Nombre'], name='Transactions', yaxis='y2', mode='lines+markers'))
    figm.update_layout(title="Volume par Minute", template='plotly_white', yaxis2=dict(overlaying='y', side='right'), height=400)
    st.plotly_chart(figm, use_container_width=True)
    st.markdown("### 📈 Évolution du Taux par Minute")
    rates = df.groupby(['trade_date','minute_key'])['rate'].agg(['mean','min','max']).reset_index()
    rates.columns=['Date','Minute','Taux Moyen','Taux Min','Taux Max']
    figr=go.Figure()
    figr.add_trace(go.Scatter(x=rates['Minute'], y=rates['Taux Moyen'], name='Taux Moyen', mode='lines+markers'))
    figr.add_trace(go.Scatter(x=rates['Minute'], y=rates['Taux Max'], name='Taux Max', line=dict(width=0), showlegend=False))
    figr.add_trace(go.Scatter(x=rates['Minute'], y=rates['Taux Min'], name='Plage', fill='tonexty', fillcolor='rgba(96,165,250,0.2)', line=dict(width=0)))
    figr.update_layout(title="Taux par Minute", template='plotly_white', height=400)
    st.plotly_chart(figr, use_container_width=True)

def heatmaps(df):
    st.markdown("### 🔥 Heatmaps")
    with st.sidebar.expander("⚙️ Options Heatmaps"):
        top_n = st.slider("Top N banques (par volume)",5,30,15,1)
        show_rate = st.checkbox("Afficher Heatmap Taux", True)
        show_pair = st.checkbox("Afficher Matrix Maker/Taker", True)
        show_hour = st.checkbox("Afficher Volume Maker x Heure", True)
    def _limit(df_in, n):
        vols = df_in.groupby('maker_bank')['amount'].sum().sort_values(ascending=False)
        keep = vols.head(n).index
        return df_in[df_in['maker_bank'].isin(keep) & df_in['taker_bank'].isin(keep)]
    limited = _limit(df, top_n)
    import plotly.graph_objects as go
    if show_hour:
        st.subheader("Volume par Maker et Heure")
        pv = df.groupby(['maker_bank','hour'])['amount'].sum().reset_index()
        tbl = pv.pivot(index='maker_bank', columns='hour', values='amount').fillna(0)
        order = tbl.sum(axis=1).sort_values(ascending=False).index
        tbl = tbl.loc[order]
        fig=go.Figure(data=go.Heatmap(z=tbl.values,x=tbl.columns,y=tbl.index,colorscale='Viridis',colorbar=dict(title='Volume')))
        fig.update_layout(height=500, template='plotly_white')
        st.plotly_chart(fig, use_container_width=True)
    if show_pair:
        st.subheader("Matrix Volume Maker ↔ Taker")
        pr = limited.groupby(['maker_bank','taker_bank'])['amount'].sum().reset_index()
        tbl = pr.pivot(index='maker_bank', columns='taker_bank', values='amount').fillna(0)
        rows = tbl.sum(axis=1).sort_values(ascending=False).index
        cols = tbl.sum(axis=0).sort_values(ascending=False).index
        tbl = tbl.loc[rows, cols]
        fig=go.Figure(data=go.Heatmap(z=tbl.values,x=tbl.columns,y=tbl.index,colorscale='Blues',colorbar=dict(title='Volume')))
        fig.update_layout(height=600, template='plotly_white')
        st.plotly_chart(fig, use_container_width=True)
    if show_rate:
        st.subheader("Taux Moyen par Heure et Minute")
        pv = df.groupby(['hour','minute'])['rate'].mean().reset_index()
        tbl = pv.pivot(index='hour', columns='minute', values='rate')
        fig=go.Figure(data=go.Heatmap(z=tbl.values,x=tbl.columns,y=tbl.index,colorscale='RdYlGn',reversescale=True,colorbar=dict(title='Taux')))
        fig.update_layout(height=500, template='plotly_white')
        st.plotly_chart(fig, use_container_width=True)
