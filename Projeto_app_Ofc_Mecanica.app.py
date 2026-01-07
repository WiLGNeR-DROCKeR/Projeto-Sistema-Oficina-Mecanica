import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import os
import json
from datetime import datetime

# ==========================================
# 1. CONFIGURAÇÕES E IDENTIDADE VISUAL
# ==========================================
st.set_page_config(page_title="OficinaPro | Gestão Master", page_icon="🛠️", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');
html, body, [class*="css"] { font-family: 'Roboto', sans-serif; }
.stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left: 5px solid #007bff; }
[data-testid="stMetricValue"] { font-size: 24px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Credenciais Master (Secrets do Streamlit)
try:
    ADMIN_USER = st.secrets["admin_user"]
    ADMIN_PASS = st.secrets["admin_password"]
except:
    st.error("Erro: Configure 'admin_user' e 'admin_password' nos Secrets do Streamlit.")
    st.stop()

# ==========================================
# 2. CAMADA DE DADOS
# ==========================================
def conectar():
    return sqlite3.connect('oficina_mecanica_V2.db', check_same_thread=False)

def inicializar_db():
    conn = conectar(); cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, cargo TEXT, email TEXT UNIQUE,
        telefone TEXT, endereco TEXT, especializacoes TEXT, exp_anos TEXT,
        senha_hash TEXT, nivel_acesso TEXT, primeiro_acesso INTEGER DEFAULT 1,
        permissoes_gerente TEXT DEFAULT '[]')''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS estoque (
        id INTEGER PRIMARY KEY AUTOINCREMENT, peca TEXT, sku TEXT, quantidade INTEGER, 
        quantidade_minima INTEGER, valor_compra REAL, fornecedor TEXT, prazo_entrega TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS ordens_servico (
        id INTEGER PRIMARY KEY AUTOINCREMENT, carro_modelo TEXT, carro_marca TEXT, carro_placa TEXT, 
        carro_ano TEXT, descricao_problema TEXT, pecas_trocadas TEXT, id_mecanico TEXT, 
        status TEXT DEFAULT 'Pendente', valor_pecas REAL DEFAULT 0.0, 
        valor_mao_obra REAL DEFAULT 0.0, valor_comissao REAL DEFAULT 0.0, 
        bonificacao REAL DEFAULT 0.0, data_registro TEXT)''')
    conn.commit(); conn.close()

def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

inicializar_db()

# ==========================================
# 3. CONTROLE DE ACESSO E SESSÃO
# ==========================================
if 'logado' not in st.session_state:
    st.session_state.update({'logado': False, 'perfil': None, 'nome': None, 'permissoes': []})

if not st.session_state.logado:
    st.title("🔐 Portal OficinaPro")
    u = st.text_input("E-mail Profissional")
    p = st.text_input("Senha", type="password")
    
    if st.button("🚀 Entrar no Sistema"):
        if u == ADMIN_USER and p == ADMIN_PASS:
            st.session_state.update({'logado': True, 'perfil': "Admin", 'nome': "Administrador Geral"})
            st.rerun()
        else:
            conn = conectar(); cursor = conn.cursor()
            cursor.execute("SELECT nivel_acesso, nome, primeiro_acesso, email, permissoes_gerente FROM usuarios WHERE email=? AND senha_hash=?", 
                           (u, hash_senha(p)))
            res = cursor.fetchone(); conn.close()
            if res:
                perm_list = json.loads(res[4]) if res[4] else []
                st.session_state.update({
                    'logado': True, 'perfil': res[0], 'nome': res[1], 
                    'p_acesso': res[2], 'email_u': res[3], 'permissoes': perm_list
                })
                st.rerun()
            else: st.error("Credenciais inválidas.")

else:
    # Sidebar e Logout
    st.sidebar.markdown(f"### ⚙️ {st.session_state.perfil}")
    st.sidebar.write(f"Usuário: {st.session_state.nome}")

    # --- MENUS DINÂMICOS (CORRIGIDO) ---
    abas_disp = ["🏠 Início"]
    if st.session_state.perfil == "Admin":
        abas_disp += ["📋 Ordens de Serviço", "📦 Estoque", "💰 Financeiro", "⚙️ Administração"]
    elif st.session_state.perfil == "Gerente":
        # Se for gerente, mostra abas baseadas nas permissões salvas
        abas_disp += [a for a in ["📋 Ordens de Serviço", "📦 Estoque", "💰 Financeiro"] if a in st.session_state.permissoes]
    else:
        abas_disp += ["🛠️ Meus Serviços"]

    # LINHA CORRIGIDA (105):
    aba = st.sidebar.radio("Navegação", abas_disp)

    if aba == "🏠 Início":
        st.header(f"Dashboard Operacional - {st.session_state.nome}")
        c1, c2, c3 = st.columns(3)
        conn = conectar()
        os_p = pd.read_sql_query("SELECT COUNT(*) FROM ordens_servico WHERE status='Pendente'", conn).iloc[0,0]
        est_c = pd.read_sql_query("SELECT COUNT(*) FROM estoque WHERE quantidade <= quantidade_minima", conn).iloc[0,0]
        conn.close()
        c1.metric("Serviços Pendentes", os_p)
        c2.metric("Estoque Crítico", est_c, delta="-Reposição", delta_color="inverse")
        c3.metric("Integridade do Sistema", "100%")

    elif aba == "📋 Ordens de Serviço":
        st.header("📋 Gestão de Ordens Master")
        with st.expander("➕ Lançar Serviço com Financeiro"):
            with st.form("os_fin"):
                col1, col2 = st.columns(2)
                v_mod = col1.text_input("Veículo"); v_pla = col2.text_input("Placa")
                v_p = col1.number_input("Valor Peças (R$)", min_value=0.0)
                v_m = col2.number_input("Valor Mão de Obra (R$)", min_value=0.0)
                com = st.number_input("Comissão (R$)", min_value=0.0)
                if st.form_submit_button("Lançar"):
                    conn = conectar(); cursor = conn.cursor()
                    cursor.execute("""INSERT INTO ordens_servico 
                        (carro_modelo, carro_placa, valor_pecas, valor_mao_obra, valor_comissao, id_mecanico, data_registro) 
                        VALUES (?,?,?,?,?,?,?)""", (v_mod, v_pla, v_p, v_m, com, st.session_state.nome, datetime.now().strftime("%Y-%m-%d")))
                    conn.commit(); conn.close(); st.success("Serviço lançado!")

    elif aba == "💰 Financeiro":
        st.header("📊 Business Intelligence Financeiro")
        conn = conectar()
        df = pd.read_sql_query("SELECT valor_pecas, valor_mao_obra, valor_comissao FROM ordens_servico", conn)
        conn.close()
        if not df.empty:
            total_bruto = df['valor_pecas'].sum() + df['valor_mao_obra'].sum()
            lucro = total_bruto - df['valor_pecas'].sum() - df['valor_comissao'].sum()
            f1, f2, f3 = st.columns(3)
            f1.metric("Faturamento", f"R$ {total_bruto:,.2f}")
            f2.metric("Comissões", f"R$ {df['valor_comissao'].sum():,.2f}")
            f3.metric("Lucro Real", f"R$ {lucro:,.2f}")
            st.bar_chart(df[['valor_mao_obra', 'valor_comissao']])

    elif aba == "⚙️ Administração":
        st.header("⚙️ Painel do Administrador")
        t1, t2, t3 = st.tabs(["👥 Usuários", "🔑 Reset", "💾 Segurança"])
        with t1:
            with st.form("cad"):
                n = st.text_input("Nome"); e = st.text_input("E-mail"); c = st.selectbox("Cargo", ["Mecanico", "Gerente"])
                if st.form_submit_button("Cadastrar"):
                    conn = conectar(); cursor = conn.cursor()
                    cursor.execute("INSERT INTO usuarios (nome, email, cargo, nivel_acesso, senha_hash) VALUES (?,?,?,?,?)",
                                   (n, e, c, c, hash_senha("123456")))
                    conn.commit(); conn.close(); st.success("Cadastrado com senha 123456")
        with t3:
            if os.path.exists('oficina_mecanica_V2.db'):
                with open('oficina_mecanica_V2.db', 'rb') as f:
                    st.download_button("📥 Backup do Banco de Dados", f, file_name="oficina_backup.db")

    if st.sidebar.button("🚪 Sair"):
        st.session_state.logado = False
        st.rerun()
