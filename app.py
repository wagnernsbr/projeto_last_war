import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="VS TRACKER", layout="wide", initial_sidebar_state="expanded")

# --- LINK DA PLANILHA (Sincronizado com os 60.7M) ---
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/17K3uwOjJd3lOKH8el6b1sMwJpBBCEu2MrHdOJXXhMgI/edit?usp=sharing"

# Arquivos locais para Backup e Persistência
ARQUIVO_MEMBROS = "lista_membros.csv"
ARQUIVO_HISTORICO = "historico_escalacoes.csv"
ARQUIVO_MODELOS = "modelos_anuncio.csv"

# --- LÓGICA DE DATA ---
def obter_proxima_sexta():
    hoje = datetime.now()
    dias_ate_sexta = (4 - hoje.weekday() + 7) % 7
    if hoje.weekday() > 4: 
        dias_ate_sexta = (4 - hoje.weekday() + 7) % 7
    return (hoje + timedelta(days=dias_ate_sexta)).strftime("%d/%m/%Y")

DATA_SUGERIDA = obter_proxima_sexta()

# --- ESTILO VISUAL NEON ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: #0e1117; color: white; }}
    [data-testid="column"] {{ padding: 0px 2px !important; }}
    button[key="reset_a"] {{ background-color: #9c27b0 !important; color: white !important; border-radius: 12px !important; border: none !important; box-shadow: 0 0 15px rgba(156, 39, 176, 0.4) !important; }}
    button[key="reset_b"] {{ background-color: #2196f3 !important; color: white !important; border-radius: 12px !important; border: none !important; box-shadow: 0 0 15px rgba(33, 150, 243, 0.4) !important; }}
    div.stButton > button[key*="rem_tit_"] {{ border: 2px solid #00ff00 !important; box-shadow: 0 0 10px #00ff00 !important; background-color: #161b22 !important; }}
    div.stButton > button[key*="rem_res_"] {{ border: 2px solid #ffcc00 !important; box-shadow: 0 0 10px #ffcc00 !important; background-color: #161b22 !important; }}
    div.stButton > button[key*="add_"], div.stButton > button[key*="save_"], div.stButton > button[key*="edit_btn_"] {{ background-color: #4caf50 !important; color: white !important; border: none !important; }}
    div.stButton > button[key="save_history"] {{ background-color: #ff5722 !important; color: white !important; font-weight: bold !important; box-shadow: 0 0 15px rgba(255, 87, 34, 0.5) !important; border: none !important; }}
    </style>
""", unsafe_allow_html=True)

# --- CARREGAMENTO DE DADOS (ONLINE COM BACKUP LOCAL) ---
def carregar_dados():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_online = conn.read(spreadsheet=URL_PLANILHA, ttl=0)
        
        # Se a planilha vier vazia ou der erro, criamos um exemplo para o app não travar
        if df_online is None or df_online.empty:
            raise ValueError("Planilha vazia")

        # Garante que os nomes das colunas batem com o que o código espera
        if "Poder" in df_online.columns:
            df_online = df_online.rename(columns={"Poder": "Poder (M)"})
        
        # Preenche campos vazios para evitar erros visuais
        for col in ["Time", "Status", "Tropa"]:
            if col not in df_online.columns: df_online[col] = "Nenhum"
        
        df_online["Time"] = df_online["Time"].fillna("Nenhum")
        df_online["Status"] = df_online["Status"].fillna("Nenhum")
        
        # Guarda um backup local automático sempre que a internet funcionar
        df_online.to_csv(ARQUIVO_MEMBROS, index=False)
        return df_online
    except Exception as e:
        st.error(f"Conexão falhou: {e}")
        if os.path.exists(ARQUIVO_MEMBROS):
            return pd.read_csv(ARQUIVO_MEMBROS)
        # Se tudo falhar, retorna estrutura vazia para o dashboard não quebrar
        return pd.DataFrame(columns=["Jogador", "Poder (M)", "Time", "Status", "Tropa"])

def carregar_modelos():
    if os.path.exists(ARQUIVO_MODELOS):
        try:
            df_m = pd.read_csv(ARQUIVO_MODELOS)
            if not df_m.empty: return df_m.iloc[0].to_dict()
        except: pass
    return {"deserto": "🌵 {lista}", "meio": "📅 {lista}", "final": "⚔️ {lista}"}

# Inicialização do estado
if 'dados' not in st.session_state: st.session_state.dados = carregar_dados()
if 'modelos' not in st.session_state: st.session_state.modelos = carregar_modelos()

df = st.session_state.dados
ICONES = {"Tanque": "🚜", "Míssil": "🚀", "Aeronave": "✈️", "Nenhum": "❓"}

# --- MENU LATERAL ---
aba = st.sidebar.radio("MENU", ["📊 Dashboard", "⚔️ Escalação Rápida", "👤 Membros", "📜 Histórico", "📢 Anúncio"])

if st.sidebar.button("🔄 ATUALIZAR PLANILHA AGORA"):
    st.session_state.dados = carregar_dados()
    st.rerun()

# --- ABA: DASHBOARD ---
if aba == "📊 Dashboard":
    st.title("🛡️ Painel de Comando")
    if not df.empty:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("PODER TOTAL", f"{df['Poder (M)'].sum():.1f} M")
        c2.metric("JOGADORES", len(df))
        c3.metric("TANQUES 🚜", len(df[df['Tropa'] == 'Tanque']))
        c4.metric("MÍSSIL/AÉREO 🚀", len(df[df['Tropa'].isin(['Míssil', 'Aeronave'])]))
        st.divider()
        ce, cd = st.columns(2)
        with ce:
            st.subheader("🏆 Top 10 Elite")
            t10 = df.nlargest(10, 'Poder (M)').copy()
            t10['Info'] = t10.apply(lambda r: f"{ICONES.get(r['Tropa'], '')} {r['Jogador']}", axis=1)
            st.table(t10[['Info', 'Poder (M)']].reset_index(drop=True))
        with cd:
            st.subheader("📈 Distribuição")
            st.bar_chart(df['Tropa'].value_counts())
    else:
        st.error("Nenhum dado encontrado na planilha ou no backup.")

# --- ABA: ESCALAÇÃO RÁPIDA ---
elif aba == "⚔️ Escalação Rápida":
    st.header("Centro de Escalação")
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1: data_esc = st.text_input("Data da Batalha:", DATA_SUGERIDA)
    with c2: 
        if st.button("🚨 RESET TIME A", key="reset_a"):
            df.loc[df['Time'] == "Time A (18h)", ['Time', 'Status']] = "Nenhum"
            df.to_csv(ARQUIVO_MEMBROS, index=False); st.rerun()
    with c3:
        if st.button("🚨 RESET TIME B", key="reset_b"):
            df.loc[df['Time'] == "Time B (09h)", ['Time', 'Status']] = "Nenhum"
            df.to_csv(ARQUIVO_MEMBROS, index=False); st.rerun()
    st.divider()
    t_alvo = st.radio("Escalar no:", ["Time A (18h)", "Time B (09h)"], horizontal=True)
    s_alvo = st.radio("Categoria:", ["Titular", "Reserva"], horizontal=True)
    st.subheader("👤 Disponíveis (Poder)")
    disp = df[df['Time'] == "Nenhum"].sort_values(by="Poder (M)", ascending=False)
    if not disp.empty:
        cols = st.columns(8)
        for i, (idx, row) in enumerate(disp.iterrows()):
            with cols[i % 8]:
                lb = f"{ICONES.get(row['Tropa'], '')}\n{row['Jogador']}\n({row['Poder (M)']}M)"
                if st.button(lb, key=f"add_{row['Jogador']}"):
                    df.at[idx, 'Time'], df.at[idx, 'Status'] = t_alvo, s_alvo
                    df.to_csv(ARQUIVO_MEMBROS, index=False); st.rerun()
    st.divider()
    st.subheader(f"⚔️ {t_alvo} Atual")
    esc_at = df[df['Time'] == t_alvo].sort_values(by=["Status", "Poder (M)"], ascending=[False, False])
    if not esc_at.empty:
        cols_e = st.columns(8)
        for i, (idx, row) in enumerate(esc_at.iterrows()):
            tp = "tit" if row['Status'] == "Titular" else "res"
            pref = "🟢" if tp == "tit" else "🟡"
            with cols_e[i % 8]:
                if st.button(f"{pref} {row['Jogador']}\n({row['Poder (M)']}M)", key=f"rem_{tp}_{row['Jogador']}"):
                    df.at[idx, 'Time'], df.at[idx, 'Status'] = "Nenhum", "Nenhum"
                    df.to_csv(ARQUIVO_MEMBROS, index=False); st.rerun()

# --- ABA: MEMBROS ---
elif aba == "👤 Membros":
    st.header("👤 Gestão da Tropa")
    if 'edit_nome' not in st.session_state: st.session_state.edit_nome = ""
    if 'edit_poder' not in st.session_state: st.session_state.edit_poder = 0.0
    if 'edit_tropa' not in st.session_state: st.session_state.edit_tropa = "Tanque"
    with st.expander("📝 Cadastrar ou Editar Membro", expanded=True):
        c1, c2, c3 = st.columns([2, 1, 1])
        n_nome = c1.text_input("Nome", value=st.session_state.edit_nome)
        n_poder = c2.number_input("Poder (M)", step=0.1, value=st.session_state.edit_poder)
        n_tropa = c3.selectbox("Tropa", ["Tanque", "Míssil", "Aeronave"], index=["Tanque", "Míssil", "Aeronave"].index(st.session_state.edit_tropa))
        if st.button("💾 Salvar Localmente", key="save_membro"):
            df = df[df['Jogador'] != n_nome]
            n_v = pd.DataFrame([[n_nome, n_poder, "Nenhum", "Nenhum", n_tropa]], columns=df.columns)
            df = pd.concat([df, n_v], ignore_index=True)
            df.to_csv(ARQUIVO_MEMBROS, index=False); st.session_state.dados = df
            st.session_state.edit_nome = ""; st.session_state.edit_poder = 0.0; st.rerun()
    st.subheader("🔍 Localizar Membro")
    busca = st.text_input("Busque pelo nome...")
    df_f = df[df['Jogador'].str.contains(busca, case=False)] if busca else df.sort_values(by="Poder (M)", ascending=False)
    cols_m = st.columns(8)
    for i, (idx, row) in enumerate(df_f.iterrows()):
        with cols_m[i % 8]:
            if st.button(f"{ICONES.get(row['Tropa'], '')} {row['Jogador']}\n{row['Poder (M)']}M", key=f"edit_btn_{row['Jogador']}"):
                st.session_state.edit_nome = row['Jogador']; st.session_state.edit_poder = float(row['Poder (M)']); st.session_state.edit_tropa = row['Tropa']; st.rerun()

# --- ABA: HISTÓRICO ---
elif aba == "📜 Histórico":
    st.header("📜 Histórico de Guerras")
    if os.path.exists(ARQUIVO_HISTORICO):
        h_df = pd.read_csv(ARQUIVO_HISTORICO)
        if not h_df.empty:
            datas = sorted(h_df['Data'].unique(), reverse=True)
            d_sel = st.selectbox("Selecione a Data:", datas)
            filtro = h_df[h_df['Data'] == d_sel]
            ca, cb = st.columns(2)
            with ca:
                st.subheader("📍 TIME A (18h)")
                ta = filtro[filtro['Time'] == "Time A (18h)"].sort_values(by=["Status", "Poder (M)"], ascending=[False, False])
                st.table(ta[['Jogador', 'Poder (M)', 'Status']])
            with cb:
                st.subheader("📍 TIME B (09h)")
                tb = filtro[filtro['Time'] == "Time B (09h)"].sort_values(by=["Status", "Poder (M)"], ascending=[False, False])
                st.table(tb[['Jogador', 'Poder (M)', 'Status']])
            if st.button("🗑️ APAGAR DATA"):
                h_df[h_df['Data'] != d_sel].to_csv(ARQUIVO_HISTORICO, index=False); st.rerun()

# --- ABA: ANÚNCIO ---
elif aba == "📢 Anúncio":
    st.header("📢 Central de Anúncios")
    data_rel = st.text_input("Data da Guerra:", DATA_SUGERIDA)
    def gerar_lista():
        txt = ""
        for t in ["Time A (18h)", "Time B (09h)"]:
            sub = df[df['Time'] == t].sort_values(by=["Status", "Poder (M)"], ascending=[False, False])
            if not sub.empty:
                txt += f"📍 *{t.upper()}*\n"
                for _, r in sub.iterrows():
                    p = "🟢" if r['Status'] == "Titular" else "🟡"
                    txt += f"{p} {ICONES.get(r['Tropa'], '')} {r['Jogador']} ({r['Poder (M)']}M)\n"
                txt += "\n"
        return txt
    l_viva = gerar_lista()
    t1, t2, t3 = st.tabs(["🌵 Alistamento", "📅 Meio", "🏁 Final"])
    with t1: m1 = st.text_area("Alistamento:", st.session_state.modelos['deserto']); st.code(m1.replace("{lista}", l_viva))
    with t2: m2 = st.text_area("Meio da Semana:", st.session_state.modelos['meio']); st.code(m2.replace("{lista}", l_viva))
    with t3: m3 = st.text_area("Convocação Final:", st.session_state.modelos['final']); st.code(m3.replace("{lista}", l_viva))
    st.divider()
    c_b1, c_b2 = st.columns(2)
    with c_b1:
        if st.button("💾 SALVAR MODELOS"):
            pd.DataFrame([{"deserto": m1, "meio": m2, "final": m3}]).to_csv(ARQUIVO_MODELOS, index=False); st.success("Modelos salvos!")
    with c_b2:
        if st.button("🗄️ ARQUIVAR HISTÓRICO", key="save_history"):
            quem_vai = df[df['Time'] != "Nenhum"].copy(); quem_vai['Data'] = data_rel
            if os.path.exists(ARQUIVO_HISTORICO):
                h_at = pd.read_csv(ARQUIVO_HISTORICO); h_at = h_at[h_at['Data'] != data_rel]
                h_final = pd.concat([h_at, quem_vai], ignore_index=True)
            else: h_final = quem_vai
            h_final.to_csv(ARQUIVO_HISTORICO, index=False); st.success("Histórico arquivado!")