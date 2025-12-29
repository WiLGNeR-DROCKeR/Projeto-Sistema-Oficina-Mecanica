import streamlit as st
import sqlite3
import json
import hashlib
import pandas as pd

# ==========================================
# 1. CONFIGURAÇÕES INICIAIS E SEGURANÇA
# ==========================================
st.set_page_config(page_title="OficinaPro - Gestão Especializada", layout="wide")

# Senhas administrativas vindas do Streamlit Cloud Secrets
ADMIN_USER = st.secrets["admin_user"]
ADMIN_PASS = st.secrets["admin_password"]

# ==========================================
# 2. CAMADA DE DADOS (DATABASE)
# ==========================================
def conectar():
    return sqlite3.connect('oficina_mecanica.db', check_same_thread=False)

def inicializar_db():
    conn = conectar()
    cursor = conn.cursor()
    # Tabela de Usuários (Ilimitada)
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT, cargo TEXT, email TEXT UNIQUE, telefone TEXT,
        especializacoes TEXT, senha_hash TEXT, nivel_acesso TEXT,
        permissoes_json TEXT)''')
    
    # Tabela de Estoque (Margem Vermelha)
    cursor.execute('''CREATE TABLE IF NOT EXISTS estoque (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        peca TEXT, quantidade INTEGER, quantidade_minima INTEGER,
        valor_compra REAL, fornecedor TEXT)''')

    # Tabela de Ordens de Serviço (Refatorada)
    cursor.execute('''CREATE TABLE IF NOT EXISTS ordens_servico (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        carro_modelo TEXT, carro_placa TEXT, id_mecanico INTEGER,
        pecas_sugeridas_mecanico TEXT, pecas_aprovadas_admin TEXT,
        valor_total REAL, comissao_percentual REAL, valor_comissao REAL,
        status_solicitacao TEXT DEFAULT 'Pendente',
        FOREIGN KEY(id_mecanico) REFERENCES usuarios(id))''')
    conn.commit()
    conn.close()

inicializar_db()

# ==========================================
# 3. LÓGICA DE NEGÓCIO
# ==========================================
def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def cadastrar_colaborador(nome, cargo, email, nivel, permissoes):
    conn = conectar()
    cursor = conn.cursor()
    senha_padrao = hash_senha("123456")
    try:
        cursor.execute("INSERT INTO usuarios (nome, cargo, email, nivel_acesso, senha_hash, permissoes_json) VALUES (?,?,?,?,?,?)",
                       (nome, cargo, email, nivel, senha_padrao, json.dumps(permissoes)))
        conn.commit()
        return True
    except: return False
    finally: conn.close()

# ==========================================
# 4. INTERFACE DO USUÁRIO (UI)
# ==========================================

# Controle de Sessão
if 'logado' not in st.session_state:
    st.session_state.logado = False
    st.session_state.perfil = None

# --- TELA DE LOGIN ATUALIZADA ---
if not st.session_state.logado:
    st.title("🔐 Acesso OficinaPro")
    user_input = st.text_input("E-mail")
    senha_input = st.text_input("Senha", type="password")
    
    if st.button("Entrar"):
        # 1. Verifica se é você (O Dono/Admin Geral)
        if user_input == ADMIN_USER and senha_input == ADMIN_PASS:
            st.session_state.logado = True
            st.session_state.perfil = "Admin"
            st.rerun()
        
        # 2. Se não for o admin do Secrets, busca no Banco de Dados
        else:
            conn = conectar()
            cursor = conn.cursor()
            hash_da_senha = hash_senha(senha_input)
            cursor.execute("SELECT nivel_acesso, nome FROM usuarios WHERE email = ? AND senha_hash = ?", 
                           (user_input, hash_da_senha))
            resultado = cursor.fetchone()
            conn.close()

            if resultado:
                st.session_state.logado = True
                st.session_state.perfil = resultado[0] # 'Mecanico' ou 'Gerente'
                st.session_state.nome_usuario = resultado[1]
                st.rerun()
            else:
                st.error("E-mail ou senha incorretos.")

else:
    # --- DASHBOARD PRINCIPAL ---
    st.sidebar.title(f"Perfil: {st.session_state.perfil}")
    aba = st.sidebar.radio("Navegação", ["Início", "Ordens de Serviço", "Estoque", "Administração"])

    if aba == "Início":
        st.header("Bem-vindo ao OficinaPro")
        st.write("Selecione uma opção no menu lateral para começar.")

    elif aba == "Ordens de Serviço":
        st.header("📋 Gestão de Ordens de Serviço")
        if st.session_state.perfil == "Admin":
            st.subheader("Solicitações de Peças Pendentes")
            # Aqui listaria as OS para aprovação com o cálculo de comissão
            st.info("Aguardando novas solicitações dos mecânicos...")
        else:
            st.subheader("Minhas Atividades")
            with st.form("nova_os"):
                st.write("Registrar Novo Serviço")
                carro = st.text_input("Modelo do Carro")
                placa = st.text_input("Placa")
                pecas = st.text_area("Peças Sugeridas (Descreva detalhadamente)")
                if st.form_submit_button("Enviar para Orçamento"):
                    st.success("Solicitação enviada ao Administrador!")

    elif aba == "Estoque":
        st.header("📦 Controle de Peças")
        # Simulação de Margem Vermelha
        st.warning("⚠️ Alerta: Pastilhas de Freio em nível crítico (2 unidades)!")

    elif aba == "Administração":
        if st.session_state.perfil == "Admin":
            st.header("⚙️ Painel do Administrador")
            tab1, tab2 = st.tabs(["Cadastrar Colaborador", "Relatórios"])
            
            with tab1:
                with st.form("cad_user"):
                    nome = st.text_input("Nome Completo")
                    email = st.text_input("E-mail")
                    cargo = st.selectbox("Cargo", ["Mecânico", "Gerente"])
                    st.write("Permissões de Acesso:")
                    p1 = st.checkbox("Pode dispensar Nota Fiscal")
                    p2 = st.checkbox("Ver comissões")
                    if st.form_submit_button("Salvar Cadastro"):
                        cadastrar_colaborador(nome, cargo, email, cargo, {"nf": p1, "comissao": p2})
                        st.success("Colaborador cadastrado!")
        else:
            st.error("Acesso negado.")

    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()
