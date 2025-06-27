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
        return pd.DataFrame(columns=['Data', 'Horário', 'Cliente', 'Serviço', 'Barbeiro', 'Pagamento', 'Valor (R$)']), \
               pd.DataFrame(columns=['Data', 'Descrição', 'Valor (R$)']), \
               pd.DataFrame(columns=['Data', 'Item', 'Valor (R$)'])
    except gspread.exceptions.APIError as e:
        st.error(f"Erro da API Google Sheets: {e}. Verifique as permissões da conta de serviço e se as APIs estão ativadas.")
        return pd.DataFrame(columns=['Data', 'Horário', 'Cliente', 'Serviço', 'Barbeiro', 'Pagamento', 'Valor (R$)']), \
               pd.DataFrame(columns=['Data', 'Descrição', 'Valor (R$)']), \
               pd.DataFrame(columns=['Data', 'Item', 'Valor (R$)'])
    except Exception as e:
        st.error(f"Erro inesperado ao carregar dados do Google Sheets: {e}")
        # Retorne DataFrames vazios com as colunas esperadas para evitar erros no restante do app
        return (
            pd.DataFrame(columns=['Data', 'Horário', 'Cliente', 'Serviço', 'Barbeiro', 'Pagamento', 'Valor (R$)']),
            pd.DataFrame(columns=['Data', 'Descrição', 'Valor (R$)']),
            pd.DataFrame(columns=['Data', 'Item', 'Valor (R$)'])
        )

def salvar_dados(agendamentos, saidas, vendas):
    try:
        df_ag = pd.DataFrame(agendamentos)
        df_sai = pd.DataFrame(saidas)
        df_ven = pd.DataFrame(vendas)

        if "Vendedor" not in df_ven.columns:
            df_ven["Vendedor"] = ""
        if 'Data' in df_ag.columns:
            df_ag['Data'] = df_ag['Data'].apply(lambda x: x.strftime('%Y-%m-%d') if isinstance(x, date) else x)
        if 'Data' in df_sai.columns:
            df_sai['Data'] = df_sai['Data'].apply(lambda x: x.strftime('%Y-%m-%d') if isinstance(x, date) else x)
        if 'Data' in df_ven.columns:
            df_ven['Data'] = df_ven['Data'].apply(lambda x: x.strftime('%Y-%m-%d') if isinstance(x, date) else x)

        ws_agendamentos.clear()
        ws_agendamentos.update([df_ag.columns.values.tolist()] + df_ag.values.tolist())

        ws_saidas.clear()
        ws_saidas.update([df_sai.columns.values.tolist()] + df_sai.values.tolist())

        ws_vendas.clear()
        ws_vendas.update([df_ven.columns.values.tolist()] + df_ven.values.tolist())

        st.sidebar.success("Dados salvos no Google Sheets com sucesso!")
    except Exception as e:
        st.sidebar.error(f"Erro ao salvar dados no Google Sheets: {e}")

def gerar_horarios(inicio_hora, fim_hora, intervalo_min):
    horarios = []
    current = datetime(1, 1, 1, inicio_hora, 0)
    end = datetime(1, 1, 1, fim_hora, 0)
    while current <= end:
        horarios.append(current.strftime('%H:%M'))
        current += pd.Timedelta(minutes=intervalo_min)
    return horarios

