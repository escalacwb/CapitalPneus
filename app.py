import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta, time

st.set_page_config(
    page_title="Sistema de Agendamento",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)

def execute_query(query, params=None, fetch=True, commit=False):
    """Executa query no banco"""
    conn = None
    try:
        conn = psycopg2.connect(
            host=st.secrets.get("NEON_HOST", "ep-wispy-smoke-ac9dimqg-pooler.sa-east-1.aws.neon.tech"),
            user=st.secrets.get("NEON_USER", "neondb_owner"),
            password=st.secrets.get("NEON_PASSWORD", "npg_l2IOvsnEW1QZ"),
            database="neondb",
            sslmode="require",
            connect_timeout=5
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
        
    except Exception as e:
        return None, str(e)
    finally:
        if conn:
            conn.close()

def normalizar_hora(hora):
    """Converte qualquer formato de hora para HH:MM"""
    if isinstance(hora, time):
        return hora.strftime("%H:%M")
    elif isinstance(hora, str):
        # "08:00:00" -> "08:00"
        # "08:00" -> "08:00"
        return hora[:5]
    else:
        return str(hora)[:5]

def gerar_horarios_base(data_str):
    """Gera horários de 20 em 20 minutos"""
    data = datetime.strptime(data_str, "%Y-%m-%d").date()
    dia_semana = data.weekday()
    
    if dia_semana == 6:
        return []
    elif dia_semana == 5:
        inicio, fim = "08:00", "12:00"
    else:
        inicio, fim = "08:00", "17:30"
    
    horarios = []
    hora_atual = datetime.strptime(inicio, "%H:%M")
    hora_fim = datetime.strptime(fim, "%H:%M")
    
    while hora_atual <= hora_fim:
        horarios.append(hora_atual.strftime("%H:%M"))
        hora_atual += timedelta(minutes=20)
    
    return horarios

def obter_horarios_agendados(data_str):
    """Retorna lista de horários agendados - GARANTIDAMENTE NORMALIZADOS"""
    query = """
        SELECT DISTINCT hora_agendamento 
        FROM agendamentos 
        WHERE data_agendamento = %s AND status = 'confirmado'
    """
    resultado, erro = execute_query(query, (data_str,), fetch=True)
    
    if erro:
        st.error(f"❌ Erro ao buscar agendamentos: {erro}")
        return []
    
    if resultado:
        agendados = []
        for row in resultado:
            hora = row['hora_agendamento']
            hora_normalizada = normalizar_hora(hora)
            agendados.append(hora_normalizada)
        return agendados
    
    return []

st.title("📅 Sistema de Agendamento - Capital Truck Center")
st.markdown("---")

menu = st.sidebar.radio("Selecione uma opção:", ["🏪 Agendar Serviço", "👨‍💼 Painel Admin"])

if menu == "🏪 Agendar Serviço":
    st.subheader("Agende seu serviço")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 👤 Dados do Cliente")
        nome_cliente = st.text_input("Nome completo *", key="nome")
        telefone = st.text_input("Telefone *", key="tel")
        email = st.text_input("Email (opcional)", key="email")
    
    with col2:
        st.markdown("### 🚗 Dados do Veículo")
        placa = st.text_input("Placa *", key="placa", max_chars=8)
        modelo = st.text_input("Modelo *", key="modelo")
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
    
    # Buscar horários base e agendados
    horarios_base = gerar_horarios_base(data_str)
    horarios_agendados = obter_horarios_agendados(data_str)
    
    if horarios_base:
        st.markdown("#### 📅 Selecione um horário:")
        st.info("🟢 Verde = Disponível | ⚫ Cinza = Reservado")
        
        st.divider()
        
        hora_selecionada = st.session_state.get('hora_selecionada', None)
        
        # Grid de horários com cores CORRETAS
        cols = st.columns(5)
        col_index = 0
        
        for hora in horarios_base:
            is_agendado = hora in horarios_agendados
            is_selecionado = hora == hora_selecionada
            
            with cols[col_index % 5]:
                if is_agendado:
                    # BOTÃO CINZA - DESABILITADO
                    st.button(
                        f"🚫 {hora}",
                        key=f"agend_{hora}",
                        disabled=True,
                        use_container_width=True
                    )
                elif is_selecionado:
                    # BOTÃO AZUL - SELECIONADO
                    if st.button(
                        f"✅ {hora}",
                        key=f"selecionado_{hora}",
                        use_container_width=True,
                        type="primary"
                    ):
                        st.session_state['hora_selecionada'] = None
                        st.rerun()
                else:
                    # BOTÃO VERDE - DISPONÍVEL
                    if st.button(
                        f"⏰ {hora}",
                        key=f"disponivel_{hora}",
                        use_container_width=True
                    ):
                        st.session_state['hora_selecionada'] = hora
                        st.rerun()
            
            col_index += 1
        
        st.divider()
        
        if hora_selecionada:
            if hora_selecionada not in horarios_agendados:
                st.success(f"✅ Horário selecionado: **{hora_selecionada}**")
            else:
                st.error(f"❌ Horário {hora_selecionada} foi agendado!")
                st.session_state['hora_selecionada'] = None
                st.rerun()
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
        
        if not all([nome_cliente, telefone, placa, modelo, hora_selecionada]):
            st.error("❌ Preencha todos os campos obrigatórios!")
        else:
            # VALIDAÇÃO 1: Verificar se horário ainda está disponível
            horarios_agendados_check1 = obter_horarios_agendados(data_str)
            
            if hora_selecionada in horarios_agendados_check1:
                st.error(f"❌ Desculpe! Horário {hora_selecionada} já foi agendado por outro cliente!")
                st.session_state['hora_selecionada'] = None
                st.rerun()
            else:
                # Inserir cliente
                query_cliente = "INSERT INTO clientes (nome, telefone, email) VALUES (%s, %s, %s) RETURNING id"
                resultado_cliente, erro_cliente = execute_query(query_cliente, (nome_cliente, telefone, email), fetch=True, commit=True)
                
                if erro_cliente:
                    st.error(f"❌ Erro ao cadastrar cliente: {erro_cliente}")
                elif resultado_cliente:
                    cliente_id = resultado_cliente[0]['id']
                    
                    # Inserir veículo
                    query_veiculo = "INSERT INTO veiculos (cliente_id, placa, modelo, ano) VALUES (%s, %s, %s, %s) RETURNING id"
                    resultado_veiculo, erro_veiculo = execute_query(query_veiculo, (cliente_id, placa, modelo, ano), fetch=True, commit=True)
                    
                    if erro_veiculo:
                        st.error(f"❌ Erro ao cadastrar veículo: {erro_veiculo}")
                    elif resultado_veiculo:
                        veiculo_id = resultado_veiculo[0]['id']
                        
                        # VALIDAÇÃO 2: Verificar novamente antes de agendar
                        horarios_agendados_check2 = obter_horarios_agendados(data_str)
                        
                        if hora_selecionada in horarios_agendados_check2:
                            st.error("❌ Alguém agendou este horário agora!")
                            st.session_state['hora_selecionada'] = None
                            st.rerun()
                        else:
                            # Inserir agendamento
                            query_agendamento = "INSERT INTO agendamentos (cliente_id, veiculo_id, data_agendamento, hora_agendamento, servico, status) VALUES (%s, %s, %s, %s, %s, 'confirmado')"
                            _, erro_agendamento = execute_query(query_agendamento, (cliente_id, veiculo_id, data_str, hora_selecionada, servico), fetch=False, commit=True)
                            
                            if erro_agendamento:
                                st.error(f"❌ Erro ao criar agendamento: {erro_agendamento}")
                            else:
                                st.success(f"✅ Agendamento confirmado para {data_agendamento.strftime('%d/%m/%Y')} às {hora_selecionada}!")
                                st.balloons()
                                st.session_state['hora_selecionada'] = None

elif menu == "👨‍💼 Painel Admin":
    st.subheader("Painel de Administração")
    
    senha_admin = st.text_input("Senha do admin:", type="password", key="admin_pass")
    
    if senha_admin == "admin123":
        admin_tab = st.tabs(["📋 Agendamentos", "🗑️ Cancelar", "📊 Estatísticas"])
        
        with admin_tab[0]:
            st.markdown("### Agendamentos Confirmados")
            
            query = """
                SELECT 
                    a.id, c.nome, c.telefone, v.placa, v.modelo,
                    a.data_agendamento, a.hora_agendamento, a.servico, a.status
                FROM agendamentos a
                JOIN clientes c ON a.cliente_id = c.id
                JOIN veiculos v ON a.veiculo_id = v.id
                WHERE a.status = 'confirmado'
                ORDER BY a.data_agendamento, a.hora_agendamento
            """
            agendamentos, _ = execute_query(query, fetch=True)
            
            if agendamentos:
                st.dataframe(agendamentos, use_container_width=True)
            else:
                st.info("Nenhum agendamento encontrado")
        
        with admin_tab[1]:
            st.markdown("### Cancelar Agendamento")
            
            query = "SELECT id, data_agendamento, hora_agendamento FROM agendamentos WHERE status = 'confirmado' ORDER BY data_agendamento DESC"
            agendamentos, _ = execute_query(query, fetch=True)
            
            if agendamentos:
                opcoes = [f"{a['data_agendamento']} às {a['hora_agendamento']}" for a in agendamentos]
                selecionado = st.selectbox("Selecione o agendamento para cancelar:", opcoes)
                
                if st.button("❌ Cancelar Agendamento", type="secondary"):
                    idx = opcoes.index(selecionado)
                    agendamento_id = agendamentos[idx]['id']
                    
                    query_cancel = "UPDATE agendamentos SET status = 'cancelado' WHERE id = %s"
                    _, erro_cancel = execute_query(query_cancel, (agendamento_id,), fetch=False, commit=True)
                    
                    if not erro_cancel:
                        st.success("✅ Agendamento cancelado!")
                        st.rerun()
                    else:
                        st.error(f"❌ Erro ao cancelar: {erro_cancel}")
            else:
                st.info("Nenhum agendamento para cancelar")
        
        with admin_tab[2]:
            st.markdown("### Estatísticas")
            
            query_total = "SELECT COUNT(*) as total FROM agendamentos WHERE status = 'confirmado'"
            total_result, _ = execute_query(query_total, fetch=True)
            total = total_result[0]['total'] if total_result else 0
            
            query_servicos = "SELECT servico, COUNT(*) as quantidade FROM agendamentos WHERE status = 'confirmado' GROUP BY servico"
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
                for s in servicos:
                    st.write(f"- {s['servico']}: {s['quantidade']}")
    else:
        if senha_admin:
            st.error("❌ Senha incorreta!")
