import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta, time

st.set_page_config(
    page_title="Agendamento - Capital Pneus",
    page_icon="🛞",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ESTILO CAPITAL PNEUS - Cores profissionais
st.markdown("""
<style>
:root {
    --capital-azul: #003366;
    --capital-laranja: #FF6600;
    --capital-cinza: #666666;
    --capital-claro: #F5F5F5;
    --michelin-amarelo: #FFD700;
}

body {
    background-color: var(--capital-claro);
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.header-capital {
    background: linear-gradient(135deg, var(--capital-azul) 0%, #004488 100%);
    color: white;
    padding: 30px;
    border-radius: 10px;
    margin-bottom: 30px;
    box-shadow: 0 4px 12px rgba(0, 51, 102, 0.15);
    text-align: center;
}

.header-capital h1 {
    margin: 0;
    font-size: 2.5em;
    font-weight: bold;
    letter-spacing: 1px;
}

.header-capital p {
    margin: 10px 0 0 0;
    font-size: 1em;
    opacity: 0.9;
}

.info-box {
    background-color: #E8F4F8;
    border-left: 4px solid var(--capital-laranja);
    padding: 15px;
    border-radius: 5px;
    margin: 15px 0;
    color: var(--capital-azul);
    font-weight: 500;
}

.form-section {
    background-color: white;
    padding: 25px;
    border-radius: 8px;
    margin: 20px 0;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    border-top: 3px solid var(--capital-laranja);
}

.form-section h3 {
    color: var(--capital-azul);
    margin-top: 0;
    display: flex;
    align-items: center;
    gap: 10px;
}

.horarios-container {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
    gap: 12px;
    margin: 20px 0;
}

/* Botões - Cores Capital Pneus */
.stButton > button {
    border-radius: 6px;
    font-weight: 600;
    transition: all 0.3s ease;
    border: none;
}

.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

/* Botão Verde - Disponível */
[data-testid="stButton"] button:not(:disabled):not([type="secondary"]):not([type="primary"]) {
    background-color: #27AE60 !important;
    color: white !important;
}

[data-testid="stButton"] button:not(:disabled):not([type="secondary"]):not([type="primary"]):hover {
    background-color: #229954 !important;
}

/* Botão Azul - Primário */
[data-testid="stButton"] button[type="primary"] {
    background-color: var(--capital-azul) !important;
    color: white !important;
}

[data-testid="stButton"] button[type="primary"]:hover {
    background-color: #002244 !important;
}

/* Botão Cinza - Desabilitado */
[data-testid="stButton"] button:disabled {
    background-color: #CCCCCC !important;
    color: #666666 !important;
    opacity: 0.6;
    cursor: not-allowed !important;
}

.success-message {
    background-color: #D4EDDA;
    border-left: 4px solid #28A745;
    padding: 15px;
    border-radius: 5px;
    color: #155724;
}

.error-message {
    background-color: #F8D7DA;
    border-left: 4px solid #DC3545;
    padding: 15px;
    border-radius: 5px;
    color: #721C24;
}

.marca-footer {
    text-align: center;
    padding: 20px;
    color: var(--capital-cinza);
    font-size: 0.9em;
    border-top: 1px solid #DDDDDD;
    margin-top: 40px;
}

.logo-michelin {
    display: inline-block;
    margin: 0 10px;
    color: var(--capital-laranja);
    font-weight: bold;
}

@media (max-width: 768px) {
    .header-capital h1 {
        font-size: 1.8em;
    }
    
    .horarios-container {
        grid-template-columns: repeat(3, 1fr);
    }
}
</style>
""", unsafe_allow_html=True)

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

# HEADER
st.markdown("""
<div class="header-capital">
    <h1>🛞 CAPITAL PNEUS</h1>
    <p>Sistema de Agendamento Online</p>
    <p style="font-size: 0.9em; margin-top: 10px;">Revenda Autorizada Michelin & BF Goodrich</p>
</div>
""", unsafe_allow_html=True)

menu = st.sidebar.radio("📋 Menu", ["🛞 Agendar Serviço", "👨‍💼 Painel Admin"])

if menu == "🛞 Agendar Serviço":
    
    st.markdown('<div class="form-section">', unsafe_allow_html=True)
    st.markdown("### 👤 Dados do Cliente")
    
    col1, col2 = st.columns(2)
    
    with col1:
        nome_cliente = st.text_input("Nome completo *", key="nome", placeholder="João Silva")
        email = st.text_input("Email (opcional)", key="email", placeholder="joao@email.com")
    
    with col2:
        telefone = st.text_input("Telefone *", key="tel", placeholder="(67) 99999-9999")
        
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="form-section">', unsafe_allow_html=True)
    st.markdown("### 🚗 Dados do Veículo")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        placa = st.text_input("Placa *", key="placa", max_chars=8, placeholder="ABC-1234")
    with col2:
        modelo = st.text_input("Modelo *", key="modelo", placeholder="Iveco Truck")
    with col3:
        ano = st.number_input("Ano", min_value=2000, max_value=2025, step=1, key="ano", value=2020)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="form-section">', unsafe_allow_html=True)
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
    
    horarios_base = gerar_horarios_base(data_str)
    horarios_agendados = obter_horarios_agendados(data_str)
    
    if horarios_base:
        st.markdown("#### Selecione um horário disponível:")
        st.markdown('<div class="info-box">🟢 Verde = Disponível | ⚫ Cinza = Reservado</div>', unsafe_allow_html=True)
        
        hora_selecionada = st.session_state.get('hora_selecionada', None)
        
        cols = st.columns(5)
        col_index = 0
        
        for hora in horarios_base:
            is_agendado = hora in horarios_agendados
            is_selecionado = hora == hora_selecionada
            
            with cols[col_index % 5]:
                if is_agendado:
                    st.button(
                        f"🚫 {hora}",
                        key=f"agend_{hora}",
                        disabled=True,
                        use_container_width=True
                    )
                elif is_selecionado:
                    if st.button(
                        f"✅ {hora}",
                        key=f"selecionado_{hora}",
                        use_container_width=True,
                        type="primary"
                    ):
                        st.session_state['hora_selecionada'] = None
                        st.rerun()
                else:
                    if st.button(
                        f"⏰ {hora}",
                        key=f"disponivel_{hora}",
                        use_container_width=True
                    ):
                        st.session_state['hora_selecionada'] = hora
                        st.rerun()
            
            col_index += 1
        
        if hora_selecionada:
            if hora_selecionada not in horarios_agendados:
                st.markdown(f'<div class="success-message">✅ Horário selecionado: <strong>{hora_selecionada}</strong></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="error-message">❌ Horário {hora_selecionada} foi agendado!</div>', unsafe_allow_html=True)
                st.session_state['hora_selecionada'] = None
                st.rerun()
    else:
        st.warning("⚠️ Não há horários disponíveis para esta data (domingo ou feriado)")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="form-section">', unsafe_allow_html=True)
    st.markdown("### 📝 Tipo de Serviço")
    servico = st.selectbox(
        "Selecione o serviço *",
        ["Troca de Pneus", "Manutenção", "Alinhamento", "Balanceamento", "Outro"],
        key="servico"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    if st.button("✅ CONFIRMAR AGENDAMENTO", use_container_width=True, type="primary"):
        hora_selecionada = st.session_state.get('hora_selecionada', None)
        
        if not all([nome_cliente, telefone, placa, modelo, hora_selecionada]):
            st.error("❌ Preencha todos os campos obrigatórios!")
        else:
            horarios_agendados_check1 = obter_horarios_agendados(data_str)
            
            if hora_selecionada in horarios_agendados_check1:
                st.error(f"❌ Desculpe! Horário {hora_selecionada} já foi agendado por outro cliente!")
                st.session_state['hora_selecionada'] = None
                st.rerun()
            else:
                query_cliente = "INSERT INTO clientes (nome, telefone, email) VALUES (%s, %s, %s) RETURNING id"
                resultado_cliente, erro_cliente = execute_query(query_cliente, (nome_cliente, telefone, email), fetch=True, commit=True)
                
                if erro_cliente:
                    st.error(f"❌ Erro ao cadastrar cliente: {erro_cliente}")
                elif resultado_cliente:
                    cliente_id = resultado_cliente[0]['id']
                    
                    query_veiculo = "INSERT INTO veiculos (cliente_id, placa, modelo, ano) VALUES (%s, %s, %s, %s) RETURNING id"
                    resultado_veiculo, erro_veiculo = execute_query(query_veiculo, (cliente_id, placa, modelo, ano), fetch=True, commit=True)
                    
                    if erro_veiculo:
                        st.error(f"❌ Erro ao cadastrar veículo: {erro_veiculo}")
                    elif resultado_veiculo:
                        veiculo_id = resultado_veiculo[0]['id']
                        
                        horarios_agendados_check2 = obter_horarios_agendados(data_str)
                        
                        if hora_selecionada in horarios_agendados_check2:
                            st.error("❌ Alguém agendou este horário agora!")
                            st.session_state['hora_selecionada'] = None
                            st.rerun()
                        else:
                            query_agendamento = "INSERT INTO agendamentos (cliente_id, veiculo_id, data_agendamento, hora_agendamento, servico, status) VALUES (%s, %s, %s, %s, %s, 'confirmado')"
                            _, erro_agendamento = execute_query(query_agendamento, (cliente_id, veiculo_id, data_str, hora_selecionada, servico), fetch=False, commit=True)
                            
                            if erro_agendamento:
                                st.error(f"❌ Erro ao criar agendamento: {erro_agendamento}")
                            else:
                                st.success(f"✅ Agendamento confirmado para {data_agendamento.strftime('%d/%m/%Y')} às {hora_selecionada}!")
                                st.balloons()
                                st.session_state['hora_selecionada'] = None
    
    st.markdown("""
    <div class="marca-footer">
        <p><strong>Capital Pneus e Acessórios</strong></p>
        <p>Rua Ediberto Celestino de Oliveira, 1750 - Centro - Dourados - MS</p>
        <p>Revenda Autorizada <span class="logo-michelin">🛞 MICHELIN</span> & <span class="logo-michelin">BF GOODRICH</span></p>
        <p>📞 (67) 3421-1234 | 📧 contato@capitalpneus.com.br</p>
    </div>
    """, unsafe_allow_html=True)

elif menu == "👨‍💼 Painel Admin":
    st.subheader("👨‍💼 Painel de Administração")
    
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
