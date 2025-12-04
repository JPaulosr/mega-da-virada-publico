import streamlit as st
import pandas as pd
import sys
import os

# --- AJUSTE DE PATH (Para garantir que utils_mb seja encontrado) ---
# Adiciona o diretório atual ao path do Python
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Tenta importar. Se falhar, mostra erro amigável.
try:
    from utils_mb import load_bets, load_players, load_contributions, _to_int_list, money
except ImportError as e:
    st.error(f"Erro crítico: Não foi possível importar 'utils_mb'. Detalhes: {e}")
    st.info("Verifique se o arquivo 'utils_mb.py' está na mesma pasta que este script no GitHub.")
    st.stop()

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Resumo do Bolão", page_icon="📢", layout="wide")

# --- CABEÇALHO ---
st.title("📢 Transparência do Bolão 2025")
st.markdown("Acompanhe a saúde financeira e os jogos do grupo.")
st.divider()

# --- CARREGAMENTO DE DADOS (COM TRATAMENTO DE ERRO DE CONEXÃO) ---
try:
    with st.spinner("Sincronizando dados..."):
        bets = load_bets()
        players = load_players()
        contrib = load_contributions()
except Exception as e:
    st.error("⚠️ Não foi possível conectar ao banco de dados.")
    st.warning("Se você é o administrador: Verifique se as credenciais (Secrets) estão configuradas corretamente no painel do Streamlit Cloud.")
    with st.expander("Ver detalhes técnicos do erro"):
        st.code(str(e))
    st.stop()

# Configuração de Valores
VALOR_COTA = 50.00
JOGOS_POR_COTA = 5
CUSTO_JOGOS_INDIVIDUAIS = 30.00 # 5 jogos de R$ 6,00

# Identificar ID do Fundo
id_fundo = 0
nome_fundo = "Fundo Bolão"
if not players.empty:
    for _, row in players.iterrows():
        if "fundo" in str(row["nome"]).lower():
            id_fundo = row["player_id"]
            nome_fundo = row["nome"]
            break

# Cruzamento de nomes e Pagamentos
player_map = {}
pagamentos_map = {}
jogos_por_pessoa = {}

if not contrib.empty:
    pagamentos_map = contrib[contrib["pago"]==True].groupby("player_id")["valor"].sum().to_dict()

if not players.empty:
    players["player_id"] = pd.to_numeric(players["player_id"], errors='coerce').fillna(0).astype(int)
    player_map = players.set_index("player_id")["nome"].to_dict()

# Contagem de jogos por pessoa
if not bets.empty:
    bets["player_id"] = pd.to_numeric(bets["player_id"], errors='coerce').fillna(0).astype(int)
    # Conta quantos jogos cada ID tem
    jogos_por_pessoa = bets["player_id"].value_counts().to_dict()

# --- CÁLCULO DE PARTICIPANTES (PAGOS vs PENDENTES) ---
qtd_jogadores_reais = 0
qtd_pagantes = 0
qtd_pendentes = 0

if not players.empty:
    # Filtra jogadores reais (exclui Fundo)
    df_reais = players[~players['nome'].str.contains("Fundo", case=False, na=False)]
    qtd_jogadores_reais = len(df_reais)
    
    for pid in df_reais["player_id"].unique():
        valor_pago = pagamentos_map.get(pid, 0.0)
        # Consideramos "Pagante" quem já pagou pelo menos a cota cheia
        if valor_pago >= VALOR_COTA:
            qtd_pagantes += 1
        else:
            qtd_pendentes += 1

# --- CÁLCULOS GERAIS (CAIXA) ---
total_arrecadado_geral = 0.0
if not contrib.empty:
    total_arrecadado_geral = contrib[contrib["pago"] == True]["valor"].sum()

total_gasto_geral = 0.0 # Pagos/Feitos
total_gasto_fila = 0.0  # Pendentes
total_jogos_feitos = 0
total_jogos_fila = 0

df_feitos = pd.DataFrame()
df_fila = pd.DataFrame()

if not bets.empty:
    bets["custo_total"] = pd.to_numeric(bets["custo_total"], errors='coerce').fillna(0)
    
    df_feitos = bets[bets["conferido"] == True].copy()
    df_fila = bets[bets["conferido"] == False].copy()
    
    total_gasto_geral = df_feitos["custo_total"].sum()
    total_gasto_fila = df_fila["custo_total"].sum()
    
    total_jogos_feitos = len(df_feitos)
    total_jogos_fila = len(df_fila)

saldo_geral = total_arrecadado_geral - total_gasto_geral

