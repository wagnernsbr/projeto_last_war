import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="VS TRACKER", layout="wide", initial_sidebar_state="expanded")

# Link da Planilha
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/17K3uwOjJd3lOKH8el6b1sMwJpBBCEu2MrHdOJXXhMgI/edit?usp=sharing"
ARQUIVO_MEMBROS = "lista_membros.csv"

# --- LÓGICA DE DATA ---
def obter_proxima_sexta():
    hoje = datetime.now()
    dias_ate_sexta = (4 - hoje.weekday() + 7) % 7
    if hoje.weekday() > 4: dias_ate_sexta = (4 - hoje.weekday() + 7) % 7
    return (hoje + timedelta(days=dias_ate_sexta)).strftime("%d/%m/%Y")

DATA_SUGERIDA = obter_proxima_sexta()

# --- ESTILO VISUAL ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    </style>
""", unsafe_allow_html=True)

# --- CARREGAMENTO DE DADOS BLINDADO ---
@st.cache_data(ttl=60) # Cache de 1 minuto para evitar o "pisca-pisca"
def carregar_dados():
    colunas_padrao = ["Jogador", "Poder (M)", "Time", "Status", "Tropa"]
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_online = conn.read(spreadsheet=URL_PLANILHA, ttl=0)
        
        if df_online is not None and not df_online.empty:
            # Padroniza nomes
            df_online = df_online.rename(columns={"Poder": "Poder (M)"})
            for col in colunas_padrao:
                if col not in df_online.columns: df_online[col] = "Nenhum"
            
            df_online["Poder (M)"] = pd.to_numeric(df_online["Poder (M)"].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
            df_online.to_csv(ARQUIVO_MEMBROS, index=False)
            return df_online
            
    except Exception as e:
        st.sidebar.error(f"Conexão falhou: {e}")
    
    # Se falhar, tenta ler local ou retorna vazio mas com estrutura correta
    if os.path.exists(ARQUIVO_MEMBROS):
        return pd.read_csv(ARQUIVO_MEMBROS)
    
    return pd.DataFrame(columns=colunas_padrao)

# Inicialização
if 'dados' not in st.session_state:
    st.session_state.dados = carregar_dados()

df = st.session_state.dados
ICONES = {"Tanque": "🚜", "Míssil": "🚀", "Aeronave": "✈️", "Nenhum": "❓"}

# --- MENU ---
aba = st.sidebar.radio("MENU", ["📊 Dashboard", "⚔️ Escalação Rápida"])

if st.sidebar.button("🔄 FORÇAR ATUALIZAÇÃO"):
    st.cache_data.clear()
    st.session_state.dados = carregar_dados()
    st.rerun()

# --- ABA DASHBOARD ---
if aba == "📊 Dashboard":
    st.title("🛡️ Painel de Comando")
    
    if df.empty:
        st.error("❌ ERRO DE ACESSO: A planilha está como 'Restrita'. Mude para 'Qualquer pessoa com o link' no Google Sheets!")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("PODER TOTAL", f"{df['Poder (M)'].sum():.1f} M")
        c2.metric("JOGADORES", len(df))
        c3.metric("TANQUES 🚜", len(df[df['Tropa'] == 'Tanque']))
        
        st.divider()
        st.subheader("🏆 Top 10 Elite")
        # Garantimos que o nlargest não quebre se o DF for menor que 10
        t10 = df.nlargest(min(len(df), 10), 'Poder (M)').copy()
        st.table(t10[['Jogador', 'Poder (M)', 'Tropa']])

# --- ABA ESCALAÇÃO ---
elif aba == "⚔️ Escalação Rápida":
    st.header("Centro de Escalação")
    if df.empty:
        st.warning("Aguardando dados da planilha...")
    else:
        st.write("Dados carregados com sucesso. Pronto para escalar!")
        # (Aqui você cola o restante da lógica de botões que já tínhamos)