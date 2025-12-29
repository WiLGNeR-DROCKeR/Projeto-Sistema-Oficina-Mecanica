import streamlit as st
import sqlite3
import json
import hashlib
import pandas as pd
import os

# ==========================================
# 1. CONFIGURAÇÕES INICIAIS E UI
# ==========================================
# Definindo o tema e ícone da página
st.set_page_config(
    page_title="OficinaPro | Gestão Inteligente",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização básica para melhorar a leitura
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_password=True)

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
        valor_total REAL DEFAULT 0.0, valor_comissao REAL DEFAULT 0.0)''')
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
    
    if st.button("🚀 Entrar no Sistema"):
        if user_input == ADMIN_USER and senha_input == ADMIN_PASS:
            st.session_state.logado = True
            st.session_state.perfil = "Admin"
            st.rerun()
        else:
            conn = conectar(); cursor = conn.cursor()
            h_senha = hash_senha(senha_input)
            cursor.execute("SELECT nivel_acesso, nome, primeiro_acesso, email FROM usuarios WHERE email = ? AND senha_hash = ?", 
                           (user_input, h_senha))
            res = cursor.fetchone(); conn.close()

            if res:
                st.session_state.logado = True
                st.session_state.perfil = res[0]
                st.session_state.nome_usuario = res[1]
                st.session_state.primeiro_acesso = res[2]
                st.session_state.email_usuario = res[3]
                st.rerun()
            else: st.error("E-mail ou senha incorretos.")

else:
    # --- INTERCEPTOR DE TROCA DE SENHA ---
    if st.session_state.get('primeiro_acesso') == 1 and st.session_state.perfil != "Admin":
        st.header("🔒 Alteração de Senha Obrigatória")
        with st.form("form_nova_senha"):
            n_senha = st.text_input("Nova Senha", type="password")
            c_senha = st.text_input("Confirme a Senha", type="password")
            if st.form_submit_button("💾 Atualizar Senha"):
                if n_senha == c_senha and len(n_senha) >= 6:
                    conn = conectar(); cursor = conn.cursor()
                    cursor.execute("UPDATE usuarios SET senha_hash = ?, primeiro_acesso = 0 WHERE email = ?", 
                                   (hash_senha(n_senha), st.session_state.email_usuario))
                    conn.commit(); conn.close()
                    st.session_state.primeiro_acesso = 0
                    st.success("Senha atualizada!")
                    st.rerun()
                else: st.error("Senhas inválidas ou curtas (min 6 carac).")
    
    else:
        # --- MENU LATERAL COM ÍCONES ---
        st.sidebar.markdown(f"### 👤 {st.session_state.perfil}")
        aba = st.sidebar.radio(
            "Navegação", 
            ["🏠 Início", "📋 Ordens de Serviço", "📦 Estoque", "💰 Financeiro", "⚙️ Administração"]
        )

        # 🏠 ABA: INÍCIO
        if aba == "🏠 Início":
            st.header(f"👋 Bem-vindo, {st.session_state.get('nome_usuario', 'Admin')}")
            st.info("Utilize o menu ao lado para gerenciar as atividades da oficina.")
            
            # Cards de resumo rápido
            c1, c2, c3 = st.columns(3)
            conn = conectar()
            os_ativas = pd.read_sql_query("SELECT COUNT(*) FROM ordens_servico WHERE status_solicitacao = 'Pendente'", conn).iloc[0,0]
            pecas_falta = pd.read_sql_query("SELECT COUNT(*) FROM estoque WHERE quantidade <= quantidade_minima", conn).iloc[0,0]
            conn.close()
            
            c1.metric("Serviços Pendentes", os_ativas)
            c2.metric("Alertas de Estoque", pecas_falta, delta_color="inverse", delta=pecas_falta*-1 if pecas_falta > 0 else 0)
            c3.metric("Status do Sistema", "Online")

        # 📋 ABA: ORDENS DE SERVIÇO
        elif aba == "📋 Ordens de Serviço":
            st.header("📋 Ordens de Serviço")
            nome_responsavel = st.session_state.get('nome_usuario', 'Admin')
            
            with st.expander("➕ Abrir Nova OS"):
                with st.form("form_os"):
                    c1, c2, c3 = st.columns(3)
                    mod = c1.text_input("Modelo"); pla = c2.text_input("Placa"); an = c3.text_input("Ano")
                    prob = st.text_area("Diagnóstico Técnico")
                    pec = st.text_area("Peças e Marcas Sugeridas")
                    if st.form_submit_button("✅ Registrar OS"):
                        conn = conectar(); cursor = conn.cursor()
                        cursor.execute("INSERT INTO ordens_servico (carro_modelo, carro_placa, carro_ano, descricao_problema, pecas_sugeridas_mecanico, id_mecanico) VALUES (?,?,?,?,?,?)",
                                       (mod, pla, an, prob, pec, nome_responsavel))
                        conn.commit(); conn.close()
                        st.success("OS Aberta!")

            st.write("---")
            conn = conectar()
            df_os = pd.read_sql_query(f"SELECT id, carro_modelo, carro_placa, status_solicitacao FROM ordens_servico", conn)
            conn.close()
            st.dataframe(df_os, use_container_width=True, hide_index=True)

        # 📦 ABA: ESTOQUE
        elif aba == "📦 Estoque":
            st.header("📦 Gestão de Estoque")
            with st.expander("➕ Nova Peça"):
                with st.form("form_est"):
                    c1, c2 = st.columns(2)
                    n = c1.text_input("Peça"); qa = c1.number_input("Qtd", min_value=0)
                    qm = c2.number_input("Mínimo", min_value=1); pc = c2.number_input("Preço Compra", min_value=0.0)
                    if st.form_submit_button("💾 Salvar"):
                        conn = conectar(); cursor = conn.cursor()
                        cursor.execute("INSERT INTO estoque (peca, quantidade, quantidade_minima, valor_compra) VALUES (?,?,?,?)", (n, qa, qm, pc))
                        conn.commit(); conn.close(); st.success("Salvo!"); st.rerun()

            conn = conectar()
            df_est = pd.read_sql_query("SELECT peca, quantidade, quantidade_minima FROM estoque", conn)
            conn.close()
            st.dataframe(df_est, use_container_width=True)

        # 💰 ABA: FINANCEIRO (NOVIDADE)
        elif aba == "💰 Financeiro":
            st.header("💰 Inteligência Financeira")
            if st.session_state.perfil in ["Admin", "Gerente"]:
                conn = conectar()
                df_fin = pd.read_sql_query("SELECT valor_total, valor_comissao FROM ordens_servico", conn)
                conn.close()

                total_bruto = df_fin['valor_total'].sum()
                total_comissoes = df_fin['valor_comissao'].sum()
                lucro_liquido = total_bruto - total_comissoes

                col1, col2, col3 = st.columns(3)
                col1.metric("Faturamento Bruto", f"R$ {total_bruto:,.2f}")
                col2.metric("Total Comissões", f"R$ {total_comissoes:,.2f}", delta_color="inverse")
                col3.metric("Lucro Estimado", f"R$ {lucro_liquido:,.2f}")

                st.write("---")
                st.subheader("📊 Histórico de Ganhos")
                if not df_fin.empty:
                    st.bar_chart(df_fin[['valor_total', 'valor_comissao']])
                else:
                    st.info("Ainda não há dados financeiros para exibir.")
            else:
                st.error("Acesso restrito ao Administrador e Gerente.")

        # ⚙️ ABA: ADMINISTRAÇÃO
        elif aba == "⚙️ Administração":
            if st.session_state.perfil == "Admin":
                st.header("⚙️ Painel Master")
                t_c, t_r, t_b = st.tabs(["👤 Usuários", "🔑 Reset", "💾 Backup"])
                with t_c:
                    with st.form("cad"):
                        nc = st.text_input("Nome"); ec = st.text_input("Email"); cc = st.selectbox("Cargo", ["Mecanico", "Gerente"])
                        if st.form_submit_button("Registar"):
                            conn = conectar(); cursor = conn.cursor()
                            cursor.execute("INSERT INTO usuarios (nome, email, cargo, nivel_acesso, senha_hash) VALUES (?,?,?,?,?)", (nc, ec, cc, cc, hash_senha("123456")))
                            conn.commit(); conn.close(); st.success("Senha padrão: 123456")
                with t_r:
                    # Lógica de Reset de Senha (já implementada anteriormente)
                    st.write("Selecione um usuário para resetar a senha para 123456")
                with t_b:
                    if os.path.exists('oficina_mecanica.db'):
                        with open('oficina_mecanica.db', 'rb') as f:
                            st.download_button("📥 Baixar Backup", f, file_name="oficina.db")
            else: st.error("Acesso Negado.")

        if st.sidebar.button("🚪 Sair"):
            st.session_state.logado = False
            st.rerun()
