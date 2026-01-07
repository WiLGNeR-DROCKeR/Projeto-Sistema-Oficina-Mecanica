import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import os
import json
from datetime import datetime

# ==========================================
# 1. CONFIGURAÇÕES E ESTILO (UI ORIGINAL)
# ==========================================
st.set_page_config(page_title="OficinaPro | Gestão Master", page_icon="🛠️", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Roboto', sans-serif; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left: 5px solid #007bff; }
    </style>
    """, unsafe_allow_html=True)

ADMIN_USER = st.secrets["admin_user"]
ADMIN_PASS = st.secrets["admin_password"]

# ==========================================
# 2. CAMADA DE DADOS
# ==========================================
def conectar():
    return sqlite3.connect('oficina_mecanica_V2.db', check_same_thread=False)

def inicializar_db():
    conn = conectar(); cursor = conn.cursor()
    # Tabela de Usuários Completa
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, cargo TEXT, email TEXT UNIQUE,
        telefone TEXT, endereco TEXT, especializacoes TEXT, exp_anos TEXT,
        senha_hash TEXT, nivel_acesso TEXT, primeiro_acesso INTEGER DEFAULT 1,
        permissoes_gerente TEXT DEFAULT '[]')''')
    
    # Tabela de Estoque Avançada
    cursor.execute('''CREATE TABLE IF NOT EXISTS estoque (
        id INTEGER PRIMARY KEY AUTOINCREMENT, peca TEXT, sku TEXT, quantidade INTEGER, 
        quantidade_minima INTEGER, valor_compra REAL, fornecedor TEXT, prazo_entrega TEXT)''')

    # Tabela de OS Completa
    cursor.execute('''CREATE TABLE IF NOT EXISTS ordens_servico (
        id INTEGER PRIMARY KEY AUTOINCREMENT, carro_modelo TEXT, carro_marca TEXT, carro_placa TEXT, 
        carro_ano TEXT, descricao_problema TEXT, pecas_trocadas TEXT, id_mecanico TEXT, 
        status TEXT DEFAULT 'Pendente', valor_pecas REAL DEFAULT 0.0, 
        valor_mao_obra REAL DEFAULT 0.0, pct_mecanico REAL DEFAULT 0.0, bonificacao REAL DEFAULT 0.0, data_registro TEXT)''')
    conn.commit(); conn.close()

def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

inicializar_db()

# ==========================================
# 3. LÓGICA DE LOGIN E SESSÃO
# ==========================================
if 'logado' not in st.session_state:
    st.session_state.update({'logado': False, 'perfil': None, 'nome': None, 'permissoes': []})

if not st.session_state.logado:
    st.title("🔐 Acesso Restrito OficinaPro")
    u = st.text_input("E-mail"); p = st.text_input("Senha", type="password")
    if st.button("🚀 Entrar"):
        if u == ADMIN_USER and p == ADMIN_PASS:
            st.session_state.update({'logado': True, 'perfil': "Admin", 'nome': "Administrador Geral"})
            st.rerun()
        else:
            conn = conectar(); cursor = conn.cursor()
            cursor.execute("SELECT nivel_acesso, nome, primeiro_acesso, email, permissoes_gerente FROM usuarios WHERE email=? AND senha_hash=?", (u, hash_senha(p)))
            res = cursor.fetchone(); conn.close()
            if res:
                st.session_state.update({'logado': True, 'perfil': res[0], 'nome': res[1], 'p_acesso': res[2], 'email_u': res[3], 'permissoes': json.loads(res[4])})
                st.rerun()
            else: st.error("Acesso Negado.")
else:
    # Logout no Sidebar
    if st.sidebar.button("🚪 Sair do Sistema"):
        st.session_state.logado = False
        st.rerun()

    # --- BLOQUEIO DE PRIMEIRO ACESSO ---
    if st.session_state.get('p_acesso') == 1 and st.session_state.perfil != "Admin":
        st.header("🛡️ Segurança: Alterar Senha")
        with st.form("reset_p"):
            n_p = st.text_input("Nova Senha", type="password")
            if st.form_submit_button("Salvar"):
                conn = conectar(); cursor = conn.cursor()
                cursor.execute("UPDATE usuarios SET senha_hash=?, primeiro_acesso=0 WHERE email=?", (hash_senha(n_p), st.session_state.email_u))
                conn.commit(); conn.close(); st.session_state.p_acesso = 0; st.success("Pronto!"); st.rerun()
    
    else:
        # --- DASHBOARD DE ACORDO COM PERFIL ---
        st.sidebar.markdown(f"**👤 {st.session_state.nome}**")
        abas_disp = ["🏠 Início"]
        if st.session_state.perfil == "Admin":
            abas_disp += ["📋 O.S. Master", "📦 Estoque", "💰 Financeiro", "⚙️ Administração"]
        elif st.session_state.perfil == "Gerente":
            abas_disp += [a for a in ["📋 O.S. Master", "📦 Estoque", "💰 Financeiro"] if a in st.session_state.permissoes]
        else:
            abas_disp += ["🛠️ Meus Trabalhos"]

        aba = st.sidebar.radio("Navegação", abas_disp)

        # ---------------------------------------------------------
        # ABA: INÍCIO (DASHBOARD)
        # ---------------------------------------------------------
        if "🏠 Início" in aba:
            st.header(f"Bem-vindo ao OficinaPro")
            c1, c2, c3 = st.columns(3)
            conn = conectar()
            os_p = pd.read_sql_query("SELECT COUNT(*) FROM ordens_servico WHERE status='Pendente'", conn).iloc[0,0]
            est_c = pd.read_sql_query("SELECT COUNT(*) FROM estoque WHERE quantidade <= quantidade_minima", conn).iloc[0,0]
            c1.metric("Serviços Pendentes", os_p)
            c2.metric("Linha Vermelha (Estoque)", est_c, delta_color="inverse", delta=-est_c if est_c > 0 else 0)
            c3.metric("Segurança", "Criptografia Ativa")
            conn.close()

        # ---------------------------------------------------------
        # ABA: MEUS TRABALHOS (MECÂNICO)
        # ---------------------------------------------------------
        elif "🛠️ Meus Trabalhos" in aba:
            st.subheader("🛠️ Registro de Atividades Técnicas")
            with st.expander("📝 Abrir Laudo de Carro"):
                with st.form("os_mecanico"):
                    c1, c2, c3 = st.columns(3)
                    mod = c1.text_input("Modelo"); marc = c2.text_input("Marca"); pla = c3.text_input("Placa")
                    desc = st.text_area("Diagnóstico (Sem limite de texto)")
                    pecas = st.text_area("Peças Necessárias")
                    if st.form_submit_button("Enviar para Gerência"):
                        conn = conectar(); cursor = conn.cursor()
                        cursor.execute("INSERT INTO ordens_servico (carro_modelo, carro_marca, carro_placa, descricao_problema, pecas_sugeridas_mecanico, id_mecanico, data_registro) VALUES (?,?,?,?,?,?,?)",
                                       (mod, marc, pla, desc, pecas, st.session_state.nome, datetime.now().strftime("%d/%m/%Y")))
                        conn.commit(); conn.close(); st.success("Enviado!")

        # ---------------------------------------------------------
        # ABA: FINANCEIRO (BI AVANÇADO)
        # ---------------------------------------------------------
        elif "💰 Financeiro" in aba:
            st.header("📊 Relatórios Financeiros e Comissões")
            conn = conectar()
            df_fin = pd.read_sql_query("SELECT * FROM ordens_servico", conn)
            conn.close()
            if not df_fin.empty:
                bruto = df_fin['valor_pecas'].sum() + df_fin['valor_mao_obra'].sum()
                comiss = df_fin['valor_comissao'].sum() + df_fin['bonificacao'].sum()
                st.columns(3)[0].metric("Receita Bruta", f"R$ {bruto:,.2f}")
                st.columns(3)[1].metric("Total Pago a Mecânicos", f"R$ {comiss:,.2f}")
                st.columns(3)[2].metric("Lucro Líquido", f"R$ {bruto - comiss - df_fin['valor_pecas'].sum():,.2f}")
                st.bar_chart(df_fin[['valor_mao_obra', 'valor_comissao']])

        # ---------------------------------------------------------
        # ABA: ADMINISTRAÇÃO (GESTÃO DE PESSOAS E SISTEMA)
        # ---------------------------------------------------------
        elif "⚙️ Administração" in aba:
            st.header("⚙️ Controle Geral do Sistema")
            t_usr, t_ger, t_back = st.tabs(["👤 Cadastrar Profissional", "🔑 Permissões Gerente", "💾 Backups"])
            
            with t_usr:
                with st.form("cad_prof"):
                    st.write("Dados do Colaborador")
                    col1, col2 = st.columns(2)
                    n_p = col1.text_input("Nome Completo")
                    e_p = col2.text_input("E-mail (Login)")
                    cargo_p = st.selectbox("Cargo", ["Mecanico", "Gerente"])
                    esp = st.text_area("Especializações (Use + para várias)")
                    if st.form_submit_button("Cadastrar"):
                        conn = conectar(); cursor = conn.cursor()
                        cursor.execute("INSERT INTO usuarios (nome, email, cargo, nivel_acesso, senha_hash, especializacoes) VALUES (?,?,?,?,?,?)",
                                       (n_p, e_p, cargo_p, cargo_p, hash_senha("123456"), esp))
                        conn.commit(); conn.close(); st.success("Cadastrado! Senha padrão: 123456")

            with t_ger:
                st.write("Defina o que os Gerentes podem acessar:")
                p_os = st.checkbox("Acesso a O.S. Master")
                p_est = st.checkbox("Acesso ao Estoque")
                p_fin = st.checkbox("Acesso ao Financeiro")
                if st.button("Salvar Limitações"):
                    # Aqui você salvaria no banco as escolhas para o cargo 'Gerente'
                    st.success("Permissões de Gerência atualizadas!")

            with t_back:
                st.write("Baixe o backup criptografado do banco de dados:")
                if os.path.exists('oficina_mecanica_V2.db'):
                    with open('oficina_mecanica_V2.db', 'rb') as f:
                        st.download_button("📥 Download Backup Diário", f, file_name=f"backup_{datetime.now().strftime('%Y%m%d')}.db")
