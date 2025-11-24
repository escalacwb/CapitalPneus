import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta

st.set_page_config(
    page_title="Sistema de Agendamento",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.horario-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 10px;
    margin: 20px 0;
}

.horario-container {
    display: flex;
    justify-content: center;
}

.horario-btn {
    width: 100%;
    padding: 15px;
    border: none;
    border-radius: 8px;
    font-weight: bold;
    font-size: 14px;
    transition: all 0.3s ease;
    cursor: pointer;
    text-align: center;
    font-family: Arial, sans-serif;
}

.horario-disponivel {
    background-color: #10B981;
    color: white;
}

.horario-disponivel:hover {
    background-color: #059669;
    transform: scale(1.05);
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}

.horario-agendado {
    background-color: #9CA3AF;
    color: #4B5563;
    cursor: not-allowed;
    opacity: 0.6;
}

.horario-agendado:hover {
    background-color: #9CA3AF;
    transform: none;
    box-shadow: none;
    cursor: not-allowed;
}

.horario-selecionado {
    background-color: #3B82F6;
    color: white;
    border: 2px solid #1E40AF;
    box-shadow: 0 0 15px rgba(59, 130, 246, 0.5);
}

.horario-selecionado:hover {
    background-color: #1D4ED8;
}

.legenda-item {
    display: inline-block;
    margin: 0 15px 10px 0;
    padding: 8px 12px;
    border-radius: 6px;
    font-weight: bold;
    font-size: 14px;
}

.legenda-verde {
    background-color: #10B981;
    color: white;
}

.legenda-azul {
    background-color: #3B82F6;
    color: white;
}

.legenda-cinza {
    background-color: #9CA3AF;
    color: white;
}

@media (max-width: 768px) {
    .horario-grid {
        grid-template-columns: repeat(3, 1fr);
    }
}
</style>

<script>
function selecionarHorario(hora) {
    window.parent.postMessage({type: 'streamlit:setComponentValue', value: hora}, '*');
}

function deselecionarHorario() {
    window.parent.postMessage({type: 'streamlit:setComponentValue', value: null}, '*');
}
</script>
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

def verificar_horario_disponivel(data_str, hora):
    """Verifica se horário está disponível"""
    query = """
        SELECT COUNT(*) as count FROM agendamentos 
        WHERE data_agendamento = %s AND hora_agendamento = %s AND status = 'confirmado'
    """
    result, erro = execute_query(query, (data_str, hora), fetch=True)
    
    if erro or not result:
        return False
    
    return result[0]['count'] == 0

def obter_horarios_status_completo(data_str):
    """Retorna status EXATO de cada horário"""
    horarios_base = gerar_horarios_base(data_str)
    
    if not horarios_base:
        return {}
    
    query = """
        SELECT DISTINCT hora_agendamento 
        FROM agendamentos 
        WHERE data_agendamento = %s AND status = 'confirmado'
    """
    resultado, _ = execute_query(query, (data_str,), fetch=True)
    
    agendados = set()
    if resultado:
        for row in resultado:
            agendados.add(row['hora_agendamento'])
    
    horarios_com_status = {}
    for hora in horarios_base:
        horarios_com_status[hora] = 'agendado' if hora in agendados else 'disponivel'
    
    return horarios_com_status

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
    horarios_status = obter_horarios_status_completo(data_str)
    
    if horarios_status:
        st.markdown("#### 📅 Selecione um horário:")
        
        st.markdown(
            '<div><span class="legenda-item legenda-verde">🟢 Verde = Disponível</span>'
            '<span class="legenda-item legenda-cinza">⚫ Cinza = Reservado</span>'
            '<span class="legenda-item legenda-azul">🔵 Azul = Selecionado</span></div>',
            unsafe_allow_html=True
        )
        
        st.divider()
        
        hora_selecionada = st.session_state.get('hora_selecionada', None)
        
        # Renderizar grid de horários com HTML puro
        html_grid = '<div class="horario-grid">'
        
        for hora in sorted(horarios_status.keys()):
            status = horarios_status[hora]
            
            if status == 'agendado':
                classe = 'horario-agendado'
                icone = '🚫'
                html_grid += f'<div class="horario-container"><button class="horario-btn {classe}" disabled>{icone} {hora}</button></div>'
            elif hora == hora_selecionada:
                classe = 'horario-selecionado'
                icone = '✅'
                html_grid += f'<div class="horario-container"><button class="horario-btn {classe}" onclick="deselecionarHorario()">{icone} {hora}</button></div>'
            else:
                classe = 'horario-disponivel'
                icone = '⏰'
                html_grid += f'<div class="horario-container"><button class="horario-btn {classe}" onclick="selecionarHorario(\'{hora}\')">{icone} {hora}</button></div>'
        
        html_grid += '</div>'
        st.markdown(html_grid, unsafe_allow_html=True)
        
        st.divider()
        
        # Campo oculto para sincronizar com Streamlit
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🔄 Atualizar", use_container_width=True, key="refresh"):
                st.rerun()
        
        with col2:
            if hora_selecionada:
                if st.button("❌ Desselecionar", use_container_width=True, key="desel"):
                    st.session_state['hora_selecionada'] = None
                    st.rerun()
        
        with col3:
            pass
        
        st.divider()
        
        if hora_selecionada:
            if verificar_horario_disponivel(data_str, hora_selecionada):
                st.success(f"✅ Horário selecionado: **{hora_selecionada}**")
            else:
                st.error(f"❌ Horário {hora_selecionada} não está mais disponível!")
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
            if not verificar_horario_disponivel(data_str, hora_selecionada):
                st.error(f"❌ Desculpe! Horário {hora_selecionada} já foi agendado. Escolha outro!")
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
                        
                        if not verificar_horario_disponivel(data_str, hora_selecionada):
                            st.error("❌ Alguém agendou este horário no último momento! Tente outro.")
                            st.session_state['hora_selecionada'] = None
                            st.rerun()
                        else:
                            query_agendamento = "INSERT INTO agendamentos (cliente_id, veiculo_id, data_agendamento, hora_agendamento, servico, status) VALUES (%s, %s, %s, %s, %s, 'confirmado')"
                            _, erro_agendamento = execute_query(query_agendamento, (cliente_id, veiculo_id, data_str, hora_selecionada, servico), fetch=False, commit=True)
                            
                            if erro_agendamento:
                                st.error(f"❌ Erro ao criar agendamento: {erro_agendamento}")
                            else:
                                st.success(f"✅ Agendamento confirmado para {data_agendamento.strftime('%d/%m/%Y')} às {hora_selecionada}")
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
