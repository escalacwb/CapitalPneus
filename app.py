import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import json

# Configuração da página
st.set_page_config(
    page_title="Sistema de Agendamento",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS e JavaScript customizado para horários interativos
st.markdown("""
<style>
.horario-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 10px;
    margin: 20px 0;
}

.horario-btn {
    padding: 15px;
    border: none;
    border-radius: 8px;
    font-weight: bold;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.3s ease;
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
    opacity: 0.6;
    cursor: not-allowed !important;
}

.horario-agendado:hover {
    background-color: #9CA3AF;
    transform: none;
    box-shadow: none;
    cursor: not-allowed !important;
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
""", unsafe_allow_html=True)

# Conectar ao NeonDB
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
        
    except psycopg2.Error as e:
        error_msg = f"Erro SQL: {str(e)}"
        return None, error_msg
    except Exception as e:
        error_msg = f"Erro: {str(e)}"
        return None, error_msg
    finally:
        if conn:
            conn.close()

def gerar_horarios_base(data_str):
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

def obter_horarios_com_status(data_str):
    """Gera horários base e busca quais foram agendados"""
    horarios_base = gerar_horarios_base(data_str)
    
    if not horarios_base:
        return []
    
    query = """
        SELECT DISTINCT hora_agendamento 
        FROM agendamentos 
        WHERE data_agendamento = %s AND status = 'confirmado'
    """
    agendados, erro = execute_query(query, (data_str,), fetch=True, commit=False)
    
    horarios_agendados = set()
    if agendados:
        for row in agendados:
            horarios_agendados.add(row['hora_agendamento'])
    
    horarios_com_status = []
    for hora in horarios_base:
        status = 'agendado' if hora in horarios_agendados else 'disponivel'
        horarios_com_status.append({'hora': hora, 'status': status})
    
    return horarios_com_status

# ======================== INTERFACE PRINCIPAL ========================

st.title("📅 Sistema de Agendamento - Capital Truck Center")
st.markdown("---")

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
    horarios_status = obter_horarios_com_status(data_str)
    
    if horarios_status:
        st.markdown("#### 📅 Selecione um horário:")
        
        # Legenda com cores reais
        st.markdown(
            '<div><span class="legenda-item legenda-verde">🟢 Verde = Disponível</span>'
            '<span class="legenda-item legenda-cinza">⚫ Cinza = Reservado</span>'
            '<span class="legenda-item legenda-azul">🔵 Azul = Selecionado</span></div>',
            unsafe_allow_html=True
        )
        
        st.divider()
        
        # Gerar HTML dos botões
        html_horarios = '<div class="horario-grid">'
        
        hora_selecionada = st.session_state.get('hora_selecionada', None)
        
        for h in horarios_status:
            hora = h['hora']
            status = h['status']
            
            if status == 'agendado':
                classe = 'horario-agendado'
                icone = '🚫'
                onclick = ''
            elif hora == hora_selecionada:
                classe = 'horario-selecionado'
                icone = '✅'
                onclick = f'onclick="document.getElementById(\'deselecionar\').click()"'
            else:
                classe = 'horario-disponivel'
                icone = '⏰'
                onclick = f'onclick="document.getElementById(\'selecionar_{hora.replace(":", "")}\').click()"'
            
            html_horarios += f'<button class="horario-btn {classe}" {onclick} {"disabled" if status == "agendado" else ""}>{icone} {hora}</button>'
        
        html_horarios += '</div>'
        st.markdown(html_horarios, unsafe_allow_html=True)
        
        st.divider()
        
        # Botões ocultos para capturar seleção
        col_hidden1, col_hidden2 = st.columns(2)
        
        with col_hidden1:
            for h in horarios_status:
                hora = h['hora']
                if h['status'] == 'disponivel':
                    if st.button(f"Selecionar {hora}", key=f"selecionar_{hora.replace(':', '')}", label_visibility="collapsed"):
                        st.session_state['hora_selecionada'] = hora
                        st.rerun()
        
        with col_hidden2:
            if st.button("Deselecionar", key="deselecionar", label_visibility="collapsed"):
                st.session_state['hora_selecionada'] = None
                st.rerun()
        
        # Mostrar seleção
        hora_selecionada = st.session_state.get('hora_selecionada', None)
        if hora_selecionada:
            st.success(f"✅ Horário selecionado: **{hora_selecionada}**")
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
                    
                    query_verificar = """
                        SELECT id FROM agendamentos 
                        WHERE data_agendamento = %s AND hora_agendamento = %s AND status = 'confirmado'
                        LIMIT 1
                    """
                    verificacao, _ = execute_query(query_verificar, (data_str, hora_selecionada), fetch=True, commit=False)
                    
                    if verificacao:
                        st.error("❌ Desculpe! Este horário foi agendado por outro cliente. Escolha outro!")
                    else:
                        query_agendamento = """
                            INSERT INTO agendamentos (cliente_id, veiculo_id, data_agendamento, hora_agendamento, servico, status)
                            VALUES (%s, %s, %s, %s, %s, 'confirmado')
                        """
                        _, erro_agendamento = execute_query(query_agendamento, (cliente_id, veiculo_id, data_str, hora_selecionada, servico), fetch=False, commit=True)
                        
                        if erro_agendamento:
                            st.error(f"❌ Erro ao criar agendamento: {erro_agendamento}")
                        else:
                            st.success(f"✅ Agendamento confirmado para {data_agendamento.strftime('%d/%m/%Y')} às {hora_selecionada}")
                            st.balloons()
                            st.session_state['hora_selecionada'] = None
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
