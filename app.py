import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta, time
import json
import hashlib

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

.auth-container {
    max-width: 400px;
    margin: 50px auto;
    padding: 40px;
    background: white;
    border-radius: 10px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.auth-container h2 {
    color: var(--capital-azul);
    text-align: center;
    margin-bottom: 30px;
}

.social-auth-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    padding: 12px;
    margin: 10px 0;
    border: 1px solid #DDD;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 600;
    transition: all 0.3s ease;
}

.social-auth-btn:hover {
    background-color: #F5F5F5;
    border-color: var(--capital-laranja);
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

.historico-card {
    background: white;
    padding: 15px;
    border-left: 4px solid var(--capital-laranja);
    border-radius: 6px;
    margin: 10px 0;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.historico-card h4 {
    margin: 0 0 10px 0;
    color: var(--capital-azul);
}

.historico-card p {
    margin: 5px 0;
    color: var(--capital-cinza);
    font-size: 0.9em;
}

@media (max-width: 768px) {
    .header-capital h1 {
        font-size: 1.8em;
    }
    
    .auth-container {
        max-width: 90%;
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

def criar_tabelas_se_nao_existem():
    """Cria tabelas necessárias se não existirem"""
    queries = [
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            nome VARCHAR(255) NOT NULL,
            telefone VARCHAR(20),
            provider VARCHAR(50),
            provider_id VARCHAR(255),
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS veiculos_usuario (
            id SERIAL PRIMARY KEY,
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
            placa VARCHAR(8) NOT NULL,
            modelo VARCHAR(255) NOT NULL,
            ano INTEGER,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
    ]
    
    for query in queries:
        _, erro = execute_query(query, fetch=False, commit=True)
        if erro and "already exists" not in erro.lower():
            st.error(f"Erro ao criar tabelas: {erro}")
    
    # Recriar tabela agendamentos com estrutura correta
    query_drop = "DROP TABLE IF EXISTS agendamentos CASCADE"
    _, _ = execute_query(query_drop, fetch=False, commit=True)
    
    query_create = """
    CREATE TABLE IF NOT EXISTS agendamentos (
        id SERIAL PRIMARY KEY,
        usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
        veiculo_id INTEGER NOT NULL REFERENCES veiculos_usuario(id),
        data_agendamento DATE NOT NULL,
        hora_agendamento TIME NOT NULL,
        servico VARCHAR(100) NOT NULL,
        status VARCHAR(50) DEFAULT 'confirmado',
        data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    _, erro = execute_query(query_create, fetch=False, commit=True)
    if erro:
        st.error(f"Erro ao criar tabela agendamentos: {erro}")

# Inicializar tabelas
criar_tabelas_se_nao_existem()

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

# Verificar se usuário está logado
if 'usuario_id' not in st.session_state:
    st.session_state.usuario_id = None
    st.session_state.usuario_nome = None
    st.session_state.usuario_email = None

# PÁGINAS
if st.session_state.usuario_id is None:
    # PÁGINA DE LOGIN/REGISTRO
    st.markdown('<div class="auth-container">', unsafe_allow_html=True)
    
    auth_tab = st.tabs(["Login", "Cadastro"])
    
    with auth_tab[0]:
        st.markdown("### 🔐 Fazer Login")
        
        email = st.text_input("Email", key="login_email", placeholder="seu@email.com")
        senha = st.text_input("Senha", type="password", key="login_senha", placeholder="••••••••")
        
        if st.button("Entrar", use_container_width=True, type="primary"):
            if email and senha:
                query = "SELECT id, nome, email FROM usuarios WHERE email = %s"
                resultado, erro = execute_query(query, (email,), fetch=True)
                
                if resultado:
                    st.session_state.usuario_id = resultado[0]['id']
                    st.session_state.usuario_nome = resultado[0]['nome']
                    st.session_state.usuario_email = resultado[0]['email']
                    st.success("✅ Login realizado com sucesso!")
                    st.rerun()
                else:
                    st.error("❌ Email ou senha incorretos!")
            else:
                st.error("❌ Preencha email e senha!")
        
        st.divider()
        st.markdown("**Ou continue com:**")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔵 Google", use_container_width=True):
                st.info("🔗 Integração Google OAuth será implementada aqui")
        
        with col2:
            if st.button("🍎 Apple", use_container_width=True):
                st.info("🔗 Integração Apple Sign In será implementada aqui")
    
    with auth_tab[1]:
        st.markdown("### 📝 Criar Conta")
        
        nome = st.text_input("Nome completo", key="reg_nome", placeholder="João Silva")
        email = st.text_input("Email", key="reg_email", placeholder="seu@email.com")
        telefone = st.text_input("Telefone", key="reg_telefone", placeholder="(67) 99999-9999")
        senha = st.text_input("Senha", type="password", key="reg_senha", placeholder="••••••••")
        senha_confirmacao = st.text_input("Confirmar senha", type="password", key="reg_senha_conf", placeholder="••••••••")
        
        if st.button("Criar Conta", use_container_width=True, type="primary"):
            if all([nome, email, telefone, senha, senha_confirmacao]):
                if senha != senha_confirmacao:
                    st.error("❌ Senhas não conferem!")
                else:
                    query = "INSERT INTO usuarios (nome, email, telefone, provider) VALUES (%s, %s, %s, 'local') RETURNING id"
                    resultado, erro = execute_query(query, (nome, email, telefone), fetch=True, commit=True)
                    
                    if erro:
                        if "unique constraint" in erro.lower():
                            st.error("❌ Este email já está cadastrado!")
                        else:
                            st.error(f"❌ Erro ao cadastrar: {erro}")
                    elif resultado:
                        st.session_state.usuario_id = resultado[0]['id']
                        st.session_state.usuario_nome = nome
                        st.session_state.usuario_email = email
                        st.success("✅ Conta criada com sucesso!")
                        st.rerun()
            else:
                st.error("❌ Preencha todos os campos!")
        
        st.divider()
        st.markdown("**Ou crie com:**")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔵 Google", use_container_width=True, key="reg_google"):
                st.info("🔗 Integração Google OAuth será implementada aqui")
        
        with col2:
            if st.button("🍎 Apple", use_container_width=True, key="reg_apple"):
                st.info("🔗 Integração Apple Sign In será implementada aqui")
    
    st.markdown('</div>', unsafe_allow_html=True)

else:
    # USUÁRIO LOGADO - MENU PRINCIPAL
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown(f"### 👤 Bem-vindo, **{st.session_state.usuario_nome}**!")
    
    with col3:
        if st.button("🚪 Sair"):
            st.session_state.usuario_id = None
            st.session_state.usuario_nome = None
            st.session_state.usuario_email = None
            st.rerun()
    
    menu = st.sidebar.radio("📋 Menu", ["🛞 Novo Agendamento", "🚗 Meus Veículos", "📋 Histórico de Serviços", "⚙️ Configurações", "👨‍💼 Admin"])
    
    if menu == "🛞 Novo Agendamento":
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown("### 🚗 Selecione um veículo")
        
        query = "SELECT id, placa, modelo, ano FROM veiculos_usuario WHERE usuario_id = %s"
        veiculos, erro = execute_query(query, (st.session_state.usuario_id,), fetch=True)
        
        if veiculos:
            opcoes_veiculo = [f"{v['placa']} - {v['modelo']} ({v['ano']})" for v in veiculos]
            veiculo_selecionado = st.selectbox("Veículo *", opcoes_veiculo)
            veiculo_id = veiculos[opcoes_veiculo.index(veiculo_selecionado)]['id']
        else:
            st.warning("⚠️ Você não tem veículos cadastrados! Cadastre um em 'Meus Veículos'")
            veiculo_id = None
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        if veiculo_id:
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
                
                if not hora_selecionada:
                    st.error("❌ Selecione um horário!")
                else:
                    horarios_agendados_check = obter_horarios_agendados(data_str)
                    
                    if hora_selecionada in horarios_agendados_check:
                        st.error(f"❌ Desculpe! Horário {hora_selecionada} já foi agendado por outro cliente!")
                        st.session_state['hora_selecionada'] = None
                        st.rerun()
                    else:
                        query_agendamento = "INSERT INTO agendamentos (usuario_id, veiculo_id, data_agendamento, hora_agendamento, servico, status) VALUES (%s, %s, %s, %s, %s, 'confirmado')"
                        _, erro_agendamento = execute_query(query_agendamento, (st.session_state.usuario_id, veiculo_id, data_str, hora_selecionada, servico), fetch=False, commit=True)
                        
                        if erro_agendamento:
                            st.error(f"❌ Erro ao criar agendamento: {erro_agendamento}")
                        else:
                            st.success(f"✅ Agendamento confirmado para {data_agendamento.strftime('%d/%m/%Y')} às {hora_selecionada}!")
                            st.balloons()
                            st.session_state['hora_selecionada'] = None
    
    elif menu == "🚗 Meus Veículos":
        st.markdown("### 🚗 Meus Veículos")
        
        col1, col2 = st.columns([3, 1])
        
        with col2:
            if st.button("➕ Adicionar Veículo", use_container_width=True):
                st.session_state.adicionar_veiculo = True
        
        if st.session_state.get('adicionar_veiculo', False):
            st.markdown('<div class="form-section">', unsafe_allow_html=True)
            st.markdown("### ➕ Novo Veículo")
            
            placa = st.text_input("Placa *", max_chars=8, placeholder="ABC-1234", key="new_placa")
            modelo = st.text_input("Modelo *", placeholder="Iveco Truck", key="new_modelo")
            ano = st.number_input("Ano", min_value=2000, max_value=2025, step=1, value=2020, key="new_ano")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Adicionar", use_container_width=True, type="primary"):
                    if placa and modelo:
                        query = "INSERT INTO veiculos_usuario (usuario_id, placa, modelo, ano) VALUES (%s, %s, %s, %s)"
                        _, erro = execute_query(query, (st.session_state.usuario_id, placa, modelo, ano), fetch=False, commit=True)
                        
                        if erro:
                            st.error(f"❌ Erro ao adicionar veículo: {erro}")
                        else:
                            st.success("✅ Veículo adicionado!")
                            st.session_state.adicionar_veiculo = False
                            st.rerun()
                    else:
                        st.error("❌ Preencha placa e modelo!")
            
            with col2:
                if st.button("Cancelar", use_container_width=True):
                    st.session_state.adicionar_veiculo = False
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        query = "SELECT id, placa, modelo, ano FROM veiculos_usuario WHERE usuario_id = %s ORDER BY data_criacao DESC"
        veiculos, _ = execute_query(query, (st.session_state.usuario_id,), fetch=True)
        
        if veiculos:
            for v in veiculos:
                st.markdown(f"""
                <div class="historico-card">
                    <h4>🚗 {v['placa']} - {v['modelo']}</h4>
                    <p>Ano: {v['ano']}</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Você não tem veículos cadastrados.")
    
    elif menu == "📋 Histórico de Serviços":
        st.markdown("### 📋 Histórico de Serviços")
        
        query = """
            SELECT 
                a.id, v.placa, v.modelo, a.servico, a.data_agendamento, a.hora_agendamento, a.status
            FROM agendamentos a
            JOIN veiculos_usuario v ON a.veiculo_id = v.id
            WHERE a.usuario_id = %s
            ORDER BY a.data_agendamento DESC
        """
        agendamentos, _ = execute_query(query, (st.session_state.usuario_id,), fetch=True)
        
        if agendamentos:
            for a in agendamentos:
                status_icon = "✅" if a['status'] == 'confirmado' else "❌" if a['status'] == 'cancelado' else "⏳"
                st.markdown(f"""
                <div class="historico-card">
                    <h4>{status_icon} {a['placa']} - {a['modelo']}</h4>
                    <p><strong>Serviço:</strong> {a['servico']}</p>
                    <p><strong>Data:</strong> {a['data_agendamento'].strftime('%d/%m/%Y')} às {a['hora_agendamento']}</p>
                    <p><strong>Status:</strong> {a['status'].upper()}</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Você não tem agendamentos registrados.")
    
    elif menu == "⚙️ Configurações":
        st.markdown("### ⚙️ Configurações da Conta")
        
        st.markdown(f"**Email:** {st.session_state.usuario_email}")
        
        if st.button("🔒 Sair de Todos os Dispositivos"):
            st.session_state.usuario_id = None
            st.session_state.usuario_nome = None
            st.session_state.usuario_email = None
            st.success("✅ Desconectado de todos os dispositivos!")
            st.rerun()
    
    elif menu == "👨‍💼 Admin":
        st.markdown("### 👨‍💼 Painel de Administração")
        
        senha_admin = st.text_input("Senha do admin:", type="password", key="admin_pass")
        
        if senha_admin == "admin123":
            admin_tab = st.tabs(["📋 Agendamentos", "🗑️ Cancelar", "📊 Estatísticas"])
            
            with admin_tab[0]:
                st.markdown("### Agendamentos Confirmados")
                
                query = """
                    SELECT 
                        a.id, u.nome, u.telefone, v.placa, v.modelo,
                        a.data_agendamento, a.hora_agendamento, a.servico, a.status
                    FROM agendamentos a
                    JOIN usuarios u ON a.usuario_id = u.id
                    JOIN veiculos_usuario v ON a.veiculo_id = v.id
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
                
                query_usuarios = "SELECT COUNT(*) as total FROM usuarios"
                usuarios_result, _ = execute_query(query_usuarios, fetch=True)
                usuarios = usuarios_result[0]['total'] if usuarios_result else 0
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total de Agendamentos", total)
                
                with col2:
                    st.metric("Total de Usuários", usuarios)
        else:
            if senha_admin:
                st.error("❌ Senha incorreta!")

st.markdown("""
<div class="marca-footer">
    <p><strong>Capital Pneus e Acessórios</strong></p>
    <p>Rua Ediberto Celestino de Oliveira, 1750 - Centro - Dourados - MS</p>
    <p>Revenda Autorizada <span class="logo-michelin">🛞 MICHELIN</span> & <span class="logo-michelin">BF GOODRICH</span></p>
    <p>📞 (67) 3421-1234 | 📧 contato@capitalpneus.com.br</p>
</div>
""", unsafe_allow_html=True)
