import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- CONFIGURAÇÕES ---
NOME_ARQUIVO = "dados_barbearia.xlsx"
USUARIOS = {
    "lb": "cortesnobres",
}

# --- Funções ---
def carregar_dados():
    if os.path.exists(NOME_ARQUIVO):
        try:
            xls = pd.ExcelFile(NOME_ARQUIVO)
            df_ag = pd.read_excel(xls, 'Agendamentos')
            df_sai = pd.read_excel(xls, 'Saidas')
            df_ven = pd.read_excel(xls, 'Vendas')
            for df in [df_ag, df_sai, df_ven]:
                if 'Data' in df.columns:
                    df['Data'] = pd.to_datetime(df['Data']).dt.date
            if 'Horário' in df_ag.columns:
                df_ag['Horário'] = df_ag['Horário'].astype(str).apply(lambda x: x if ':' in x else (f"{int(float(x)):02d}:00" if x.replace('.', '', 1).isdigit() else x))
            return df_ag, df_sai, df_ven
        except Exception as e:
            st.error(f"Erro ao ler o arquivo: {e}")
    return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def salvar_dados(ag, sai, ven):
    try:
        with pd.ExcelWriter(NOME_ARQUIVO) as writer:
            pd.DataFrame(ag).to_excel(writer, sheet_name='Agendamentos', index=False)
            pd.DataFrame(sai).to_excel(writer, sheet_name='Saidas', index=False)
            pd.DataFrame(ven).to_excel(writer, sheet_name='Vendas', index=False)
        st.sidebar.success("Dados salvos com sucesso!")
    except Exception as e:
        st.sidebar.error(f"Erro ao salvar: {e}")

def gerar_horarios(inicio_hora, fim_hora, intervalo_min):
    horarios = []
    current = datetime(1, 1, 1, inicio_hora, 0)
    end = datetime(1, 1, 1, fim_hora, 0)
    while current <= end:
        horarios.append(current.strftime('%H:%M'))
        current += pd.Timedelta(minutes=intervalo_min)
    return horarios

def agendamento_existe(agendamentos, data, horario, barbeiro):
    for ag in agendamentos:
        if ag["Data"] == data and ag["Horário"] == horario and ag["Barbeiro"] == barbeiro:
            return True
    return False

# --- CONFIG PÁGINA ---
st.set_page_config(
    page_title="Registro Diário - Barbearia Lucas Borges",
    page_icon="💈",
    layout="wide"
)

st.markdown("""
<style>
.stButton > button[kind="primary"] { background-color: #4CAF50; color: white; }
.stButton > button[kind="secondary"] { background-color: #f44336; color: white; }
</style>
""", unsafe_allow_html=True)

# --- ESTADOS INICIAIS ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'agendamentos' not in st.session_state:
    st.session_state.agendamentos = []
if 'saidas' not in st.session_state:
    st.session_state.saidas = []
if 'vendas' not in st.session_state:
    st.session_state.vendas = []
if 'dados_carregados' not in st.session_state:
    st.session_state.dados_carregados = False

