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
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT, cargo TEXT, email TEXT UNIQUE,
        senha_hash TEXT, nivel_acesso TEXT,
        primeiro_acesso INTEGER DEFAULT 1)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS estoque (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        peca TEXT, quantidade INTEGER, quantidade_minima INTEGER,
        valor_compra REAL, fornecedor TEXT, prazo_entrega_medio TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS ordens_servico (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        carro_modelo TEXT, carro_placa TEXT, carro_ano TEXT, 
        descricao_problema TEXT, pecas_sugeridas_mecanico TEXT, 
        id_mecanico TEXT, status_solicitacao TEXT DEFAULT 'Pendente',
        valor_comissao REAL DEFAULT 0.0)''')
    conn.commit()
    conn.close()

inicializar_db()

def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

# ==========================================
# 3. CONTROLE DE ACESSO
# ==========================================
if 'logado' not in st.session_state:
    st.session_state.logado = False
    st.session_state.perfil = None

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
    # --- INTERCEPTOR DE TROCA DE SENHA ---
    if st.session_state.get('primeiro_acesso') == 1 and st.session_state.perfil != "Admin":
        st.header("🔒 Alteração de Senha Obrigatória")
        with st.form("form_nova_senha"):
            n_senha = st.text_input("Nova Senha", type="password")
            c_senha = st.text_input("Confirme a Senha", type="password")
            if st.form_submit_button("Atualizar Senha"):
                if n_senha == c_senha and len(n_senha) >= 6:
                    conn = conectar(); cursor = conn.cursor()
                    cursor.execute("UPDATE usuarios SET senha_hash = ?, primeiro_acesso = 0 WHERE email = ?", 
                                   (hash_senha(n_senha), st.session_state.email_usuario))
                    conn.commit(); conn.close()
                    st.session_state.primeiro_acesso = 0
                    st.success("Senha atualizada!")
                    st.rerun()
                else: st.error("Senhas inválidas ou curtas.")
    
    else:
        # --- DASHBOARD PRINCIPAL ---
        st.sidebar.title(f"Perfil: {st.session_state.perfil}")
        aba = st.sidebar.radio("Navegação", ["Início", "Ordens de Serviço", "Estoque", "Administração"])

        # ---------------------------------------------------------
        # ABA: INÍCIO
        # ---------------------------------------------------------
        if aba == "Início":
            st.header(f"Bem-vindo, {st.session_state.get('nome_usuario', 'Admin')}")
            st.write("Sistema de gestão integrado OficinaPro.")

        # ---------------------------------------------------------
        # ABA: ORDENS DE SERVIÇO (VOLTANDO AO MODELO PADRÃO)
        # ---------------------------------------------------------
        elif aba == "Ordens de Serviço":
            nome_responsavel = st.session_state.get('nome_usuario', 'Admin')
            st.subheader(f"Área Técnica - Responsável: {nome_responsavel}")
            
            with st.expander("➕ Abrir Nova Ordem de Serviço (Laudo e Peças)"):
                with st.form("form_nova_os"):
                    col1, col2, col3 = st.columns(3)
                    with col1: modelo = st.text_input("Modelo do Veículo")
                    with col2: placa = st.text_input("Placa")
                    with col3: ano = st.text_input("Ano")
                    
                    problema = st.text_area("Descrição do Defeito / Diagnóstico Técnico")
                    pecas_sugeridas = st.text_area("Peças Necessárias e Marcas Sugeridas")
                    
                    if st.form_submit_button("Enviar para Aprovação do Administrador"):
                        if modelo and placa and problema:
                            conn = conectar(); cursor = conn.cursor()
                            cursor.execute("""INSERT INTO ordens_servico 
                                (carro_modelo, carro_placa, carro_ano, descricao_problema, pecas_sugeridas_mecanico, id_mecanico) 
                                VALUES (?, ?, ?, ?, ?, ?)""", (modelo, placa, ano, problema, pecas_sugeridas, nome_responsavel))
                            conn.commit(); conn.close()
                            st.success("✅ OS registrada com sucesso!")
                        else: st.warning("Preencha os campos obrigatórios.")

            st.write("---")
            st.subheader("🛠️ Serviços em Andamento")
            conn = conectar()
            df_os = pd.read_sql_query(f"SELECT id, carro_modelo, carro_placa, status_solicitacao FROM ordens_servico WHERE id_mecanico = '{nome_responsavel}'", conn)
            conn.close()
            st.dataframe(df_os, use_container_width=True, hide_index=True)

        # ---------------------------------------------------------
        # ABA: ESTOQUE (VOLTANDO AO MODELO PADRÃO)
        # ---------------------------------------------------------
        elif aba == "Estoque":
            st.header("📦 Gestão de Estoque")
            
            with st.expander("➕ Adicionar/Atualizar Peça no Estoque"):
                with st.form("form_estoque"):
                    col1, col2 = st.columns(2)
                    with col1:
                        nome_peca = st.text_input("Nome da Peça")
                        qtd_atual = st.number_input("Quantidade em Estoque", min_value=0, step=1)
                        qtd_min = st.number_input("Quantidade Mínima (Alerta)", min_value=1, step=1)
                    with col2:
                        preco_compra = st.number_input("Preço de Compra (R$)", min_value=0.0)
                        fornecedor = st.text_input("Fornecedor / Loja")
                        prazo = st.text_input("Prazo de Entrega Médio")
                    
                    if st.form_submit_button("Registrar no Sistema"):
                        conn = conectar(); cursor = conn.cursor()
                        cursor.execute("""INSERT INTO estoque (peca, quantidade, quantidade_minima, valor_compra, fornecedor, prazo_entrega_medio)
                            VALUES (?, ?, ?, ?, ?, ?)""", (nome_peca, qtd_atual, qtd_min, preco_compra, fornecedor, prazo))
                        conn.commit(); conn.close()
                        st.success("Peça adicionada!")
                        st.rerun()

            st.write("---")
            st.subheader("🚨 Alertas de Margem Vermelha")
            conn = conectar()
            df_critico = pd.read_sql_query("SELECT peca, quantidade, quantidade_minima FROM estoque WHERE quantidade <= quantidade_minima", conn)
            if not df_critico.empty:
                st.warning("Itens abaixo do estoque mínimo!")
                st.dataframe(df_critico, use_container_width=True)
            else: st.success("Estoque saudável.")
            conn.close()

        # ---------------------------------------------------------
        # ABA: ADMINISTRAÇÃO (MANTENDO AS NOVAS FUNÇÕES)
        # ---------------------------------------------------------
        elif aba == "Administração":
            if st.session_state.perfil == "Admin":
                st.header("⚙️ Painel Master")
                t_cad, t_reset, t_backup = st.tabs(["👥 Colaboradores", "🔑 Resetar Senhas", "💾 Backup"])
                
                with t_cad:
                    with st.form("cad"):
                        n = st.text_input("Nome"); e = st.text_input("E-mail")
                        c = st.selectbox("Cargo", ["Mecanico", "Gerente"])
                        if st.form_submit_button("Registar"):
                            conn = conectar(); cursor = conn.cursor()
                            try:
                                cursor.execute("INSERT INTO usuarios (nome, email, cargo, nivel_acesso, senha_hash) VALUES (?,?,?,?,?)",
                                               (n, e, c, c, hash_senha("123456")))
                                conn.commit(); st.success("Registo concluído! Senha: 123456")
                            except: st.error("E-mail já existe.")
                            finally: conn.close()

                with t_reset:
                    conn = conectar()
                    usrs = pd.read_sql_query("SELECT email FROM usuarios", conn)
                    conn.close()
                    sel = st.selectbox("Selecionar E-mail", usrs['email'])
                    if st.button("Resetar para 123456"):
                        conn = conectar(); cursor = conn.cursor()
                        cursor.execute("UPDATE usuarios SET senha_hash = ?, primeiro_acesso = 1 WHERE email = ?", (hash_senha("123456"), sel))
                        conn.commit(); conn.close()
                        st.warning(f"Senha de {sel} resetada.")

                with t_backup:
                    if os.path.exists('oficina_mecanica.db'):
                        with open('oficina_mecanica.db', 'rb') as f:
                            st.download_button("📥 Baixar Backup DB", f, file_name="backup.db")
            else: st.error("Acesso restrito.")

        if st.sidebar.button("Sair"):
            st.session_state.logado = False
            st.rerun()
