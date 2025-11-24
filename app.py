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

# CSS customizado para os blocos de horários
st.markdown("""
<style>
.horario-container {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
    gap: 10px;
    margin-top: 20px;
}

.horario-bloco {
    padding: 12px;
    border-radius: 8px;
    text-align: center;
    font-weight: bold;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.3s ease;
    border: 2px solid transparent;
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

.horario-reservado {
    background-color: #D1D5DB;
    color: #6B7280;
    opacity: 0.6;
    cursor: not-allowed;
}

.horario-selecionado {
    background-color: #3B82F6;
    color: white;
    border: 2px solid #1E40AF;
    box-shadow: 0 0 15px rgba(59, 130, 246, 0.5);
}
</style>
""", unsafe_allow_html=True)

# Conectar ao NeonDB
def execute_query(query, params=None, fetch=True):
    """Executa query no banco com tratamento melhorado"""
    conn = None
    try:
        conn = psycopg2.connect(
            host = st.secrets["NEON_HOST"],
            user = st.secrets["NEON_USER"],
            password= st.secrets["NEON_PASSWORD"],
            database="neondb",
            sslmode="require",
            connect_timeout=10
        )
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(query, params)
        
        if fetch:
            result = cur.fetchall()
        else:
            conn.commit()
            result = None
        
        cur.close()
        return result
        
    except psycopg2.OperationalError as e:
        st.error(f"❌ Erro de conexão: {str(e)}")
        return None
    except Exception as e:
        st.error(f"❌ Erro no banco: {str(e)}")
        return None
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

def atualizar_horarios_disponiveis(data_str):
    """Garante que os horários estão no banco para a data especificada"""
    data = datetime.strptime(data_str, "%Y-%m-%d").date()
    horarios = gerar_horarios_disponiveis(data_str)
    
    if not horarios:
        return
    
    for hora in horarios:
        query = """
            INSERT INTO horarios_disponiveis (data, hora, status)
            VALUES (%s, %s, 'disponivel')
            ON CONFLICT (data, hora) DO NOTHING
        """
        execute_query(query, (data, hora), fetch=False)

