import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta

# Configuração da página
st.set_page_config(
    page_title="Sistema de Agendamento",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado para botões coloridos do Streamlit
st.markdown("""
<style>
/* Botões verdes para horários disponíveis */
div[data-testid="stButtonContainer"] > button[kind="secondary"] {
    background-color: #10B981 !important;
    color: white !important;
    border: none !important;
}

div[data-testid="stButtonContainer"] > button[kind="secondary"]:hover {
    background-color: #059669 !important;
}

/* Botões azuis para horários selecionados */
div[data-testid="stButtonContainer"] > button[kind="primary"] {
    background-color: #3B82F6 !important;
    color: white !important;
}

div[data-testid="stButtonContainer"] > button[kind="primary"]:hover {
    background-color: #1D4ED8 !important;
}
</style>
""", unsafe_allow_html=True)

# Conectar ao NeonDB com melhor tratamento de erro
def execute_query(query, params=None, fetch=True, commit=False):
    """Executa query no banco com commit opcional"""
    conn = None
    try:
        conn = psycopg2.connect(
            host=st.secrets.get("NEON_HOST", "ep-wispy-smoke-ac9dimqg-pooler.sa-east-1.aws.neon.tech"),
            user=st.secrets.get("NEON_USER", "neondb_owner"),
            password=st.secrets.get("NEON_PASSWORD", "npg_l2IOvsnEW1QZ"),
            database="neondb",
            sslmode="require",
            connect_timeout=5,
            autocommit=False
        )
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(query, params)
        
        if fetch:
            result = cur.fetchall()
        else:
            result = None
        
        if commit or not fetch:
            conn.commit()
        
        cur.close()
        return result, None
        
    except psycopg2.Error as e:
        error_msg = f"Erro SQL: {str(e)}"
        return None, error_msg
    except Exception as e:
        error_msg = f"Erro: {str(e)}"
        return None, error_msg
    finally:
        if conn:
            conn.close()

def gerar_horarios_disponiveis(data_str):
    """Gera horários de 20 em 20 minutos conforme o dia da semana"""
    data = datetime.strptime(data_str, "%Y-%m-%d").date()
    dia_semana = data.weekday()
    
    horarios = []
    
    if dia_semana == 6:
        return horarios
    elif dia_semana == 5:
        hora_inicio = datetime.strptime("08:00", "%H:%M")
        hora_fim = datetime.strptime("12:00", "%H:%M")
    else:
        hora_inicio = datetime.strptime("08:00", "%H:%M")
        hora_fim = datetime.strptime("17:30", "%H:%M")
    
    hora_atual = hora_inicio
    while hora_atual <= hora_fim:
        horarios.append(hora_atual.strftime("%H:%M"))
        hora_atual += timedelta(minutes=20)
    
    return horarios

@st.cache_data(ttl=3600)
def obter_horarios_com_status(data_str):
    """Obtém todos os horários da data com seus status - COM CACHE"""
    data = datetime.strptime(data_str, "%Y-%m-%d").date()
    query = """
        SELECT hora, status FROM horarios_disponiveis
        WHERE data = %s
        ORDER BY hora
    """
    result, error = execute_query(query, (data,), fetch=True, commit=False)
    return result if result else []

# ======================== INTERFACE PRINCIPAL ========================

st.title("📅 Sistema de Agendamento - Capital Truck Center")
st.markdown("---")

# Menu lateral
menu = st.sidebar.radio(
    "Selecione uma opção:",
    ["🏪 Agendar Serviço", "👨‍💼 Painel Admin"]
)

if menu == "🏪 Agendar Serviço":
    st.subheader("Agende seu serviço")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 👤 Dados do Cliente")
        nome_cliente = st.text_input("Nome completo *", placeholder="João Silva", key="nome")
        telefone = st.text_input("Telefone *", placeholder="(67) 99999-9999", key="tel")
        email = st.text_input("Email (opcional)", placeholder="joao@email.com", key="email")
    
    with col2:
        st.markdown("### 🚗 Dados do Veículo")
        placa = st.text_input("Placa *", placeholder="ABC-1234", max_chars=8, key="placa")
        modelo = st.text_input("Modelo *", placeholder="Iveco Truck", key="modelo")
        ano = st.number_input("Ano", min_value=2000, max_value=2025, step=1, key="ano")
    
    st.markdown("### 📅 Data e Horário")
    
    data_minima = datetime.now().date()
    data_maxima = data_minima + timedelta(days=30)
    
    data_agendamento = st.date_input(
        "Selecione a data *",
        min_value=data_minima,
        max_value=data_maxima,
        key="data_input"
    )
    
    data_str = data_agendamento.strftime("%Y-%m-%d")
    
    with st.spinner("⏳ Carregando horários disponíveis..."):
        horarios_status = obter_horarios_com_status(data_str)
    
    if horarios_status:
        st.markdown("#### 📅 Selecione um horário:")
        
        # Separar disponíveis e reservados
        horarios_disponiveis = [h['hora'] for h in horarios_status if h['status'] == 'disponivel']
        horarios_reservados = [h['hora'] for h in horarios_status if h['status'] == 'agendado']
        
        # Mostrar legenda
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write("🟢 **Verde** = Disponível")
        with col2:
            st.write("🔵 **Azul** = Selecionado")
        with col3:
            st.write("⚫ **Cinza** = Reservado")
        
        st.divider()
        
        # HORÁRIOS DISPONÍVEIS com botões verdes
        st.markdown("**Horários disponíveis:**")
        
        hora_selecionada = st.session_state.get('hora_selecionada', None)
        
        num_colunas = 5
        for i in range(0, len(horarios_disponiveis), num_colunas):
            cols = st.columns(num_colunas)
            for j, col in enumerate(cols):
                if i + j < len(horarios_disponiveis):
                    hora = horarios_disponiveis[i + j]
                    
                    if hora == hora_selecionada:
                        # Botão azul (selecionado) - tipo primary
                        if col.button(f"✅ {hora}", key=f"btn_{hora}", use_container_width=True, type="primary"):
                            st.session_state['hora_selecionada'] = None
                    else:
                        # Botão verde (disponível) - tipo secondary
                        if col.button(f"⏰ {hora}", key=f"btn_{hora}", use_container_width=True):
                            st.session_state['hora_selecionada'] = hora
        
        st.divider()
        
        # HORÁRIOS RESERVADOS (desabilitados)
        if horarios_reservados:
            st.markdown("**Horários já reservados:**")
            
            for i in range(0, len(horarios_reservados), num_colunas):
                cols = st.columns(num_colunas)
                for j, col in enumerate(cols):
                    if i + j < len(horarios_reservados):
                        hora = horarios_reservados[i + j]
                        col.button(f"🚫 {hora}", key=f"btn_res_{hora}", use_container_width=True, disabled=True)
        
        # Mostrar seleção atual
        hora_selecionada = st.session_state.get('hora_selecionada', None)
        if hora_selecionada:
            st.success(f"✅ Horário selecionado: **{hora_selecionada}**", icon="✅")
    else:
        st.warning("⚠️ Não há horários disponíveis para esta data (domingo ou feriado)")
    
    st.markdown("### 📝 Tipo de Serviço")
    servico = st.selectbox(
        "Selecione o serviço *",
        ["Troca de Pneus", "Manutenção", "Alinhamento", "Balanceamento", "Outro"],
        key="servico"
    )
    
    st.markdown("---")
    
    if st.button("✅ Confirmar Agendamento", use_container_width=True, type="primary"):
        hora_selecionada = st.session_state.get('hora_selecionada', None)
        
        if not nome_cliente or not telefone or not placa or not modelo or not hora_selecionada:
            st.error("❌ Preencha todos os campos obrigatórios!")
        else:
            # Inserir cliente
            query_cliente = """
                INSERT INTO clientes (nome, telefone, email)
                VALUES (%s, %s, %s)
                RETURNING id
            """
            resultado_cliente, erro_cliente = execute_query(query_cliente, (nome_cliente, telefone, email), fetch=True, commit=True)
            
            if erro_cliente:
                st.error(f"❌ Erro ao cadastrar cliente: {erro_cliente}")
            elif resultado_cliente:
                cliente_id = resultado_cliente[0]['id']
                
                # Inserir veículo
                query_veiculo = """
                    INSERT INTO veiculos (cliente_id, placa, modelo, ano)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """
                resultado_veiculo, erro_veiculo = execute_query(query_veiculo, (cliente_id, placa, modelo, ano), fetch=True, commit=True)
                
                if erro_veiculo:
                    st.error(f"❌ Erro ao cadastrar veículo: {erro_veiculo}")
                elif resultado_veiculo:
                    veiculo_id = resultado_veiculo[0]['id']
                    
                    # Obter ID do horário
                    query_horario = """
                        SELECT id FROM horarios_disponiveis
                        WHERE data = %s AND hora = %s AND status = 'disponivel'
                        LIMIT 1
                    """
                    resultado_horario, erro_horario = execute_query(query_horario, (data_str, hora_selecionada), fetch=True, commit=False)
                    
                    if erro_horario:
                        st.error(f"❌ Erro ao obter horário: {erro_horario}")
                    elif resultado_horario:
                        horario_id = resultado_horario[0]['id']
                        
                        # Inserir agendamento
                        query_agendamento = """
                            INSERT INTO agendamentos (cliente_id, veiculo_id, horario_id, data_agendamento, hora_agendamento, servico, status)
                            VALUES (%s, %s, %s, %s, %s, %s, 'confirmado')
                        """
                        _, erro_agendamento = execute_query(query_agendamento, (cliente_id, veiculo_id, horario_id, data_str, hora_selecionada, servico), fetch=False, commit=True)
                        
                        if erro_agendamento:
                            st.error(f"❌ Erro ao criar agendamento: {erro_agendamento}")
                        else:
                            # Atualizar status do horário
                            query_update_horario = """
                                UPDATE horarios_disponiveis
                                SET status = 'agendado'
                                WHERE id = %s
                            """
                            _, erro_update = execute_query(query_update_horario, (horario_id,), fetch=False, commit=True)
                            
                            if erro_update:
                                st.error(f"❌ Erro ao atualizar horário: {erro_update}")
                            else:
                                st.success(f"✅ Agendamento confirmado para {data_agendamento.strftime('%d/%m/%Y')} às {hora_selecionada}")
                                st.balloons()
                                st.session_state['hora_selecionada'] = None
                                st.cache_data.clear()
                    else:
                        st.error("❌ Erro ao agendar - horário não disponível")
                else:
                    st.error("❌ Erro ao cadastrar veículo")
            else:
                st.error("❌ Erro ao cadastrar cliente")

elif menu == "👨‍💼 Painel Admin":
    st.subheader("Painel de Administração")
    
    senha_admin = st.text_input("Senha do admin:", type="password", key="admin_pass")
    
    if senha_admin == "admin123":
        admin_tab = st.tabs(["📋 Agendamentos", "🗑️ Cancelar", "📊 Estatísticas"])
        
        with admin_tab[0]:
            st.markdown("### Agendamentos Confirmados")
            
            query = """
                SELECT 
                    a.id,
                    c.nome,
                    c.telefone,
                    v.placa,
                    v.modelo,
                    a.data_agendamento,
                    a.hora_agendamento,
                    a.servico,
                    a.status
                FROM agendamentos a
                JOIN clientes c ON a.cliente_id = c.id
                JOIN veiculos v ON a.veiculo_id = v.id
                WHERE a.status = 'confirmado'
                ORDER BY a.data_agendamento, a.hora_agendamento
            """
            agendamentos, erro = execute_query(query, fetch=True)
            
            if agendamentos:
                st.dataframe(agendamentos, use_container_width=True)
            else:
                st.info("Nenhum agendamento encontrado")
        
        with admin_tab[1]:
            st.markdown("### Cancelar Agendamento")
            
            query = """
                SELECT id, data_agendamento, hora_agendamento FROM agendamentos
                WHERE status = 'confirmado'
                ORDER BY data_agendamento DESC
            """
            agendamentos, erro = execute_query(query, fetch=True)
            
            if agendamentos:
                opcoes = [f"{a['data_agendamento']} às {a['hora_agendamento']}" for a in agendamentos]
                selecionado = st.selectbox("Selecione o agendamento para cancelar:", opcoes)
                
                if st.button("❌ Cancelar Agendamento", type="secondary"):
                    idx = opcoes.index(selecionado)
                    agendamento_id = agendamentos[idx]['id']
                    
                    query_cancel = "UPDATE agendamentos SET status = 'cancelado' WHERE id = %s"
                    _, erro_cancel = execute_query(query_cancel, (agendamento_id,), fetch=False, commit=True)
                    
                    if not erro_cancel:
                        query_horario_id = "SELECT horario_id FROM agendamentos WHERE id = %s"
                        result, _ = execute_query(query_horario_id, (agendamento_id,), fetch=True)
                        if result:
                            horario_id = result[0]['horario_id']
                            query_liberar = "UPDATE horarios_disponiveis SET status = 'disponivel' WHERE id = %s"
                            execute_query(query_liberar, (horario_id,), fetch=False, commit=True)
                        
                        st.success("✅ Agendamento cancelado!")
                        st.cache_data.clear()
                    else:
                        st.error(f"❌ Erro ao cancelar: {erro_cancel}")
            else:
                st.info("Nenhum agendamento para cancelar")
        
        with admin_tab[2]:
            st.markdown("### Estatísticas")
            
            query_total = "SELECT COUNT(*) as total FROM agendamentos WHERE status = 'confirmado'"
            total_result, _ = execute_query(query_total, fetch=True)
            total = total_result[0]['total'] if total_result else 0
            
            query_servicos = """
                SELECT servico, COUNT(*) as quantidade
                FROM agendamentos
                WHERE status = 'confirmado'
                GROUP BY servico
            """
            servicos, _ = execute_query(query_servicos, fetch=True)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total de Agendamentos", total)
            
            with col2:
                query_clientes = "SELECT COUNT(DISTINCT cliente_id) as total FROM agendamentos"
                clientes_result, _ = execute_query(query_clientes, fetch=True)
                clientes = clientes_result[0]['total'] if clientes_result else 0
                st.metric("Clientes Únicos", clientes)
            
            if servicos:
                st.markdown("**Agendamentos por Serviço:**")
                for servico in servicos:
                    st.write(f"- {servico['servico']}: {servico['quantidade']}")
    else:
        if senha_admin:
            st.error("❌ Senha incorreta!")
