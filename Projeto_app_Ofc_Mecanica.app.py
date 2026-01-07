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

# CSS Limpo para evitar erros de sintaxe no Python 3.13
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');
html, body, [class*="css"] { font-family: 'Roboto', sans-serif; }
.stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left: 5px solid #007bff; }
[data-testid="stMetricValue"] { font-size: 24px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Credenciais Master (Configuradas no Secrets do Streamlit)
ADMIN_USER = st.secrets["admin_user"]
ADMIN_PASS = st.secrets["admin_password"]

# ==========================================
# 2. CAMADA DE DADOS (DATABASE)
# ==========================================
def conectar():
    return sqlite3.connect('oficina_mecanica_V2.db', check_same_thread=False)

def inicializar_db():
    conn = conectar(); cursor = conn.cursor()
    # Tabela de Usuários (Sem limites de caracteres)
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, cargo TEXT, email TEXT UNIQUE,
        telefone TEXT, endereco TEXT, especializacoes TEXT, exp_anos TEXT,
        senha_hash TEXT, nivel_acesso TEXT, primeiro_acesso INTEGER DEFAULT 1,
        permissoes_gerente TEXT DEFAULT '[]')''')
    
    # Tabela de Estoque (Margem Vermelha e Fornecedores)
    cursor.execute('''CREATE TABLE IF NOT EXISTS estoque (
        id INTEGER PRIMARY KEY AUTOINCREMENT, peca TEXT, sku TEXT, quantidade INTEGER, 
        quantidade_minima INTEGER, valor_compra REAL, fornecedor TEXT, prazo_entrega TEXT)''')

    # Tabela de OS (Campos Financeiros e Detalhamento Técnico)
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
# 3. CONTROLE DE ACESSO
# ==========================================
if 'logado' not in st.session_state:
    st.session_state.update({'logado': False, 'perfil': None, 'nome': None, 'permissoes': []})

if not st.session_state.logado:
    st.title("🔐 Portal OficinaPro")
    u = st.text_input("E-mail Profissional")
    p = st.text_input("Senha de Acesso", type="password")
    
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
                st.session_state.update({
                    'logado': True, 'perfil': res[0], 'nome': res[1], 
                    'p_acesso': res[2], 'email_u': res[3], 'permissoes': json.loads(res[4])
                })
                st.rerun()
            else: st.error("Credenciais inválidas ou usuário inexistente.")

else:
    # Sidebar de Navegação
    st.sidebar.markdown(f"### ⚙️ {st.session_state.perfil}")
    st.sidebar.write(f"Usuário: {st.session_state.nome}")

    # --- Lógica de Menus Dinâmicos (Gerente/Mecânico) ---
    abas_disp = ["🏠 Início"]
    if st.session_state.perfil == "Admin":
        abas_disp += ["📋 Ordens de Serviço", "📦 Estoque", "💰 Financeiro", "⚙️ Administração"]
    elif st.session_state.perfil == "Gerente":
        # Gerente vê o que o Admin permitiu
        abas_disp += [a for a in ["📋 Ordens de Serviço", "📦 Estoque", "💰 Financeiro"] if a in st.session_state.permissoes]
    else:
        abas_disp += ["🛠️ Meus Serviços"]

    aba = st.sidebar.
