import streamlit as st
import sqlite3
import json
import hashlib
import pandas as pd
import os

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
        nome TEXT, cargo TEXT, email TEXT UNIQUE,
        senha_hash TEXT, nivel_acesso TEXT,
        primeiro_acesso INTEGER DEFAULT 1)''')
    
    # Tabela de Estoque
    cursor.execute('''CREATE TABLE IF NOT EXISTS estoque (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        peca TEXT, quantidade INTEGER, quantidade_minima INTEGER,
        valor_compra REAL, fornecedor TEXT)''')

    # Tabela de Ordens de Serviço
    cursor.execute('''CREATE TABLE IF NOT EXISTS ordens_servico (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        carro_modelo TEXT, carro_placa TEXT, carro_ano TEXT, 
        descricao_problema TEXT, pecas_sugeridas_mecanico TEXT, 
        id_mecanico TEXT, status_solicitacao TEXT DEFAULT 'Pendente',
        valor_comissao REAL DEFAULT 0.0)''')
    conn.commit()
    conn.close()

inicializar_db()

# ==========================================
# 3. LÓGICA DE NEGÓCIO
# ==========================================
def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

# ==========================================
# 4. INTERFACE DO USUÁRIO (UI)
# ==========================================

if 'logado' not in st.session_state:
    st.session_state.logado = False
    st.session_state.perfil = None

# --- TELA DE LOGIN ---
if not st.session_state.logado:
    st.title("🔐 Acesso OficinaPro")
    user_input = st.text_input("E-mail")
    senha_input = st.text_input("Senha", type="password")
    
    if st.button("Entrar"):
        if user_input == ADMIN_USER and senha_input == ADMIN_PASS:
            st.session_state.logado = True
            st.session_state.perfil = "Admin"
            st.rerun()
        else:
            conn = conectar()
            cursor = conn.cursor()
            h_senha = hash_senha(senha_input)
            cursor.execute("SELECT nivel_acesso, nome, primeiro_acesso, email FROM usuarios WHERE email = ? AND senha_hash = ?", 
                           (user_input, h_senha))
            res = cursor.fetchone()
            conn.close()

            if res:
                st.session_state.logado = True
                st.session_state.perfil = res[0]
                st.session_state.nome_usuario = res[1]
                st.session_state.primeiro_acesso = res[2]
                st.session_state.email_usuario = res[3]
                st.rerun()
            else:
                st.error("E-mail ou senha incorretos.")

else:
    # --- VERIFICAÇÃO DE TROCA DE SENHA OBRIGATÓRIA (Cibersegurança) ---
    if st.session_state.get('primeiro_acesso') == 1 and st.session_state.perfil != "Admin":
        st.header("🔒 Alteração de Senha Obrigatória")
        st.info(f"Olá {st.session_state.nome_usuario}, defina sua senha definitiva.")
        
        with st.form("form_nova_senha"):
            n_senha = st.text_input("Nova Senha", type="password")
            c_senha = st.text_input("Confirme a Senha", type="password")
            if st.form_submit_button("Atualizar Senha"):
                if n_senha == c_senha and len(n_senha) >= 6:
                    conn = conectar()
                    cursor = conn.cursor()
                    cursor.execute("UPDATE usuarios SET senha_hash = ?, primeiro_acesso = 0 WHERE email = ?", 
                                   (hash_senha(n_senha), st.session_state.email_usuario))
                    conn.commit()
                    conn.close()
                    st.session_state.primeiro_acesso = 0
                    st.success("Senha atualizada!")
                    st.rerun()
                else:
                    st.error("Senhas não coincidem ou são muito curtas.")
    
    else:
        # --- DASHBOARD PRINCIPAL ---
        st.sidebar.title(f"Perfil: {st.session_state.perfil}")
        aba = st.sidebar.radio("Navegação", ["Início", "Ordens de Serviço", "Estoque", "Administração"])

        if aba == "Início":
            st.header(f"Bem-vindo ao OficinaPro, {st.session_state.get('nome_usuario', 'Admin')}")
            st.write("Utilize o menu lateral para gerir a oficina.")

        elif aba == "Ordens de Serviço":
            nome_responsavel = st.session_state.get('nome_usuario', 'Admin')
            st.subheader(f"Área Técnica - Responsável: {nome_responsavel}")
            # (Aqui mantém o código de OS que já temos)
            with st.expander("➕ Nova OS"):
                with st.form("nova_os"):
                    mod = st.text_input("Modelo"); pla = st.text_input("Placa")
                    if st.form_submit_button("Registrar"): st.success("Registrado!")

        elif aba == "Estoque":
            st.header("📦 Estoque e Inteligência de Preços")
            # (Aqui mantém o código de Estoque que já temos)
            st.subheader("➕ Cadastro de Itens")
            with st.form("form_est"):
                p = st.text_input("Peça"); q = st.number_input("Qtd", min_value=0)
                if st.form_submit_button("Salvar"): st.success("Salvo!")

        elif aba == "Administração":
            if st.session_state.perfil == "Admin":
                st.header("⚙️ Painel de Gestão Master")
                t_cad, t_reset, t_backup = st.tabs(["👥 Colaboradores", "🔑 Resetar Senhas", "💾 Backup e Segurança"])
                
                with t_cad:
                    st.subheader("Registar Novo Mecânico/Gerente")
                    with st.form("cad_novo"):
                        nome = st.text_input("Nome Completo")
                        email = st.text_input("E-mail de Login")
                        cargo = st.selectbox("Cargo", ["Mecanico", "Gerente"])
                        if st.form_submit_button("Finalizar Cadastro"):
                            conn = conectar(); cursor = conn.cursor()
                            try:
                                senha_i = hash_senha("123456") # Senha padrão
                                cursor.execute("INSERT INTO usuarios (nome, email, cargo, nivel_acesso, senha_hash) VALUES (?,?,?,?,?)",
                                               (nome, email, cargo, cargo, senha_i))
                                conn.commit(); st.success("Cadastrado com sucesso! Senha padrão: 123456")
                            except: st.error("E-mail já existe no sistema.")
                            finally: conn.close()

                with t_reset:
                    st.subheader("🛠️ Recuperação de Acesso")
                    st.write("Redefina a senha de um colaborador para '123456'.")
                    conn = conectar()
                    usuarios_df = pd.read_sql_query("SELECT id, nome, email FROM usuarios", conn)
                    conn.close()
                    
                    if not usuarios_df.empty:
                        selecionado = st.selectbox("Selecione o Colaborador", usuarios_df['email'])
                        if st.button("Resetar Senha para Padrão"):
                            conn = conectar(); cursor = conn.cursor()
                            nova_h = hash_senha("123456")
                            cursor.execute("UPDATE usuarios SET senha_hash = ?, primeiro_acesso = 1 WHERE email = ?", (nova_h, selecionado))
                            conn.commit(); conn.close()
                            st.warning(f"A senha de {selecionado} foi resetada. No próximo login, ele deverá mudar a senha.")
                    else:
                        st.info("Nenhum colaborador cadastrado.")

                with t_backup:
                    st.subheader("📥 Cópia de Segurança")
                    st.info("Clique no botão abaixo para descarregar a base de dados completa.")
                    if os.path.exists('oficina_mecanica.db'):
                        with open('oficina_mecanica.db', 'rb') as f:
                            st.download_button(
                                label="📥 Baixar Backup (.db)",
                                data=f,
                                file_name="backup_oficina_pro.db",
                                mime="application/octet-stream"
                            )
                    else:
                        st.error("Banco de dados não encontrado.")

            else:
                st.error("Acesso restrito.")

        if st.sidebar.button("Sair"):
            st.session_state.logado = False
            st.rerun()
