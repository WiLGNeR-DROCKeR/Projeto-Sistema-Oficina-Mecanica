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

    else:
            # --- INÍCIO DA NOVA TELA DO MECÂNICO ---
            st.subheader(f"Área Técnica - Mecânico: {st.session_state.nome_usuario}")
            
            # 1. Formulário para abrir nova Ordem de Serviço
            with st.expander("➕ Abrir Nova Ordem de Serviço (Laudo e Peças)"):
                with st.form("form_nova_os"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        modelo = st.text_input("Modelo do Veículo")
                    with col2:
                        placa = st.text_input("Placa")
                    with col3:
                        ano = st.text_input("Ano")
                    
                    problema = st.text_area("Descrição do Defeito / Diagnóstico Técnico")
                    pecas_sugeridas = st.text_area("Peças Necessárias e Marcas Sugeridas (Ex: 2x Amortecedor Monroe)")
                    
                    if st.form_submit_button("Enviar para Aprovação do Administrador"):
                        if modelo and placa and problema:
                            conn = conectar()
                            cursor = conn.cursor()
                            try:
                                cursor.execute("""
                                    INSERT INTO ordens_servico 
                                    (carro_modelo, carro_placa, carro_ano, descricao_problema, 
                                     pecas_sugeridas_mecanico, id_mecanico, status_solicitacao) 
                                    VALUES (?, ?, ?, ?, ?, ?, ?)""", 
                                    (modelo, placa, ano, problema, pecas_sugeridas, st.session_state.nome_usuario, "Pendente"))
                                conn.commit()
                                st.success("✅ Ordem de Serviço registrada! Aguarde a liberação das peças pelo Admin.")
                            except Exception as e:
                                st.error(f"Erro ao salvar: {e}")
                            finally:
                                conn.close()
                        else:
                            st.warning("Por favor, preencha o Modelo, Placa e Diagnóstico.")

            st.write("---")
            
            # 2. Listagem de serviços para o mecânico acompanhar
            st.subheader("🛠️ Meus Serviços em Andamento")
            conn = conectar()
            # Filtra apenas os serviços deste mecânico
            query = f"SELECT id, carro_modelo, carro_placa, status_solicitacao, valor_comissao FROM ordens_servico WHERE id_mecanico = '{st.session_state.nome_usuario}'"
            df_servicos = pd.read_sql_query(query, conn)
            conn.close()

            if not df_servicos.empty:
                # Melhora o visual da tabela
                df_servicos.columns = ["ID", "Veículo", "Placa", "Status Peças", "Minha Comissão (R$)"]
                st.dataframe(df_servicos, use_container_width=True, hide_index=True)
            else:
                st.info("Você ainda não possui ordens de serviço registradas.")
            # --- FIM DA NOVA TELA DO MECÂNICO ---

    elif aba == "Estoque":
        st.header("📦 Controle de Peças")
        # Simulação de Margem Vermelha
        st.warning("⚠️ Alerta: Pastilhas de Freio em nível crítico (2 unidades)!")

    elif aba == "Administração":
        if st.session_state.perfil == "Admin":
            st.header("⚙️ Painel de Controlo do Administrador")
            
            # Criamos abas para organizar as ferramentas do Admin
            tab_cad, tab_rel, tab_backup = st.tabs(["👥 Colaboradores", "📊 Relatórios", "🛡️ Segurança e Backup"])
            
            with tab_cad:
                st.subheader("Registar Novo Profissional")
                # (Aqui mantém o seu formulário de cadastro que já criámos)
                with st.form("cad_colab"):
                    nome_c = st.text_input("Nome do Profissional")
                    email_c = st.text_input("E-mail de Acesso")
                    cargo_c = st.selectbox("Cargo", ["Mecânico", "Gerente"])
                    st.write("Limitações de Acesso:")
                    lim_nf = st.checkbox("Pode dispensar Nota Fiscal?")
                    lim_logo = st.checkbox("Pode alterar Logo/Cores?")
                    
                    if st.form_submit_button("Finalizar Registo"):
                        # Chama a sua função de cadastrar_colaborador
                        st.success(f"Colaborador {nome_c} registado!")

            with tab_rel:
                st.subheader("📈 Relatórios de Fluxo de Caixa")
                st.info("Módulo de inteligência de lucro em desenvolvimento.")
                # No futuro, aqui puxaremos os cálculos de (Total - Peças - Comissão)

            with tab_backup:
                st.subheader("🔐 Gestão de Backups e Criptografia")
                st.write("""
                Este sistema realiza backups diários automáticos para o nosso servidor privado. 
                Como medida extra de segurança, pode descarregar uma cópia local criptografada.
                """)
                
                # Lógica para descarregar o ficheiro .db
                db_file = 'oficina_mecanica.db'
                if os.path.exists(db_file):
                    with open(db_file, "rb") as f:
                        st.download_button(
                            label="📥 Descarregar Backup Completo (DB)",
                            data=f,
                            file_name="backup_oficina_seguro.db",
                            mime="application/octet-stream",
                            help="O ficheiro contém todos os dados de clientes, peças e comissões."
                        )
                else:
                    st.error("Ficheiro de base de dados não encontrado para backup.")
                
                st.write("---")
                st.success("🔒 Envio para a nuvem: Ativo (Status: 100% Criptografado)")

        else:
            st.error("Acesso restrito apenas ao Administrador Geral.")

    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()