# --- PAINEL FINANCEIRO (FIXO NO TOPO) ---
st.subheader("💰 Caixa Geral (Prestação de Contas)")
with st.container(border=True):
    # Linha principal com 4 métricas
    c1, c2, c3, c4 = st.columns(4)
    
    # Métrica de Jogadores Atualizada com Delta
    c1.metric(
        "👥 Participantes", 
        f"{qtd_pagantes}/{qtd_jogadores_reais} Pagos", 
        help=f"Total: {qtd_jogadores_reais} | Pagos: {qtd_pagantes} | Pendentes: {qtd_pendentes}",
        delta=f"{qtd_pendentes} pendentes" if qtd_pendentes > 0 else "Todos pagaram! 🎉",
        delta_color="off" if qtd_pendentes > 0 else "normal"
    )
    
    c2.metric(
        "📥 Total Arrecadado", 
        money(total_arrecadado_geral), 
        help="Soma de todos os Pix recebidos (Cotas + Fundo)."
    )
    
    cor_saldo = "normal" if saldo_geral >= 0 else "inverse"
    c3.metric(
        "🏦 Saldo Disponível", 
        money(saldo_geral), 
        delta="Em caixa", 
        delta_color=cor_saldo
    )
    
    # Nova Métrica: Valor Pendente para Jogos na Fila
    c4.metric(
        "⚠️ A Pagar (Jogos na Fila)", 
        money(total_gasto_fila), 
        help=f"Valor necessário para registrar os {total_jogos_fila} jogos que estão na fila."
    )
    
    st.caption(f"💸 Total já gasto na lotérica (Jogos Feitos): **{money(total_gasto_geral)}** | 🎟️ Total de jogos cadastrados: **{total_jogos_feitos + total_jogos_fila}**")

st.divider()

# ==========================================
# ABAS PARA ORGANIZAÇÃO
# ==========================================
tab_jogos, tab_status, tab_fundo = st.tabs(["📋 Lista de Jogos", "📊 Status (Pagou/Jogou?)", "🏦 Fundo Extra"])

# ------------------------------------------
# ABA 1: LISTA DE JOGOS (AGRUPADA)
# ------------------------------------------
with tab_jogos:
    st.caption("Veja abaixo os jogos de cada participante.")
    
    subtab_feitos, subtab_fila = st.tabs([
        f"✅ Registrados na Caixa ({total_jogos_feitos})", 
        f"⏳ Aguardando Registro ({total_jogos_fila})"
    ])

    def render_game_list_grouped(df_jogos, cor_titulo):
        if df_jogos.empty:
            st.info("Nenhum jogo nesta lista.")
            return

        search = st.text_input("🔍 Buscar participante:", placeholder="Digite o nome...", key=f"search_{cor_titulo}").strip().lower()

        # Prepara dados
        dados_processados = []
        for _, row in df_jogos.iterrows():
            pid = pd.to_numeric(row.get("player_id", 0), errors="coerce")
            pid = int(pid) if not pd.isna(pid) else 0
            
            nome_real = player_map.get(pid, row.get("apostador", "Desconhecido"))
            if "fundo" in str(nome_real).lower():
                nome_real = "🏢 FUNDO DO BOLÃO"
            
            if search and search not in str(nome_real).lower():
                continue
                
            dados_processados.append({
                "Nome": nome_real,
                "Numeros": str(row["numeros"]),
                "Custo": float(row.get("custo_total", 0)),
                "ID": str(row['id'])
            })
        
        if not dados_processados:
            st.info("Nenhum jogo encontrado.")
            return

        df_proc = pd.DataFrame(dados_processados)
        
        # Agrupa por Nome
        for nome, grupo in df_proc.groupby("Nome"):
            grupo = grupo.sort_values("ID")
            total_investido = grupo["Custo"].sum()
            qtd_jogos = len(grupo)
            
            with st.container(border=True):
                c_head1, c_head2 = st.columns([2, 1])
                c_head1.markdown(f"### 👤 {nome}")
                c_head2.markdown(f"<div style='text-align:right; color:#888;'>{qtd_jogos} jogos • {money(total_investido)}</div>", unsafe_allow_html=True)
                st.divider()
                
                for _, jogo in grupo.iterrows():
                    lista_nums = _to_int_list(jogo["Numeros"])
                    numeros_fmt = "  ".join([f"{n:02d}" for n in lista_nums])
                    qtd_dezenas = len(lista_nums)
                    tipo_jogo = f"Bolão {qtd_dezenas}" if qtd_dezenas > 6 else "Simples"
                    
                    st.markdown(f"""
                    <div style="background-color: rgba(255, 255, 255, 0.05); padding: 8px 12px; border-radius: 6px; margin-bottom: 8px; border-left: 4px solid {cor_titulo}; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="font-family: monospace; font-size: 18px; font-weight: bold; color: {cor_titulo}; letter-spacing: 1px;">{numeros_fmt}</span><br>
                            <span style="font-size: 12px; color: #aaa;">{tipo_jogo} • {money(jogo['Custo'])}</span>
                        </div>
                        <div style="font-size: 10px; color: #555;">ID: {jogo['ID'][:6]}</div>
                    </div>
                    """, unsafe_allow_html=True)

    with subtab_feitos:
        render_game_list_grouped(df_feitos, "#2e7d32") # Verde
    with subtab_fila:
        render_game_list_grouped(df_fila, "#ff9800") # Laranja