def agendamento_existe(agendamentos, data, horario, barbeiro, novo_servico):
    agendamentos_mesmo_horario = [
        ag for ag in agendamentos
        if ag["Data"] == data and ag["Horário"] == horario and ag["Barbeiro"] == barbeiro
    ]        
    if not agendamentos_mesmo_horario:
        return False    
    if len(agendamentos_mesmo_horario) == 1:
        servico_existente = agendamentos_mesmo_horario[0]["Serviço"]
        if "Pezim" in servico_existente and "Pezim" in novo_servico:
            return False
        if ("Pezim" in servico_existente and novo_servico != "Pezim") or ("Pezim" in novo_servico and servico_existente != "Pezim"):
            return False
    return True    

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
                st.session_state.logged_in = True
                if not st.session_state.dados_carregados:
                    df_ag, df_sai, df_ven = carregar_dados()
                    st.session_state.agendamentos = df_ag.to_dict('records')
                    st.session_state.saidas = df_sai.to_dict('records')
                    st.session_state.vendas = df_ven.to_dict('records')
                    # Garantir que todos os registros tenham o campo "Pagamento"
                    for agendamento in st.session_state.agendamentos:
                        if "Pagamento" not in agendamento:
                            agendamento["Pagamento"] = "Não informado"  # Valor padrão

                    st.session_state.dados_carregados = True
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
# ... o restante do código ...
else:
    # --- SIDEBAR ---
    st.sidebar.title("Painel de Controle")
    st.sidebar.markdown("---")
    if st.sidebar.button("Salvar Agendamentos 📂", type="primary"):
        salvar_dados(st.session_state.agendamentos, st.session_state.saidas, st.session_state.vendas)
    st.sidebar.markdown("---")
    st.sidebar.info("Lembre-se de salvar suas alterações antes de sair.")
    if st.sidebar.button("Sair 🔒"):
        st.session_state.logged_in = False
        st.session_state.dados_carregados = False
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
                pagamento_combinado = pagamento in ["Dinheiro e Pix", "Cartão e Pix", "Cartão e Dinheiro"]
                if pagamento_combinado:
                    st.markdown("### Valores combinados:")
                    primeiro_valor = st.number_input("Valor 1 (R$)", min_value=0.0, format="%.2f", key="valor1")
                    segundo_valor = st.number_input("Valor 2 (R$)", min_value=0.0, format="%.2f", key="valor2")
                else:
                    valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f", key="valor")

            registrar = st.button("Registrar Agendamento")
            if registrar:
                valor_1_registrado = 0.0
                valor_2_registrado = 0.0
                valor_final = 0.0

                if pagamento_combinado:
                    # CORREÇÃO: Lê os valores do session_state
                    valor_1_registrado = st.session_state.get('valor1', 0.0)
                    valor_2_registrado = st.session_state.get('valor2', 0.0)
                    valor_final = valor_1_registrado + valor_2_registrado
                else:
                    # CORREÇÃO: Lê o valor do session_state usando a chave correta
                    valor_final = st.session_state.get('valor', 0.0)

                if opcao_barba == "Com Barba":
                    servico_final = f"{tipo_servico} com Barba"
                else:
                    servico_final = tipo_servico

                if not nome_cliente.strip():
                    st.error("O nome do cliente não pode estar vazio.")
                elif valor_final <= 0:
                    st.error("O valor total deve ser maior que zero.")
                elif agendamento_existe(st.session_state.agendamentos, data_selecionada, horario, barbeiro, servico_final):
                    st.warning("Já existe um agendamento neste horário com esse barbeiro.")
                elif tipo_servico == "Barba" and opcao_barba == "Com Barba":
                    st.error("Não faz sentido agendar 'Barba com Barba'. Por favor, ajuste sua seleção.")
                else:
                    st.session_state.agendamentos.append({
                        "Data": data_selecionada,
                        "Horário": horario,
                        "Cliente": nome_cliente.strip(),
                        "Serviço": servico_final,
                        "Barbeiro": barbeiro,
                        "Pagamento": pagamento if pagamento else "Não informado",
                        "Valor 1 (R$)": valor_1_registrado,
                        "Valor 2 (R$)": valor_2_registrado,
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
            descricao_saida = st.text_input("Descrição da Saída")
            valor_saida = st.number_input("Valor da Saída (R$)", min_value=0.0, format="%.2f", key="valor_saida")
            registrar_saida = st.button("Registrar Saída", key="btn_registrar_saida")

            if registrar_saida:
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
                        valor_saida = float(saida.get('Valor (R$)', 0) or 0)
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
            item_venda = st.text_input("Item Vendido")
            valor_venda = st.number_input("Valor da Venda (R$)", min_value=0.0, format="%.2f", key="valor_venda")
            vendedor = st.selectbox("Vendedor Responsável", ["Lucas Borges", "Aluízio", "Erik", "Maria"], key="vendedor")
            registrar_venda = st.button("Registrar Venda", key="btn_registrar_venda")

            if registrar_venda:
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
                        valor_venda = float(venda.get('Valor (R$)', 0) or 0)
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
