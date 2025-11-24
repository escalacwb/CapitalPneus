import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import pandas as pd
import hashlib

# Configuração da página
st.set_page_config(
    page_title="Sistema de Agendamento",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Conectar ao NeonDB
@st.cache_resource
def get_db_connection():
    conn = psycopg2.connect(
        host="ep-wispy-smoke-ac9dimqg-pooler.sa-east-1.aws.neon.tech",
        user="neondb_owner",
        password="npg_l2IOvsnEW1QZ",
        database="neondb",
        sslmode="require"
    )
    return conn

def execute_query(query, params=None, fetch=True):
    """Executa query no banco"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(query, params)
        
        if fetch:
            result = cur.fetchall()
        else:
            conn.commit()
            result = None
        
        cur.close()
        conn.close()
        return result
    except Exception as e:
        st.error(f"Erro no banco: {str(e)}")
        return None

def gerar_horarios_disponiveis(data_str):
    """Gera horários de 20 em 20 minutos conforme o dia da semana"""
    data = datetime.strptime(data_str, "%Y-%m-%d").date()
    dia_semana = data.weekday()  # 0=seg, 4=sex, 5=sab, 6=dom
    
    horarios = []
    
    if dia_semana == 6:  # Domingo - fechado
        return horarios
    elif dia_semana == 5:  # Sábado: 08:00 - 12:00
        hora_inicio = datetime.strptime("08:00", "%H:%M")
        hora_fim = datetime.strptime("12:00", "%H:%M")
    else:  # Segunda a sexta: 08:00 - 17:30
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

def obter_horarios_disponiveis(data_str):
    """Obtém horários disponíveis para uma data"""
    data = datetime.strptime(data_str, "%Y-%m-%d").date()
    query = """
        SELECT hora FROM horarios_disponiveis
        WHERE data = %s AND status = 'disponivel'
        ORDER BY hora
    """
    result = execute_query(query, (data,))
    return [row['hora'] for row in result] if result else []

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
        # Data mínima = hoje, máxima = próximos 30 dias
        data_minima = datetime.now().date()
        data_maxima = data_minima + timedelta(days=30)
        
        data_agendamento = st.date_input(
            "Selecione a data *",
            min_value=data_minima,
            max_value=data_maxima
        )
    
    with col2:
        data_str = data_agendamento.strftime("%Y-%m-%d")
        atualizar_horarios_disponiveis(data_str)
        
        horarios = obter_horarios_disponiveis(data_str)
        
        if horarios:
            hora_agendamento = st.selectbox("Selecione o horário *", horarios)
        else:
            st.warning("⚠️ Não há horários disponíveis para esta data")
            hora_agendamento = None
    
    st.markdown("### 📝 Tipo de Serviço")
    servico = st.selectbox(
        "Selecione o serviço *",
        ["Troca de Pneus", "Manutenção", "Alinhamento", "Balanceamento", "Outro"]
    )
    
    st.markdown("---")
    
    if st.button("✅ Confirmar Agendamento", use_container_width=True, type="primary"):
        # Validações
        if not nome_cliente or not telefone or not placa or not modelo or not hora_agendamento:
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
                    resultado_horario = execute_query(query_horario, (data_str, hora_agendamento), fetch=True)
                    
                    if resultado_horario:
                        horario_id = resultado_horario[0]['id']
                        
                        # Inserir agendamento
                        query_agendamento = """
                            INSERT INTO agendamentos (cliente_id, veiculo_id, horario_id, data_agendamento, hora_agendamento, servico, status)
                            VALUES (%s, %s, %s, %s, %s, %s, 'confirmado')
                        """
                        execute_query(query_agendamento, (cliente_id, veiculo_id, horario_id, data_str, hora_agendamento, servico), fetch=False)
                        
                        # Atualizar status do horário
                        query_update_horario = """
                            UPDATE horarios_disponiveis
                            SET status = 'agendado'
                            WHERE id = %s
                        """
                        execute_query(query_update_horario, (horario_id,), fetch=False)
                        
                        st.success(f"✅ Agendamento confirmado para {data_agendamento.strftime('%d/%m/%Y')} às {hora_agendamento}")
                        st.balloons()
                    else:
                        st.error("❌ Erro ao agendar - horário não disponível")
                else:
                    st.error("❌ Erro ao cadastrar veículo")
            else:
                st.error("❌ Erro ao cadastrar cliente")

elif menu == "👨‍💼 Painel Admin":
    st.subheader("Painel de Administração")
    
    # Senha simples (mude para segurança melhor em produção)
    senha_admin = st.text_input("Senha do admin:", type="password")
    
    if senha_admin == "admin123":  # Mude isso!
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
                df = pd.DataFrame(agendamentos)
                df['data_agendamento'] = pd.to_datetime(df['data_agendamento']).dt.strftime('%d/%m/%Y')
                st.dataframe(df, use_container_width=True)
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
                    
                    # Cancelar agendamento
                    query_cancel = "UPDATE agendamentos SET status = 'cancelado' WHERE id = %s"
                    execute_query(query_cancel, (agendamento_id,), fetch=False)
                    
                    # Liberar horário
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
            
            # Total de agendamentos
            query_total = "SELECT COUNT(*) as total FROM agendamentos WHERE status = 'confirmado'"
            total = execute_query(query_total)[0]['total']
            
            # Agendamentos por serviço
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
                st.metric("Clientes Únicos", execute_query("SELECT COUNT(DISTINCT cliente_id) as total FROM agendamentos")[0]['total'])
            
            if servicos:
                st.markdown("**Agendamentos por Serviço:**")
                df_servicos = pd.DataFrame(servicos)
                st.bar_chart(df_servicos.set_index('servico'))
    else:
        if senha_admin:
            st.error("❌ Senha incorreta!")
