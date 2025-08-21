import streamlit as st
import pandas as pd
from datetime import datetime, date
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# --- CONFIGURAÇÕES ---
USUARIOS = {
    "lb": "cn",
}
# --- Configuração do Google Sheets ---
try:
    credentials_dict = dict(st.secrets["gcp_service_account"])
    
    # A linha abaixo substitui toda a lógica de autenticação antiga
    client = gspread.service_account_from_dict(credentials_dict)

    # O resto do código permanece o mesmo
    SHEET_ID = st.secrets["sheet_id"] # Assumindo que você moveu para a raiz do secrets.toml
    spreadsheet = client.open_by_key(SHEET_ID)

    ws_agendamentos = spreadsheet.worksheet('Agendamentos')
    ws_saidas = spreadsheet.worksheet('Saidas')
    ws_vendas = spreadsheet.worksheet('Vendas')

except Exception as e:
    st.error(f"Erro ao conectar com Google Sheets. Verifique suas credenciais e ID da planilha no .streamlit/secrets.toml: {e}")
    st.stop() # Interrompe a execução se não conseguir conectar

def carregar_dados():
    try:
        # --- Carregar Agendamentos ---
        # Tenta obter todos os valores, incluindo a primeira linha (cabeçalhos)
        all_values_agendamentos = ws_agendamentos.get_all_values()
        if not all_values_agendamentos: # Se a aba está completamente vazia
            df_ag = pd.DataFrame(columns=['Data', 'Horário', 'Cliente', 'Serviço', 'Barbeiro', 'Pagamento', 'Valor (R$)'])
        else:
            # A primeira linha são os cabeçalhos
            headers_ag = all_values_agendamentos[0]
            # O restante são os dados
            data_ag = all_values_agendamentos[1:]
            
            df_ag = pd.DataFrame(data_ag, columns=headers_ag)
            df_ag['Pagamento'] = df_ag.get('Pagamento', 'Não informado')
            
            # Garantir que todas as colunas esperadas existam
            expected_ag_cols = ['Data', 'Horário', 'Cliente', 'Serviço', 'Barbeiro', 'Pagamento', 'Valor 1 (R$)', 'Valor 2 (R$)', 'Valor (R$)']
            for col in expected_ag_cols:
                if col not in df_ag.columns:
                    df_ag[col] = '' # Adiciona a coluna vazia se estiver faltando
            # <<< CORREÇÃO: Converter todas as colunas de valor para numérico, tratando vírgulas >>>
            valor_cols_ag = ['Valor (R$)', 'Valor 1 (R$)', 'Valor 2 (R$)']
            for col in valor_cols_ag:
                if col in df_ag.columns:
                    # Substitui vírgula por ponto e converte para numérico
                    df_ag[col] = df_ag[col].astype(str).str.replace(',', '.', regex=False).str.strip()
                    df_ag[col] = pd.to_numeric(df_ag[col], errors='coerce').fillna(0.0)

        if 'Data' in df_ag.columns:
            df_ag['Data'] = df_ag['Data'].astype(str)
            df_ag['Data'] = pd.to_datetime(df_ag['Data'], errors='coerce').dt.date
        
        # O erro 'Horário' é tratado aqui. Com a leitura de 'all_values', deve funcionar.
        if 'Horário' in df_ag.columns:
            df_ag['Horário'] = df_ag['Horário'].astype(str).apply(
                lambda x: x if ':' in x else (f"{int(float(x)):02d}:00" if x.replace('.', '', 1).isdigit() else x)
            )
        else: # Se por algum motivo 'Horário' ainda não aparecer, isso vai alertar.
            st.warning("Aviso: Coluna 'Horário' não foi encontrada na aba 'Agendamentos' após o carregamento. Verifique sua planilha.")
            # Para evitar erro, podemos adicionar uma coluna vazia, se não tiver sido adicionada já.
            if 'Horário' not in df_ag.columns:
                df_ag['Horário'] = ''


        # --- Carregar Saídas ---
        all_values_saidas = ws_saidas.get_all_values()
        if not all_values_saidas:
            df_sai = pd.DataFrame(columns=['Data', 'Descrição', 'Valor (R$)'])
        else:
            headers_sai = all_values_saidas[0]
            data_sai = all_values_saidas[1:]
            df_sai = pd.DataFrame(data_sai, columns=headers_sai)
            # <<< CORREÇÃO: Substitui vírgula por ponto antes de converter para número >>>
            if 'Valor (R$)' in df_sai.columns:
                df_sai['Valor (R$)'] = df_sai['Valor (R$)'].astype(str).str.replace(',', '.', regex=False).str.strip()
                df_sai['Valor (R$)'] = pd.to_numeric(df_sai['Valor (R$)'], errors='coerce').fillna(0.0)
            expected_sai_cols = ['Data', 'Descrição', 'Valor (R$)']
            for col in expected_sai_cols:
                if col not in df_sai.columns:
                    df_sai[col] = ''

        if 'Data' in df_sai.columns:
            df_sai['Data'] = df_sai['Data'].astype(str)
            df_sai['Data'] = pd.to_datetime(df_sai['Data'], errors='coerce').dt.date


        # --- Carregar Vendas ---
        all_values_vendas = ws_vendas.get_all_values()
        if not all_values_vendas:
            df_ven = pd.DataFrame(columns=['Data', 'Item', 'Valor (R$)'])
        else:
            headers_ven = all_values_vendas[0]
            data_ven = all_values_vendas[1:]
            df_ven = pd.DataFrame(data_ven, columns=headers_ven)
            # <<< CORREÇÃO: Substitui vírgula por ponto antes de converter para número >>>
            if 'Valor (R$)' in df_ven.columns:
                df_ven['Valor (R$)'] = df_ven['Valor (R$)'].astype(str).str.replace(',', '.', regex=False).str.strip()
                df_ven['Valor (R$)'] = pd.to_numeric(df_ven['Valor (R$)'], errors='coerce').fillna(0.0)
            expected_ven_cols = ['Data', 'Item', 'Valor (R$)']
            for col in expected_ven_cols:
                if col not in df_ven.columns:
                    df_ven[col] = ''

        if 'Data' in df_ven.columns:
            df_ven['Data'] = df_ven['Data'].astype(str)
            df_ven['Data'] = pd.to_datetime(df_ven['Data'], errors='coerce').dt.date
            
        return df_ag, df_sai, df_ven
    
    except gspread.exceptions.SpreadsheetNotFound:
        st.error("Planilha Google não encontrada. Verifique o ID no .streamlit/secrets.toml.")
        return None, None, None
    except gspread.exceptions.APIError as e:
        st.error(f"Erro da API Google Sheets: {e}. Verifique as permissões da conta de serviço e se as APIs estão ativadas.")
        return None, None, None
    except Exception as e:
        st.error(f"Erro inesperado ao carregar dados do Google Sheets: {e}")
        return None, None, None

