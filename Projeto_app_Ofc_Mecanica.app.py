import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import os
import json
from datetime import datetime

# ==========================================
# 1. CONFIGURAÇÕES E IDENTIDADE VISUAL (PROJETO_02)
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

try:
    ADMIN_USER = st.secrets["admin_user"]
    ADMIN_PASS = st.secrets["admin_password"]
except:
    st.error("Erro: Configure 'admin_user' e 'admin_password' nos Secrets do Streamlit.")
    st.stop()

# ==========================================
# 2. CAMADA DE DADOS E CORREÇÃO DE ERROS
# ==========================================
def conectar():
    return sqlite3.connect('oficina_mecanica_V2.db', check_same_thread=False)

def inicializar_db():
    conn = conectar(); cursor = conn.cursor()
    # Tabela de Usuários (Projeto_02)
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, cargo TEXT, email TEXT UNIQUE,
        telefone TEXT, endereco TEXT, especializacoes TEXT, exp_anos TEXT,
        senha_hash TEXT, nivel_acesso TEXT, primeiro_acesso INTEGER DEFAULT 1,
        permissoes_gerente TEXT DEFAULT '[]')''')
    
    # Tabela de Estoque (Projeto_02)
    cursor.execute('''CREATE TABLE IF NOT EXISTS estoque (
        id INTEGER PRIMARY KEY AUTOINCREMENT, peca TEXT, sku TEXT, quantidade INTEGER, 
        quantidade_minima INTEGER, valor_compra REAL, fornecedor TEXT, prazo_entrega TEXT)''')

    # Tabela de OS com Correção Automática de Colunas (Evita o DatabaseError)
    cursor.execute('''CREATE TABLE IF NOT EXISTS ordens_servico (
        id INTEGER PRIMARY KEY AUTOINCREMENT, carro_modelo TEXT, carro_marca TEXT, carro_placa TEXT, 
        carro_ano TEXT, descricao_problema TEXT, pecas_trocadas TEXT, id_mecanico TEXT, 
        status TEXT DEFAULT 'Pendente', valor_pecas REAL DEFAULT 0.0, 
        valor_mao_obra REAL DEFAULT 0.0, valor_comissao REAL DEFAULT 0.0, 
        bonificacao REAL DEFAULT 0.0, data_registro TEXT)''')
    
    # Verificação extra para garantir que colunas novas existam (Prevenção de erros futuros)
    colunas_novas = [('valor_pecas', 'REAL'), ('valor_mao_obra', 'REAL'), ('valor_comissao', 'REAL')]
    for col, tipo in colunas_novas:
        try:
            cursor.execute(f"ALTER TABLE ordens_servico ADD COLUMN {col} {tipo} DEFAULT 0.0")
        except: pass

    conn.commit(); conn.close()

def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

inicializar_db()

# ==========================================
# 3. CONTROLE DE ACESSO (PROJETO_02)
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
    # Sidebar (Projeto_02)
    st.sidebar.markdown(f"### ⚙️ {st.session_state.perfil}")
    st.sidebar.write(f"Usuário: {st.session_state.nome}")

    abas_disp = ["🏠 Início", "📋 Ordens de Serviço", "📦 Estoque", "💰 Financeiro", "⚙️ Administração"]
    # Filtro de permissões para Gerente/Mecânico
    if st.session_state.perfil == "Gerente":
        abas_disp = ["🏠 Início"] + [a for a in ["📋 Ordens de Serviço", "📦 Estoque", "💰 Financeiro"] if a in st.session_state.permissoes]
    elif st.session_state.perfil == "Mecanico":
        abas_disp = ["🏠 Início", "📋 Ordens de Serviço"]

    aba = st.sidebar.radio("Navegação", abas_disp)

    # 🏠 ABA: INÍCIO (HIBRIDIZAÇÃO PROJETO 01 + 02)
    if aba == "🏠 Início":
        st.header("🏠 Bem-vindo ao OficinaPro.")
        st.info(f"⚙️ {st.session_state.perfil} ⬅️ Utilize o menu lateral para gerir a oficina.")
        
        c1, c2, c3 = st.columns(3)
        conn = conectar()
        os_p = pd.read_sql_query("SELECT COUNT(*) FROM ordens_servico WHERE status='Pendente'", conn).iloc[0,0]
        est_c = pd.read_sql_query("SELECT COUNT(*) FROM estoque WHERE quantidade <= quantidade_minima", conn).iloc[0,0]
        conn.close()
        c1.metric("Serviços Pendentes", os_p)
        c2.metric("Estoque Crítico", est_c, delta="-Reposição", delta_color="inverse")
        c3.metric("Integridade do Sistema", "100%")

    # 📋 ABA: ORDENS DE SERVIÇO (PROJETO_02 + SELETOR DE PEÇAS)
    elif aba == "📋 Ordens de Serviço":
        st.header("📋 Gestão de Ordens Master")
        
        # Buscar peças para o seletor
        conn = conectar()
        pecas_disponiveis = pd.read_sql_query("SELECT peca FROM estoque", conn)['peca'].tolist()
        conn.close()

        with st.expander("➕ Lançar Serviço com Financeiro"):
            with st.form("os_fin"):
                col1, col2 = st.columns(2)
                v_mod = col1.text_input("Veículo"); v_pla = col2.text_input("Placa")
                v_p = col1.number_input("Valor Peças (R$)", min_value=0.0)
                v_m = col2.number_input("Valor Mão de Obra (R$)", min_value=0.0)
                
                # NOVO SELETOR DE PEÇAS
                pecas_sel = st.multiselect("Selecione as Peças Utilizadas", pecas_disponiveis)
                
                com = st.number_input("Comissão (R$)", min_value=0.0)
                
                if st.form_submit_button("Lançar"):
                    # Converte lista de peças em string para salvar no banco
                    str_pecas = ", ".join(pecas_sel)
                    conn = conectar(); cursor = conn.cursor()
                    cursor.execute("""INSERT INTO ordens_servico 
                        (carro_modelo, carro_placa, valor_pecas, valor_mao_obra, valor_comissao, id_mecanico, pecas_trocadas, data_registro) 
                        VALUES (?,?,?,?,?,?,?,?)""", (v_mod, v_pla, v_p, v_m, com, st.session_state.nome, str_pecas, datetime.now().strftime("%Y-%m-%d")))
                    conn.commit(); conn.close(); st.success("Serviço lançado!")

    # 📦 ABA: ESTOQUE (LAYOUT INTERNO PROJETO_01)
    elif aba == "📦 Estoque":
        st.header("📦 Estoque e Inteligência de Preços")
        st.subheader("➕ Cadastro de Itens")
        with st.form("form_est"):
            col1, col2 = st.columns(2)
            p = col1.text_input("Peça")
            q = col1.number_input("Quantidade Atual", min_value=0)
            qm = col2.number_input("Quantidade Mínima", min_value=1)
            vc = col2.number_input("Valor de Compra (R$)", min_value=0.0)
            if st.form_submit_button("Salvar Item"):
                conn = conectar(); cursor = conn.cursor()
                cursor.execute("INSERT INTO estoque (peca, quantidade, quantidade_minima, valor_compra) VALUES (?,?,?,?)", (p, q, qm, vc))
                conn.commit(); conn.close(); st.success("Peça salva com sucesso!")

    # 💰 ABA: FINANCEIRO (PROJETO_02)
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

    # ⚙️ ABA: ADMINISTRAÇÃO (LAYOUT PROJETO_01 + NOMES NOVOS)
    elif aba == "⚙️ Administração":
        if st.session_state.perfil == "Admin":
            st.header("⚙️ Painel de Gestão Master")
            t_cad, t_reset, t_backup = st.tabs(["👥 Usuários", "🔑 Resetar Senhas", "💾 Backup e Segurança"])
            
            with t_cad:
                st.subheader("Registar Novo Mecânico/Gerente")
                with st.form("cad_novo"):
                    nome = st.text_input("Nome Completo")
                    email = st.text_input("E-mail de Login")
                    cargo = st.selectbox("Cargo", ["Mecanico", "Gerente"])
                    if st.form_submit_button("Finalizar Cadastro"):
                        conn = conectar(); cursor = conn.cursor()
                        try:
                            senha_i = hash_senha("123456")
                            cursor.execute("INSERT INTO usuarios (nome, email, cargo, nivel_acesso, senha_hash) VALUES (?,?,?,?,?)",
                                           (nome, email, cargo, cargo, senha_i))
                            conn.commit(); st.success("Cadastrado com sucesso! Senha padrão: 123456")
                        except: st.error("E-mail já existe.")
                        finally: conn.close()

            with t_reset:
                st.subheader("🛠️ Recuperação de Acesso")
                conn = conectar()
                usrs = pd.read_sql_query("SELECT email FROM usuarios", conn)
                conn.close()
                sel = st.selectbox("Selecione o E-mail", usrs['email'])
                if st.button("Executar Reset de Senha"):
                    conn = conectar(); cursor = conn.cursor()
                    cursor.execute("UPDATE usuarios SET senha_hash = ?, primeiro_acesso = 1 WHERE email = ?", (hash_senha("123456"), sel))
                    conn.commit(); conn.close()
                    st.warning(f"A senha de {sel} foi resetada para 123456.")

            with t_backup:
                st.subheader("💾 Backup do Sistema")
                if os.path.exists('oficina_mecanica_V2.db'):
                    with open('oficina_mecanica_V2.db', 'rb') as f:
                        st.download_button("📥 Baixar Banco de Dados (.db)", f, file_name="oficina_backup_master.db")

    if st.sidebar.button("🚪 Sair"):
        st.session_state.logado = False
        st.rerun()