# ------------------------------------------
# ABA 2: QUEM PAGOU? (STATUS DETALHADO)
# ------------------------------------------
with tab_status:
    st.subheader("👥 Status Financeiro e de Jogos")
    
    # Processa listas
    lista_pagou = []
    lista_devendo = []
    
    if not players.empty:
        for _, row in players.iterrows():
            pid = row["player_id"]
            nome = row["nome"]
            if pid == id_fundo or "fundo" in str(nome).lower(): continue
                
            pago = pagamentos_map.get(pid, 0.0)
            jogos_feitos = jogos_por_pessoa.get(pid, 0)
            
            # Status Jogos
            if jogos_feitos >= JOGOS_POR_COTA:
                status_jogos = f"✅ Jogou tudo ({jogos_feitos})"
            elif jogos_feitos > 0:
                status_jogos = f"⚠️ Jogando ({jogos_feitos}/{JOGOS_POR_COTA})"
            else:
                status_jogos = "❌ Não jogou"

            item = {
                "Nome": nome, 
                "Pago": pago, 
                "Jogos": jogos_feitos,
                "StatusJogos": status_jogos
            }
            
            if pago >= VALOR_COTA:
                lista_pagou.append(item)
            else:
                lista_devendo.append(item)

    # Ordenações
    lista_pagou.sort(key=lambda x: x["Nome"])
    lista_devendo.sort(key=lambda x: x["Pago"], reverse=True) # Quem pagou mais (parcial) aparece antes

    sub_pagou, sub_devendo = st.tabs([
        f"✅ Pagamento OK ({len(lista_pagou)})", 
        f"⚠️ Pendentes/Parciais ({len(lista_devendo)})"
    ])
    
    with sub_pagou:
        if not lista_pagou:
            st.info("Ninguém quitou a cota ainda.")
        else:
            cols = st.columns(3)
            for i, item in enumerate(lista_pagou):
                with cols[i % 3]:
                    with st.container(border=True):
                        st.markdown(f"**{item['Nome']}**")
                        st.success(f"💰 {money(item['Pago'])} (Pago)")
                        
                        # Mostra status dos jogos com cor apropriada
                        if item['Jogos'] >= JOGOS_POR_COTA:
                            st.caption(f"🎟️ {item['StatusJogos']}")
                        else:
                            st.markdown(f"<small style='color:orange'>🎟️ Falta jogar ({item['Jogos']}/{JOGOS_POR_COTA})</small>", unsafe_allow_html=True)

    with sub_devendo:
        if not lista_devendo:
            st.success("Todo mundo pagou! 🎉")
        else:
            cols = st.columns(3)
            for i, item in enumerate(lista_devendo):
                with cols[i % 3]:
                    with st.container(border=True):
                        st.markdown(f"**{item['Nome']}**")
                        
                        falta = VALOR_COTA - item['Pago']
                        if item['Pago'] > 0:
                            st.warning(f"💰 Parcial: {money(item['Pago'])}")
                            st.caption(f"Falta: {money(falta)}")
                        else:
                            st.error(f"💰 Pendente (R$ 0,00)")
                        
                        # Status Jogos
                        st.caption(f"🎟️ {item['StatusJogos']}")

# ------------------------------------------
# ABA 3: FUNDO EXTRA
# ------------------------------------------
with tab_fundo:
    st.subheader("🏦 O Fundo do Bolão")
    st.markdown("Valores arrecadados além da cota individual (sobras de R$ 30,00), usados para jogos coletivos.")

    # Cálculos Específicos do Fundo
    arrecadado_fundo = 0.0
    for pid, valor_pago in pagamentos_map.items():
        if pid == id_fundo: continue
        sobra = max(0.0, valor_pago - CUSTO_JOGOS_INDIVIDUAIS)
        arrecadado_fundo += sobra

    gasto_fundo_calc = 0.0
    if not bets.empty:
        is_fundo_bet = (bets["player_id"] == id_fundo) | (bets["apostador"].str.lower().str.contains("fundo"))
        gasto_fundo_calc = bets[is_fundo_bet]["custo_total"].sum()

    saldo_fundo_calc = arrecadado_fundo - gasto_fundo_calc

    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        c1.metric("📥 Total Arrecadado (Fundo)", money(arrecadado_fundo), help="Soma dos R$ 20,00 de cada participante")
        c2.metric("🚀 Jogado pelo Fundo", money(gasto_fundo_calc), help="Valor já apostado em bolões extras")
        cor_f = "normal" if saldo_fundo_calc >= 0 else "inverse"
        c3.metric("💰 Saldo Disponível", money(saldo_fundo_calc), delta="Para novos jogos", delta_color=cor_f)

st.markdown("---")
st.caption("Sistema desenvolvido por João Paulo Rodrigues. Boa sorte! 🍀")