def salvar_dados(agendamentos, saidas, vendas, data_selecionada):
    """
    Salva os dados de forma segura, atualizando apenas as entradas
    para a data selecionada e preservando os dados de outros dias.
    Inclui uma trava de segurança para o dia atual.
    """
    try:
        with st.spinner("Verificando e salvando dados... Por favor, aguarde."):
            
            # --- AGENDAMENTOS ---
            all_ag_sheet = ws_agendamentos.get_all_records()
            df_ag_sheet = pd.DataFrame(all_ag_sheet)
            if not df_ag_sheet.empty and 'Data' in df_ag_sheet.columns:
                df_ag_sheet['Data'] = pd.to_datetime(df_ag_sheet['Data'], errors='coerce').dt.date

            agendamentos_do_dia_app = [ag for ag in agendamentos if ag.get('Data') == data_selecionada]
            agendamentos_do_dia_sheet = pd.DataFrame() # Inicializa como DF vazio
            if not df_ag_sheet.empty:
                agendamentos_do_dia_sheet = df_ag_sheet[df_ag_sheet['Data'] == data_selecionada]

            # --- TRAVA DE SEGURANÇA (CORRIGIDA) ---
            # Se a lista do app está vazia, mas o DataFrame da planilha não está...
            if not agendamentos_do_dia_app and not agendamentos_do_dia_sheet.empty:
                st.sidebar.error(f"SALVAMENTO CANCELADO: O app não possui dados para o dia {data_selecionada.strftime('%d/%m')}, mas a planilha online sim. A operação foi bloqueada para evitar perda de dados.")
                return 

            if not df_ag_sheet.empty:
                df_ag_outros_dias = df_ag_sheet[df_ag_sheet['Data'] != data_selecionada]
            else:
                df_ag_outros_dias = pd.DataFrame()

            df_ag_dia_app = pd.DataFrame(agendamentos_do_dia_app)
            df_ag_final = pd.concat([df_ag_outros_dias, df_ag_dia_app], ignore_index=True)
            
            if 'Data' in df_ag_final.columns:
                df_ag_final['Data'] = df_ag_final['Data'].apply(lambda x: x.strftime('%Y-%m-%d') if isinstance(x, date) else x)

            ws_agendamentos.clear()
            colunas_ag_padrao = ['Data', 'Horário', 'Cliente', 'Serviço', 'Barbeiro', 'Pagamento', 'Valor 1 (R$)', 'Valor 2 (R$)', 'Valor (R$)']
            df_ag_final = df_ag_final.reindex(columns=colunas_ag_padrao).fillna('')
            ws_agendamentos.update([df_ag_final.columns.values.tolist()] + df_ag_final.values.tolist())

            # --- REPETIR PARA SAÍDAS (COM TRAVA CORRIGIDA) ---
            all_sai_sheet = ws_saidas.get_all_records()
            df_sai_sheet = pd.DataFrame(all_sai_sheet)
            if not df_sai_sheet.empty and 'Data' in df_sai_sheet.columns:
                df_sai_sheet['Data'] = pd.to_datetime(df_sai_sheet['Data'], errors='coerce').dt.date

            saidas_do_dia_app = [s for s in saidas if s.get('Data') == data_selecionada]
            saidas_do_dia_sheet = pd.DataFrame()
            if not df_sai_sheet.empty:
                saidas_do_dia_sheet = df_sai_sheet[df_sai_sheet['Data'] == data_selecionada]
            
            if not saidas_do_dia_app and not saidas_do_dia_sheet.empty:
                st.sidebar.error(f"SALVAMENTO DE SAÍDAS CANCELADO: Risco de perda de dados para o dia {data_selecionada.strftime('%d/%m')}.")
                return

            if not df_sai_sheet.empty:
                df_sai_outros_dias = df_sai_sheet[df_sai_sheet['Data'] != data_selecionada]
            else:
                df_sai_outros_dias = pd.DataFrame()
            
            df_sai_dia_app = pd.DataFrame(saidas_do_dia_app)
            df_sai_final = pd.concat([df_sai_outros_dias, df_sai_dia_app], ignore_index=True)
            if 'Data' in df_sai_final.columns:
                df_sai_final['Data'] = df_sai_final['Data'].apply(lambda x: x.strftime('%Y-%m-%d') if isinstance(x, date) else x)
            ws_saidas.clear()
            colunas_sai_padrao = ['Data', 'Descrição', 'Valor (R$)']
            df_sai_final = df_sai_final.reindex(columns=colunas_sai_padrao).fillna('')
            ws_saidas.update([df_sai_final.columns.values.tolist()] + df_sai_final.values.tolist())

            # --- REPETIR PARA VENDAS (COM TRAVA CORRIGIDA) ---
            all_ven_sheet = ws_vendas.get_all_records()
            df_ven_sheet = pd.DataFrame(all_ven_sheet)
            if not df_ven_sheet.empty and 'Data' in df_ven_sheet.columns:
                df_ven_sheet['Data'] = pd.to_datetime(df_ven_sheet['Data'], errors='coerce').dt.date

            vendas_do_dia_app = [v for v in vendas if v.get('Data') == data_selecionada]
            vendas_do_dia_sheet = pd.DataFrame()
            if not df_ven_sheet.empty:
                vendas_do_dia_sheet = df_ven_sheet[df_ven_sheet['Data'] == data_selecionada]
            
            if not vendas_do_dia_app and not vendas_do_dia_sheet.empty:
                st.sidebar.error(f"SALVAMENTO DE VENDAS CANCELADO: Risco de perda de dados para o dia {data_selecionada.strftime('%d/%m')}.")
                return

            if not df_ven_sheet.empty:
                df_ven_outros_dias = df_ven_sheet[df_ven_sheet['Data'] != data_selecionada]
            else:
                df_ven_outros_dias = pd.DataFrame()

            df_ven_dia_app = pd.DataFrame(vendas_do_dia_app)
            df_ven_final = pd.concat([df_ven_outros_dias, df_ven_dia_app], ignore_index=True)
            if 'Data' in df_ven_final.columns:
                df_ven_final['Data'] = df_ven_final['Data'].apply(lambda x: x.strftime('%Y-%m-%d') if isinstance(x, date) else x)
            ws_vendas.clear()
            colunas_ven_padrao = ['Data', 'Item', 'Valor (R$)'] # Removido Vendedor para bater com a planilha
            df_ven_final = df_ven_final.reindex(columns=colunas_ven_padrao).fillna('')
            ws_vendas.update([df_ven_final.columns.values.tolist()] + df_ven_final.values.tolist())

        st.sidebar.success("Dados salvos no Google Sheets com sucesso!")

    except gspread.exceptions.APIError as e:
        st.sidebar.error(f"Erro de API do Google: {e}. Verifique as permissões da planilha.")
    except Exception as e:
        st.sidebar.error(f"Ocorreu um erro inesperado ao salvar: {e}")

