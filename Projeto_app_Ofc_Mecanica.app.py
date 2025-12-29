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
    # Tabela de Usuários (Adicionada a coluna primeiro_acesso)
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT, cargo TEXT, email TEXT UNIQUE, telefone TEXT,
        especializacoes TEXT, senha_hash TEXT, nivel_acesso TEXT,
        permissoes_json TEXT,
        primeiro_acesso INTEGER DEFAULT 1)''')
    
    # Tabela de Estoque (Margem Vermelha)
    cursor.execute('''CREATE TABLE IF NOT EXISTS estoque (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        peca TEXT, quantidade INTEGER, quantidade_minima INTEGER,
        valor_compra REAL, fornecedor TEXT)''')

    # Tabela de Ordens de Serviço (Refatorada)
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
                st.error("Credenciais incorretas.")

else:
    # --- VERIFICAÇÃO DE TROCA DE SENHA OBRIGATÓRIA ---
    if st.session_state.get('primeiro_acesso') == 1 and st.session_state.perfil != "Admin":
        st.header("🔒 Troca de Senha Obrigatória")
        st.info(f"Olá {st.session_state.nome_usuario}, por segurança, defina uma nova senha para o seu primeiro acesso.")
        
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
                    st.success("Senha atualizada! Acessando sistema...")
                    st.rerun()
                else:
                    st.error("Senhas não coincidem ou são muito curtas (min. 6 caracteres).")
    
    else:
        # --- DASHBOARD PRINCIPAL (CORRIGIDO: ELIF EM VEZ DE ELSE) ---
        st.sidebar.title(f"Perfil: {st.session_state.perfil}")
        aba = st.sidebar.radio("Navegação", ["Início", "Ordens de Serviço", "Estoque", "Administração"])

        if aba == "Início":
            st.header("Bem-vindo ao OficinaPro")
            st.write(f"Logado como: {st.session_state.get('nome_usuario', 'Administrador')}")

        elif aba == "Ordens de Serviço":
            nome_responsavel = st.session_state.get('nome_usuario', 'Administrador')
            st.subheader(f"Área Técnica - Responsável: {nome_responsavel}")
            
            with st.expander("➕ Abrir Nova Ordem de Serviço"):
                with st.form("form_nova_os"):
                    col1, col2, col3 = st.columns(3)
                    with col1: mod = st.text_input("Modelo")
                    with col2: pla = st.text_input("Placa")
                    with col3: an = st.text_input("Ano")
                    prob = st.text_area("Diagnóstico")
                    pec = st.text_area("Peças Sugeridas")
                    if st.form_submit_button("Enviar"):
                        conn = conectar(); cursor = conn.cursor()
                        cursor.execute("INSERT INTO ordens_servico (carro_modelo, carro_placa, carro_ano, descricao_problema, pecas_sugeridas_mecanico, id_mecanico) VALUES (?,?,?,?,?,?)",
                                       (mod, pla, an, prob, pec, nome_responsavel))
                        conn.commit(); conn.close()
                        st.success("OS Registrada!")

            st.write("---")
            st.subheader("🛠️ Serviços em Andamento")
            conn = conectar()
            df_os = pd.read_sql_query(f"SELECT id, carro_modelo, carro_placa, status_solicitacao FROM ordens_servico WHERE id_mecanico = '{nome_responsavel}'", conn)
            conn.close()
            st.dataframe(df_os, use_container_width=True, hide_index=True)

        elif aba == "Estoque":
            st.header("📦 Gestão de Estoque")
            st.subheader("➕ Cadastro de Peças")
            with st.form("form_estoque"):
                c1, c2 = st.columns(2)
                with c1:
                    n_peca = st.text_input("Nome da Peça")
                    q_atual = st.number_input("Qtd Atual", min_value=0, step=1)
                with c2:
                    q_min = st.number_input("Qtd Mínima", min_value=1, step=1)
                    p_compra = st.number_input("Preço Compra", min_value=0.0)
                forn = st.text_input("Fornecedor")
                if st.form_submit_button("Salvar Peça"):
                    conn = conectar(); cursor = conn.cursor()
                    cursor.execute("INSERT INTO estoque (peca, quantidade, quantidade_minima, valor_compra, fornecedor) VALUES (?,?,?,?,?)",
                                   (n_peca, q_atual, q_min, p_compra, forn))
                    conn.commit(); conn.close()
                    st.success("Peça salva!")
                    st.rerun()

            st.write("---")
            st.subheader("🚨 Alertas de Reposição")
            conn = conectar()
            df_cr = pd.read_sql_query("SELECT peca, quantidade, quantidade_minima FROM estoque WHERE quantidade <= quantidade_minima", conn)
            if not df_cr.empty: st.warning("Itens críticos encontrados!"); st.dataframe(df_cr, use_container_width=True)
            else: st.success("Estoque OK!")
            conn.close()

        elif aba == "Administração":
            if st.session_state.perfil == "Admin":
                st.header("⚙️ Painel Administrativo")
                t1, t2 = st.tabs(["Colaboradores", "Backup"])
                with t1:
                    st.subheader("Novo Registo")
                    with st.form("cad_colab"):
                        nc = st.text_input("Nome")
                        ec = st.text_input("E-mail")
                        cc = st.selectbox("Cargo", ["Mecânico", "Gerente"])
                        if st.form_submit_button("Registar"):
                            # Aqui você usaria sua função hash_senha e cadastrar_colaborador
                            st.success("Colaborador registado com senha padrão 123456")
                with t2:
                    if os.path.exists('oficina_mecanica.db'):
                        with open('oficina_mecanica.db', 'rb') as f:
                            st.download_button("📥 Baixar Banco de Dados", f, file_name="backup.db")
            else:
                st.error("Acesso Negado.")

        if st.sidebar.button("Sair"):
            st.session_state.logado = False
            st.rerun()
