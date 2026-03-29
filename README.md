# 🛠️ Sistema de Gestão para Oficinas Mecânicas (OficinaPro)

Este projeto consiste num ecossistema completo para gestão de oficinas, focado em automação, segurança de dados e transparência financeira entre administradores e colaboradores. Desenvolvido como parte do meu percurso académico em Análise e Desenvolvimento de Sistemas (ADS).

## 🚀 Funcionalidades Principais

### 🔐 Segurança e Níveis de Acesso (RBAC)
O sistema utiliza **Controlo de Acesso Baseado em Funções**, permitindo que o Administrador configure permissões específicas através de uma interface visual:
* **Administrador:** Acesso total, gestão de colaboradores, relatórios financeiros de lucro líquido e configuração de identidade visual.
* **Gerente:** Acesso configurável pelo administrador (pode ou não ver financeiros/estoque).
* **Mecânico:** Interface focada na execução, onde visualiza ordens de serviço e o valor da sua própria comissão, sem acesso ao lucro total da empresa.

### 📦 Gestão Inteligente de Estoque
* **Margem Vermelha:** Alertas automáticos quando uma peça atinge o stock mínimo.
* **Histórico de Compras:** Inteligência de mercado que mostra onde as peças foram compradas pelo melhor preço e o prazo médio de entrega.

### 💰 Financeiro e Comissões
* **Cálculo Automatizado:** O sistema calcula a comissão do mecânico com base na percentagem definida pelo administrador.
* **Módulo Fiscal:** Opção de emissão de NF-e/NFS-e com controlo administrativo para dispensar a obrigatoriedade em casos específicos.

### 🛡️ Proteção de Dados e Infraestrutura
* **Criptografia:** Senhas protegidas por Hashing (Bcrypt) e dados sensíveis criptografados em repouso.
* **Backups Diários:** Rotina de backup automatizada para servidores privados e nuvem, sem impacto na performance do utilizador.
* **Responsividade:** Desenvolvido para funcionar com 100% de qualidade em Smartphones, Tablets e Desktops.

## 🛠️ Tecnologias Utilizadas
* **Linguagem:** Python
* **Interface:** Streamlit (Web Responsiva)
* **Banco de Dados:** SQLite (Prototipagem) / PostgreSQL (Produção)
* **Segurança:** JSON Web Tokens (JWT) e Fernet Encryption
* **Cloud/Deploy:** Streamlit Cloud / GitHub

## 📈 Potencial de Mercado
Este software foi desenhado para ser escalável no modelo SaaS (Software as a Service). Segundo análises de mercado, sistemas similares para o nicho automotivo possuem alta retenção, com tickets médios variando entre R$ 150 a R$ 450 mensais por unidade de oficina.

## 👷 Como Executar o Projeto (Modo de Teste)
```bash
# Instalar dependências
pip install streamlit pandas

# Executar o sistema
streamlit run app.py

Desenvolvido por [Wilgner Sousa] Estudante de Análise e Desenvolvimento de Sistemas [Meu LinkedIn: https://www.linkedin.com/in/wilgner-sousa-566bb3354/]