def gerar_horarios(inicio_hora, fim_hora, intervalo_min):
    horarios = []
    current = datetime(1, 1, 1, inicio_hora, 0)
    end = datetime(1, 1, 1, fim_hora, 0)
    while current <= end:
        horarios.append(current.strftime('%H:%M'))
        current += pd.Timedelta(minutes=intervalo_min)
    return horarios

# Versão CORRIGIDA
def agendamento_existe(agendamentos, data, horario, barbeiro):
    """Verifica se já existe um agendamento para o mesmo barbeiro no mesmo dia e horário."""
    for ag in agendamentos:
        # Garante que a comparação de datas funcione corretamente
        ag_data = ag.get("Data")
        if isinstance(ag_data, str):
            try:
                ag_data = datetime.strptime(ag_data, '%Y-%m-%d').date()
            except ValueError:
                continue # Pula registros com formato de data inválido

        if (ag_data == data and
            ag.get("Horário") == horario and
            ag.get("Barbeiro") == barbeiro):
            return True # Conflito encontrado!
    return False # Horário livre  

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
# --- LOGIN ---
if not st.session_state.logged_in:
    login_col1, login_col2, login_col3 = st.columns([1, 1, 1])
    with login_col2:
        st.markdown("<h1 style='text-align: center;'>Acesso Restrito</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center;'>Faça login para continuar</h3>", unsafe_allow_html=True)

        # --- LOGO CENTRALIZADA E MAIOR ---
        st.markdown(
            """
            <div style='text-align: center; margin-top: 10px; margin-bottom: 20px;'>
                <img src='https://github.com/barbearialb/sistemalb/blob/main/icone.png?raw=true' width='300'/>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("---")

        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")

        login_button = st.button("Entrar")

        if login_button:
            if username in USUARIOS and USUARIOS[username] == password:
                # Mostra uma mensagem enquanto carrega
                with st.spinner("Conectando e carregando dados..."):
                    df_ag, df_sai, df_ven = carregar_dados()

                # --- VERIFICAÇÃO CRÍTICA ---
                # Verifica se os dados foram realmente carregados
                if df_ag is not None and df_sai is not None and df_ven is not None:
                    # Se o carregamento foi bem-sucedido, prossiga
                    st.session_state.logged_in = True
                    st.session_state.dados_carregados = True

                    st.session_state.agendamentos = df_ag.to_dict('records')
                    st.session_state.saidas = df_sai.to_dict('records')
                    st.session_state.vendas = df_ven.to_dict('records')

                    for agendamento in st.session_state.agendamentos:
                        if "Pagamento" not in agendamento:
                            agendamento["Pagamento"] = "Não informado"

                    st.success("Login e carregamento de dados bem-sucedidos!")
                    st.rerun()
                else:
                    # Se o carregamento falhou, exibe o erro e NÃO faz login
                    st.error("Falha ao carregar os dados da planilha. Verifique a conexão e tente novamente.")
                    # Não altera 'logged_in' ou 'dados_carregados'

            else:
                st.error("Usuário ou senha incorretos.")

# ... o restante do código ...
else:
        # --- SIDEBAR ---
    st.sidebar.title("Painel de Controle")
    st.sidebar.markdown("---")

    # Este é o ÚNICO seletor de data. Ele fica na sidebar.
    data_selecionada = st.sidebar.date_input(
        "Selecione a Data",
        datetime.now().date(),
        format="DD/MM/YYYY"
    )

    if st.sidebar.button("Salvar Agendamentos 📂", type="primary"):
        # A função de salvar usa a data selecionada na sidebar.
        salvar_dados(st.session_state.agendamentos, st.session_state.saidas, st.session_state.vendas, data_selecionada)

    st.sidebar.markdown("---")
    st.sidebar.info("Lembre-se de salvar suas alterações antes de sair.")

    if st.sidebar.button("Sair 🔒"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    # --- TÍTULO E ENTRADAS ---
    st.title("Registro Diário da Barbearia Lucas Borges")
    st.markdown("---")
    opcoes_servicos = ["Degradê", "Pezim", "Barba", "Social", "Tradicional", "Visagismo", "Navalhado"]
    opcoes_pagamento = ["Dinheiro", "Pix", "Cartão", "Dinheiro e Pix", "Cartão e Pix", "Cartão e Dinheiro"]
    opcoes_barbeiros = ["Aluízio", "Lucas Borges", "Erik"]
    horarios_disponiveis = gerar_horarios(8, 22, 30)
    data_selecionada = st.date_input("Selecione a data", value=datetime.today().date(), format="DD/MM/YYYY")

    # --- TABS ---
    tab1, tab2, tab3 = st.tabs(["🗓️ Agendamentos", "💸 Saídas", "💼 Vendas"])

    # --- AGENDAMENTOS ---
    with tab1:
        st.header(f"Agendamentos - {data_selecionada.strftime('%d/%m/%Y')}")

        with st.expander("➕ Registrar Novo Agendamento"):
            # A chave 'form_agendamento_key' ajuda a preservar o estado
            with st.form("form_agendamento", clear_on_submit=True):
                col1, col2, col3 = st.columns(3)
                with col1:
                    nome_cliente = st.text_input("Nome do Cliente")
                    tipo_servico = st.selectbox("Tipo de Serviço", options=opcoes_servicos)
                    opcao_barba = st.selectbox("Barba", options=["Sem Barba", "Com Barba"])
                with col2:
                    horario = st.selectbox("Horário", options=horarios_disponiveis)
                    barbeiro = st.selectbox("Barbeiro", options=opcoes_barbeiros)
                with col3:
                    pagamento = st.selectbox("Forma de Pagamento", options=opcoes_pagamento)
                    
                    st.info("Use 'Valor' para pagamentos simples. Para combinados, use 'Valor 1' e 'Valor 2'.")
                    # Damos 'keys' para ler os valores de forma segura
                    valor = st.number_input("Valor (R$)", value=None, min_value=0.0, format="%.2f", key="valor_unico", placeholder="Digite o valor")
                    st.markdown("---")
                    primeiro_valor = st.number_input("Valor 1 (R$)", value=None, min_value=0.0, format="%.2f", key="valor_p1", placeholder="Digite o valor")
                    segundo_valor = st.number_input("Valor 2 (R$)", value=None, min_value=0.0, format="%.2f", key="valor_p2", placeholder="Digite o valor")

                registrar = st.form_submit_button("Registrar Agendamento")

                if registrar:
                    pagamento_combinado = pagamento in ["Dinheiro e Pix", "Cartão e Pix", "Cartão e Dinheiro"]
                    
                    # Lemos os valores usando st.session_state com as 'keys' que definimos
                    valor_lido = st.session_state.get('valor_unico', 0.0)
                    valor1_lido = st.session_state.get('valor_p1', 0.0)
                    valor2_lido = st.session_state.get('valor_p2', 0.0)

                    valor_final = 0.0
                    if pagamento_combinado:
                        valor_final =(float(valor1_lido) if valor1_lido is not None else 0.0) + \
                                      (float(valor2_lido) if valor2_lido is not None else 0.0)
                    else:
                        valor_final = float(valor_lido) if valor_lido is not None else 0.0

                    if not nome_cliente.strip():
                        st.error("O nome do cliente não pode estar vazio.")
                    elif valor_final <= 0:
                        st.error("O valor total deve ser maior que zero.")
                    elif agendamento_existe(st.session_state.agendamentos, data_selecionada, horario, barbeiro):
                        st.warning("Este barbeiro já possui um agendamento neste horário.")
                    else:
                        # O resto do código continua como antes, mas agora com os valores corretos
                        if opcao_barba == "Com Barba":
                            servico_final = f"{tipo_servico} com Barba"
                        else:
                            servico_final = tipo_servico
                        
                        st.session_state.agendamentos.append({
                            "Data": data_selecionada, "Horário": horario, "Cliente": nome_cliente.strip(),
                            "Serviço": servico_final, "Barbeiro": barbeiro, "Pagamento": pagamento,
                            "Valor 1 (R$)": valor1_lido if pagamento_combinado else 0.0,
                            "Valor 2 (R$)": valor2_lido if pagamento_combinado else 0.0,
                            "Valor (R$)": valor_final
                        })
                        st.success(f"Agendamento para {nome_cliente} às {horario} registrado!")

                    # CORREÇÃO: Deleta as chaves para resetar os campos de valor
                    keys_to_reset = ['valor1', 'valor2', 'valor']
                    for key in keys_to_reset:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()
            
            st.markdown("---")

            agendamentos_do_dia = [
                ag for ag in st.session_state.agendamentos
                if ag ["Data"] == data_selecionada
            ]
            # Na linha 157
            if agendamentos_do_dia:
                st.subheader(f"Agendamentos para {data_selecionada.strftime('%d/%m/%Y')}")

                agendamentos_para_mostrar = sorted(agendamentos_do_dia, key=lambda x: datetime.strptime(x['Horário'], "%H:%M"))

 
        
        # Iterar sobre os agendamentos e adicionar um botão de exclusão
                (col_idx, col_horario, col_cliente, col_servico, col_barbeiro, col_pagamento, 
                 col_v1, col_v2, col_valor, col_acao) = st.columns([0.4, 0.8, 1.8, 1.5, 1.2, 1.2, 0.8, 0.8, 0.8, 0.8])
                with col_idx: st.markdown("**#**")
                with col_horario: st.markdown("**Horário**")
                with col_cliente: st.markdown("**Cliente**")
                with col_servico: st.markdown("**Serviço**")
                with col_barbeiro: st.markdown("**Barbeiro**")
                with col_pagamento: st.markdown("**Pagamento**")
                with col_v1: st.markdown("**Valor 1**")
                with col_v2: st.markdown("**Valor 2**")
                with col_valor: st.markdown("**Total**")
                with col_acao: st.markdown("**Excluir**")
        
                for i, agendamento in enumerate(agendamentos_para_mostrar):
                    (col_idx, col_horario, col_cliente, col_servico, col_barbeiro, col_pagamento, 
                     col_v1, col_v2, col_valor, col_acao) = st.columns([0.4, 0.8, 1.8, 1.5, 1.2, 1.2, 0.8, 0.8, 0.8, 0.8])
                    with col_idx:
                        st.write(i + 1) # Número da linha
                    with col_horario:
                        st.write(agendamento.get("Horário", ""))
                    with col_cliente:
                        st.write(agendamento.get("Cliente", ""))
                    with col_servico:
                        st.write(agendamento.get("Serviço", ""))
                    with col_barbeiro:
                        st.write(agendamento.get("Barbeiro", ""))
                    with col_pagamento:
                        st.write(agendamento.get("Pagamento", ""))
                    with col_v1:
                        try:
                            valor1 = float(agendamento.get('Valor 1 (R$)', 0) or 0)
                            if valor1 > 0:
                                st.write(f"R$ {valor1:.2f}")
                            else:
                                st.write("-") # Mostra um traço se não for pagamento combinado
                        except (ValueError, TypeError):
                            st.write("-")
                    with col_v2:
                        try:
                            valor2 = float(agendamento.get('Valor 2 (R$)', 0) or 0)
                            if valor2 > 0:
                                st.write(f"R$ {valor2:.2f}")
                            else:
                                st.write("-")
                        except (ValueError, TypeError):
                            st.write("-")

                    with col_valor:
                        try:
                            valor = float(agendamento.get('Valor (R$)', 0) or 0)
                        except (ValueError, TypeError):
                            valor = 0.0  # valor padrão caso esteja vazio ou inválido
                        st.write(f"R$ {valor:.2f}")
                    with col_acao:
                        if st.button("🗑️", key=f"delete_ag_{i}_{agendamento['Cliente']}_{agendamento['Horário']}"):
                            # Precisamos encontrar o item original em st.session_state.agendamentos para remover
                            # já que agendamentos_para_mostrar é uma cópia filtrada
                            original_index_to_remove = None
                            for idx, original_ag in enumerate(st.session_state.agendamentos):
                                if original_ag == agendamento:
                                    original_index_to_remove = idx
                                    break
                            
                            if original_index_to_remove is not None:
                                st.session_state.agendamentos.pop(original_index_to_remove)
                                st.success(f"Agendamento de {agendamento['Cliente']} às {agendamento['Horário']} removido!")
                                st.rerun()
            else:
                st.info("Nenhum agendamento registrado para esta data")

                        
                
    with tab2:
        st.header(f"Saídas - {data_selecionada.strftime('%d/%m/%Y')}")

        with st.expander("➕ Registrar Nova Saída"):
            with st.form("form_saida", clear_on_submit=True):
                descricao_saida = st.text_input("Descrição da Saída")
                valor_saida = st.number_input("Valor da Saída (R$)", value=None, min_value=0.0, format="%.2f", placeholder="Digite o valor")
                
                registrar_saida = st.form_submit_button("Registrar Saída")

                if registrar_saida:
                    valor_final_saida = float(valor_saida) if valor_saida is not None else 0.0
                    if not descricao_saida.strip():
                        st.error("A descrição da saída não pode estar vazia.")
                    elif valor_saida <= 0:
                        st.error("O valor da saída deve ser maior que zero.")
                    else:
                        st.session_state.saidas.append({
                            "Data": data_selecionada, "Descrição": descricao_saida.strip(), "Valor (R$)": valor_saida
                        })
                        st.success(f"Saída de R$ {valor_saida:.2f} registrada!")
        st.markdown("---")

        # Exibir saídas do dia
        saidas_do_dia = [
            s for s in st.session_state.saidas
            if s["Data"] == data_selecionada
        ]
        if saidas_do_dia:
           st.subheader(f"Saídas para {data_selecionada.strftime('%d/%m/%Y')}")
           saidas_para_mostrar = list(saidas_do_dia) 
           col_idx, col_data, col_descricao, col_valor_saida, col_acao_saida = st.columns([0.5, 1, 3, 1, 0.7])
           with col_idx: st.markdown("**#**")
           with col_data: st.markdown("**Data**")
           with col_descricao: st.markdown("**Descrição**")
           with col_valor_saida: st.markdown("**Valor (R$)**")
           with col_acao_saida: st.markdown("**Excluir**")
           for i, saida in enumerate(saidas_para_mostrar):
                col_idx, col_data, col_descricao, col_valor_saida, col_acao_saida = st.columns([0.5, 1, 3, 1, 0.7])
                with col_idx:
                    st.write(i + 1)
                with col_data:
                    st.write(saida["Data"].strftime('%d/%m/%Y')) # Formata a data para exibição
                with col_descricao:
                    st.write(saida["Descrição"])
                with col_valor_saida:
                    try:
                        valor_saida = float(str(saida.get('Valor (R$)', 0)).strip().replace(',', '.'))
                    except (ValueError, TypeError):
                        valor_saida = 0.0
                    st.write(f"R$ {valor_saida:.2f}")
                with col_acao_saida:
                    if st.button("🗑️", key=f"delete_saida_{i}_{saida['Descrição']}_{saida['Data']}"):
                        st.session_state.saidas.remove(saida)
                        st.success(f"Saída '{saida['Descrição']}' de R$ {valor_saida:.2f} removida!")
                        st.rerun() # Recarregar a página para atualizar a tabela
        else:
            st.info("Nenhuma saída registrada para esta data.")

    # --- VENDAS ---
    with tab3:
        st.header(f"Vendas - {data_selecionada.strftime('%d/%m/%Y')}")

        with st.expander("➕ Registrar Nova Venda"):
            with st.form("form_venda", clear_on_submit=True):
                item_venda = st.text_input("Item Vendido")
                valor_venda = st.number_input("Valor da Venda (R$)", value=None, min_value=0.0, format="%.2f", placeholder="Digite o valor")
                vendedor = st.selectbox("Vendedor Responsável", ["Lucas Borges", "Aluízio", "Erik", "Maria"], key="vendedor")
                registrar_venda = st.form_submit_button("Registrar Venda")

                if registrar_venda:
                    valor_final_venda = float(valor_venda) if valor_venda is not None else 0.0
                    if not item_venda.strip():
                        st.error("O item vendido não pode estar vazio.")
                    elif valor_venda <= 0:
                        st.error("O valor da venda deve ser maior que zero.")
                    else:
                        st.session_state.vendas.append({
                            "Data": data_selecionada, "Item": item_venda.strip(), "Valor (R$)": valor_venda, "Vendedor": vendedor
                        })
                        st.success(f"Venda de {item_venda} por R$ {valor_venda:.2f} registrada!")

        st.markdown("---")

        # Exibir vendas do dia
        vendas_do_dia = [
            v for v in st.session_state.vendas
            if v["Data"] == data_selecionada
        ]
        if vendas_do_dia:
            st.subheader(f"Vendas para {data_selecionada.strftime('%d/%m/%Y')}")

            vendas_para_mostrar = list(vendas_do_dia) # Criar uma cópia para iterar

            # Cabeçalho da "tabela" manual para Vendas
            col_idx, col_data, col_item, col_valor_venda, col_vendedor_header, col_acao_venda = st.columns([0.5, 1, 2, 1, 1, 0.7])
            with col_idx: st.markdown("**#**")
            with col_data: st.markdown("**Data**")
            with col_item: st.markdown("**Item**")
            with col_valor_venda: st.markdown("**Valor (R$)**")
            with col_vendedor_header: st.markdown("**Vendedor**")
            with col_acao_venda: st.markdown("**Excluir**")

            # Iterar sobre as vendas e adicionar um botão de exclusão
            for i, venda in enumerate(vendas_para_mostrar):
                col_idx, col_data, col_item, col_valor_venda, col_vendedor, col_acao_venda = st.columns([0.5, 1, 2, 1, 1, 0.7])
                
                with col_idx:
                    st.write(i + 1)
                with col_data:
                    st.write(venda["Data"].strftime('%d/%m/%Y')) # Formata a data para exibição
                with col_item:
                    st.write(venda["Item"])
                with col_vendedor:
                    st.write(venda.get("Vendedor", "-"))
                with col_valor_venda:
                    try:
                        valor_venda = float(str(venda.get('Valor (R$)', 0)).strip().replace(',', '.'))
                    except (ValueError, TypeError):
                        valor_venda = 0.0
                    st.write(f"R$ {valor_venda:.2f}")
                with col_acao_venda:
                    if st.button("🗑️", key=f"delete_venda_{i}_{venda['Item']}_{venda['Data']}"):
                        st.session_state.vendas.remove(venda)
                        st.success(f"Venda '{venda['Item']}' de R$ {valor_venda:.2f} removida!")
                        st.rerun()
        else:
            st.info("Nenhuma venda registrada para esta data.")

    # --- RESUMO FINANCEIRO ---
    st.markdown("---")
    st.header("📊 Resumo Financeiro do Dia")
    ag = st.session_state.agendamentos
    sai = st.session_state.saidas
    ven = st.session_state.vendas

    def valor_seguro(valor):
        try:
            return float(valor)
        except (ValueError, TypeError):
            return 0.0
        
    total_ag = sum(valor_seguro(reg.get("Valor (R$)", 0)) for reg in ag if reg.get("Data") == data_selecionada)
    total_sai = sum(valor_seguro(reg.get("Valor (R$)", 0)) for reg in sai if reg.get("Data") == data_selecionada)
    total_ven = sum(valor_seguro(reg.get("Valor (R$)", 0)) for reg in ven if reg.get("Data") == data_selecionada)
    
    lucro = total_ag + total_ven - total_sai
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("💼 Agendamentos", f"R$ {total_ag:.2f}")
    col2.metric("💼 Vendas", f"R$ {total_ven:.2f}")
    col3.metric("💸 Saídas", f"R$ {total_sai:.2f}")
    col4.metric("📈 Lucro Líquido", f"R$ {lucro:.2f}")