def obter_horarios_com_status(data_str):
    """Obtém todos os horários da data com seus status"""
    data = datetime.strptime(data_str, "%Y-%m-%d").date()
    query = """
        SELECT hora, status FROM horarios_disponiveis
        WHERE data = %s
        ORDER BY hora
    """
    result = execute_query(query, (data,))
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
        nome_cliente = st.text_input("Nome completo *", placeholder="João Silva")
        telefone = st.text_input("Telefone *", placeholder="(67) 99999-9999")
        email = st.text_input("Email (opcional)", placeholder="joao@email.com")
    
    with col2:
        st.markdown("### 🚗 Dados do Veículo")
        placa = st.text_input("Placa *", placeholder="ABC-1234", max_chars=8)
        modelo = st.text_input("Modelo *", placeholder="Iveco Truck")
        ano = st.number_input("Ano", min_value=2000, max_value=2025, step=1)
    
    st.markdown("### 📅 Data e Horário")
    
    col1, col2 = st.columns(2)
    
    with col1:
        data_minima = datetime.now().date()
        data_maxima = data_minima + timedelta(days=30)
        
        data_agendamento = st.date_input(
            "Selecione a data *",
            min_value=data_minima,
            max_value=data_maxima
        )
    
    data_str = data_agendamento.strftime("%Y-%m-%d")
    atualizar_horarios_disponiveis(data_str)
    
    horarios_status = obter_horarios_com_status(data_str)
    
    if horarios_status:
        st.markdown("#### Selecione o horário:")
        
        # Criar grid de horários com CSS
        cols = st.columns(5)
        hora_selecionada = st.session_state.get('hora_selecionada', None)
        
        html_blocos = '<div class="horario-container">'
        for horario_data in horarios_status:
            hora = horario_data['hora']
            status = horario_data['status']
            
            if status == 'disponivel':
                classe = 'horario-disponivel'
                if hora == hora_selecionada:
                    classe = 'horario-selecionado'
            else:
                classe = 'horario-reservado'
            
            html_blocos += f'<div class="horario-bloco {classe}" onclick="selectHour(\'{hora}\')">{hora}</div>'
        
        html_blocos += '</div>'
        st.markdown(html_blocos, unsafe_allow_html=True)
        
        # Usar botões para seleção (alternativa ao JavaScript)
        st.markdown("**Ou clique no horário abaixo:**")
        
        horarios_disponiveis = [h['hora'] for h in horarios_status if h['status'] == 'disponivel']
        
        if horarios_disponiveis:
            # Criar botões em grid
            num_colunas = 5
            for i in range(0, len(horarios_disponiveis), num_colunas):
                cols = st.columns(num_colunas)
                for j, col in enumerate(cols):
                    if i + j < len(horarios_disponiveis):
                        hora = horarios_disponiveis[i + j]
                        if col.button(f"⏰ {hora}", key=f"btn_{hora}", use_container_width=True):
                            st.session_state['hora_selecionada'] = hora
                            st.rerun()
            
            hora_selecionada = st.session_state.get('hora_selecionada', None)
            if hora_selecionada:
                st.success(f"✅ Horário selecionado: **{hora_selecionada}**")
        else:
            st.warning("⚠️ Não há horários disponíveis para esta data")
            hora_selecionada = None
    else:
        st.warning("⚠️ Não há horários disponíveis para esta data")
        hora_selecionada = None
    
    st.markdown("### 📝 Tipo de Serviço")
    servico = st.selectbox(
        "Selecione o serviço *",
        ["Troca de Pneus", "Manutenção", "Alinhamento", "Balanceamento", "Outro"]
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
            resultado_cliente = execute_query(query_cliente, (nome_cliente, telefone, email), fetch=True)
            
            if resultado_cliente:
                cliente_id = resultado_cliente[0]['id']
                
                # Inserir veículo
                query_veiculo = """
                    INSERT INTO veiculos (cliente_id, placa, modelo, ano)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """
                resultado_veiculo = execute_query(query_veiculo, (cliente_id, placa, modelo, ano), fetch=True)
                
                if resultado_veiculo:
                    veiculo_id = resultado_veiculo[0]['id']
                    
                    # Obter ID do horário
                    query_horario = """
                        SELECT id FROM horarios_disponiveis
                        WHERE data = %s AND hora = %s AND status = 'disponivel'
                        LIMIT 1
                    """
                    resultado_horario = execute_query(query_horario, (data_str, hora_selecionada), fetch=True)
                    
                    if resultado_horario:
                        horario_id = resultado_horario[0]['id']
                        
                        # Inserir agendamento
                        query_agendamento = """
                            INSERT INTO agendamentos (cliente_id, veiculo_id, horario_id, data_agendamento, hora_agendamento, servico, status)
                            VALUES (%s, %s, %s, %s, %s, %s, 'confirmado')
                        """
                        execute_query(query_agendamento, (cliente_id, veiculo_id, horario_id, data_str, hora_selecionada, servico), fetch=False)
                        
                        # Atualizar status do horário
                        query_update_horario = """
                            UPDATE horarios_disponiveis
                            SET status = 'agendado'
                            WHERE id = %s
                        """
                        execute_query(query_update_horario, (horario_id,), fetch=False)
                        
                        st.success(f"✅ Agendamento confirmado para {data_agendamento.strftime('%d/%m/%Y')} às {hora_selecionada}")
                        st.balloons()
                        st.session_state['hora_selecionada'] = None
                    else:
                        st.error("❌ Erro ao agendar - horário não disponível")
                else:
                    st.error("❌ Erro ao cadastrar veículo")
            else:
                st.error("❌ Erro ao cadastrar cliente")

elif menu == "👨‍💼 Painel Admin":
    st.subheader("Painel de Administração")
    
    senha_admin = st.text_input("Senha do admin:", type="password")
    
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
            agendamentos = execute_query(query)
            
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
            agendamentos = execute_query(query)
            
            if agendamentos:
                opcoes = [f"{a['data_agendamento']} às {a['hora_agendamento']}" for a in agendamentos]
                selecionado = st.selectbox("Selecione o agendamento para cancelar:", opcoes)
                
                if st.button("❌ Cancelar Agendamento", type="secondary"):
                    idx = opcoes.index(selecionado)
                    agendamento_id = agendamentos[idx]['id']
                    
                    query_cancel = "UPDATE agendamentos SET status = 'cancelado' WHERE id = %s"
                    execute_query(query_cancel, (agendamento_id,), fetch=False)
                    
                    query_horario_id = "SELECT horario_id FROM agendamentos WHERE id = %s"
                    result = execute_query(query_horario_id, (agendamento_id,))
                    if result:
                        horario_id = result[0]['horario_id']
                        query_liberar = "UPDATE horarios_disponiveis SET status = 'disponivel' WHERE id = %s"
                        execute_query(query_liberar, (horario_id,), fetch=False)
                    
                    st.success("✅ Agendamento cancelado!")
            else:
                st.info("Nenhum agendamento para cancelar")
        
        with admin_tab[2]:
            st.markdown("### Estatísticas")
            
            query_total = "SELECT COUNT(*) as total FROM agendamentos WHERE status = 'confirmado'"
            total_result = execute_query(query_total)
            total = total_result[0]['total'] if total_result else 0
            
            query_servicos = """
                SELECT servico, COUNT(*) as quantidade
                FROM agendamentos
                WHERE status = 'confirmado'
                GROUP BY servico
            """
            servicos = execute_query(query_servicos)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total de Agendamentos", total)
            
            with col2:
                query_clientes = "SELECT COUNT(DISTINCT cliente_id) as total FROM agendamentos"
                clientes_result = execute_query(query_clientes)
                clientes = clientes_result[0]['total'] if clientes_result else 0
                st.metric("Clientes Únicos", clientes)
            
            if servicos:
                st.markdown("**Agendamentos por Serviço:**")
                for servico in servicos:
                    st.write(f"- {servico['servico']}: {servico['quantidade']}")
    else:
        if senha_admin:
            st.error("❌ Senha incorreta!")