# --- LOGIN ---
if not st.session_state.logged_in:
    st.title("Acesso Restrito - Registro Diário da Barbearia")
    st.subheader("Faça login para continuar")

    login_col1, login_col2, login_col3 = st.columns([1, 1, 1])
    with login_col2:
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            if username in USUARIOS and USUARIOS[username] == password:
                st.session_state.logged_in = True
                if not st.session_state.dados_carregados:
                    df_ag, df_sai, df_ven = carregar_dados()
                    st.session_state.agendamentos = df_ag.to_dict('records')
                    st.session_state.saidas = df_sai.to_dict('records')
                    st.session_state.vendas = df_ven.to_dict('records')
                    st.session_state.dados_carregados = True
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
else:
    # --- SIDEBAR ---
    st.sidebar.title("Painel de Controle")
    st.sidebar.markdown("---")
    if st.sidebar.button("Salvar Alterações 📂", type="primary"):
        salvar_dados(st.session_state.agendamentos, st.session_state.saidas, st.session_state.vendas)
    st.sidebar.markdown("---")
    st.sidebar.info("Lembre-se de salvar suas alterações antes de sair.")
    if st.sidebar.button("Sair 🔒"):
        st.session_state.logged_in = False
        st.session_state.dados_carregados = False
        st.rerun()

    # --- LOGO ---
    logo_path = "https://github.com/barbearialb/sistemalb/blob/main/icone.png?raw=true"
    if os.path.exists(logo_path):
        st.image(logo_path, width=150, use_container_width=True)
    else:
        st.warning(f"Logo não encontrada em: {logo_path}")

    # --- TÍTULO E ENTRADAS ---
    st.title("Registro Diário da Barbearia Lucas Borges 💼")
    st.markdown("---")

    opcoes_servicos = ["Degradê", "Pezim", "Social", "Tradicional", "Visagismo"]
    opcoes_pagamento = ["Pix", "Dinheiro", "Cartão"]
    opcoes_barbeiros = ["Aluízio", "Lucas Borges"]
    horarios_disponiveis = gerar_horarios(8, 22, 30)
    data_selecionada = st.date_input("Selecione a data", value=datetime.today().date(), format="DD/MM/YYYY")

    # --- TABS ---
    tab1, tab2, tab3 = st.tabs(["🗓️ Agendamentos", "💸 Saídas", "💼 Vendas"])

    # --- AGENDAMENTOS ---
    with tab1:
        st.image(logo_path, width=120)
        st.header(f"Agendamentos - {data_selecionada.strftime('%d/%m/%Y')}")

        with st.expander("➕ Registrar Novo Agendamento"):
            col1, col2, col3 = st.columns(3)
            with col1:
                nome_cliente = st.text_input("Nome do Cliente")
                tipo_servico = st.selectbox("Tipo de Serviço", options=opcoes_servicos)
            with col2:
                horario = st.selectbox("Horário", options=horarios_disponiveis)
                barbeiro = st.selectbox("Barbeiro", options=opcoes_barbeiros)
            with col3:
                pagamento = st.selectbox("Forma de Pagamento", options=opcoes_pagamento)
                valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")

            registrar = st.button("Registrar Agendamento")
            if registrar:
                if not nome_cliente.strip():
                    st.error("O nome do cliente não pode estar vazio.")
                elif valor <= 0:
                    st.error("Valor deve ser maior que zero.")
                elif agendamento_existe(st.session_state.agendamentos, data_selecionada, horario, barbeiro):
                    st.warning("Já existe um agendamento neste horário com esse barbeiro.")
                else:
                    st.session_state.agendamentos.append({
                        "Data": data_selecionada, "Horário": horario,
                        "Cliente": nome_cliente.strip(), "Serviço": tipo_servico,
                        "Barbeiro": barbeiro, "Pagamento": pagamento, "Valor (R$)": valor
                    })
                    st.success(f"Agendamento para {nome_cliente} às {horario} registrado!")
       
        if st.button("📂 Salvar agora", key="save_button"):
            salvar_dados(st.session_state.agendamentos, st.session_state.saidas, st.session_state.vendas)
            st.success("Dados salvos com sucesso!")
            st.rerun()

    # --- RESUMO FINANCEIRO ---
    st.markdown("---")
    st.header("📊 Resumo Financeiro do Dia")
    ag = st.session_state.agendamentos
    sai = st.session_state.saidas
    ven = st.session_state.vendas

    total_ag = sum(reg.get("Valor (R$)", 0) for reg in ag if reg["Data"] == data_selecionada)
    total_sai = sum(reg.get("Valor (R$)", 0) for reg in sai if reg["Data"] == data_selecionada)
    total_ven = sum(reg.get("Valor (R$)", 0) for reg in ven if reg["Data"] == data_selecionada)
    lucro = total_ag + total_ven - total_sai

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("💼 Agendamentos", f"R$ {total_ag:.2f}")
    col2.metric("💼 Vendas", f"R$ {total_ven:.2f}")
    col3.metric("💸 Saídas", f"R$ {total_sai:.2f}")
    col4.metric("📈 Lucro Líquido", f"R$ {lucro:.2f}")