import streamlit as st
import pandas as pd
import sys
import os

# Garante path
try:
    from utils_mb import load_bets, load_players, check_bet_results, _to_int_list
except ImportError:
    # Fallback para execução local/nuvem
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils_mb import load_bets, load_players, check_bet_results, _to_int_list

st.set_page_config(page_title="Conferência Pública", page_icon="🤞", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# CSS MOBILE-FIRST (RESPONSIVO)
# ==========================================
st.markdown("""
<style>
    /* Remove margens excessivas no mobile */
    .block-container { padding-top: 1rem; padding-bottom: 2rem; padding-left: 1rem; padding-right: 1rem; }
    
    /* Bolinhas de Sorteio (Responsivas) */
    .lottery-ball {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 35px; height: 35px; /* Menor para caber no celular */
        border-radius: 50%;
        background: radial-gradient(circle at 30% 30%, #ffffff, #e0e0e0);
        color: #333;
        font-weight: bold;
        font-size: 14px;
        box-shadow: 1px 1px 3px rgba(0,0,0,0.2);
        margin: 2px;
        border: 1px solid #ccc;
    }
    
    /* Bolinha Selecionada / Acerto */
    .ball-hit {
        background: radial-gradient(circle at 30% 30%, #4CAF50, #2E7D32);
        color: white; border: 1px solid #1B5E20; transform: scale(1.05);
    }
    
    /* Bolinha Erro */
    .ball-miss { background: #f0f0f0; color: #ccc; border: 1px solid #ddd; opacity: 0.5; }

    /* CARD DE JOGADOR (MOBILE FRIENDLY) */
    .player-card {
        background-color: #262730;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 8px;
        border-left: 4px solid #555;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    
    /* Cores de Destaque */
    .card-sena { border-left-color: #FFD700; background-color: rgba(255, 215, 0, 0.15); }
    .card-quina { border-left-color: #4CAF50; background-color: rgba(76, 175, 80, 0.15); }
    .card-quadra { border-left-color: #2196F3; background-color: rgba(33, 150, 243, 0.15); }

    /* Layout Flex para Nome e Pontos */
    .card-header {
        display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;
    }
    .card-name { font-size: 16px; font-weight: bold; color: #fff; }
    .card-points { font-size: 18px; font-weight: bold; }
    .card-dezenas { display: flex; flex-wrap: wrap; gap: 2px; }

    /* Painel de Sorteio */
    .draw-panel {
        background: #1e1e1e; padding: 15px; border-radius: 12px; text-align: center; margin-bottom: 15px; border: 1px solid #333;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# LÓGICA
# ==========================================
if "public_draw" not in st.session_state:
    st.session_state["public_draw"] = []

def toggle_num(n):
    picked = st.session_state["public_draw"]
    if n in picked:
        picked.remove(n)
    else:
        if len(picked) < 6:
            picked.append(n)
    st.session_state["public_draw"] = sorted(picked)

# ==========================================
# UI
# ==========================================
st.markdown("<h2 style='text-align: center; margin-bottom: 5px;'>🤞 Conferência da Sorte</h2>", unsafe_allow_html=True)

# --- SORTEIO ---
picked = st.session_state["public_draw"]
with st.container():
    st.markdown('<div class="draw-panel">', unsafe_allow_html=True)
    if picked:
        html = "".join([f"<div class='lottery-ball ball-hit' style='width:42px; height:42px; font-size:18px;'>{n:02d}</div>" for n in picked])
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.caption("Toque nos números abaixo para simular")
    st.markdown('</div>', unsafe_allow_html=True)

# --- TECLADO NUMÉRICO (EXPANDER) ---
aberto = len(picked) < 6
with st.expander("🔢 Selecionar Números", expanded=aberto):
    # Grid responsivo (6 colunas no mobile fica apertado, vamos de 5 ou 6)
    cols = st.columns(6)
    for i in range(1, 61):
        col_idx = (i - 1) % 6
        is_sel = i in picked
        # Botão nativo do Streamlit (funciona bem no touch)
        if cols[col_idx].button(f"{i:02d}", key=f"btn_{i}", type="primary" if is_sel else "secondary"):
            toggle_num(i)
            st.rerun()
    
    if st.button("Limpar Tudo", use_container_width=True):
        st.session_state["public_draw"] = []
        st.rerun()

# ==========================================
# RESULTADOS
# ==========================================
st.divider()

if len(picked) == 6:
    # Carrega dados (com cache interno do utils)
    try:
        bets = load_bets()
        players = load_players()
    except Exception:
        st.error("Erro ao conectar no banco.")
        st.stop()

    if bets.empty:
        st.info("Nenhuma aposta cadastrada.")
    else:
        # Prepara mapa de nomes
        player_map = {}
        if not players.empty:
            players["player_id"] = pd.to_numeric(players["player_id"], errors='coerce').fillna(0).astype(int)
            player_map = players.set_index("player_id")["nome"].to_dict()

        draw_set = set(picked)
        resultados = []

        for _, row in bets.iterrows():
            str_nums = str(row["numeros"]).replace("[","").replace("]","").replace(","," ")
            lista_aposta = _to_int_list(str_nums)
            stats = check_bet_results(lista_aposta, draw_set)
            acertos = stats['best_hits']
            
            # Nome
            pid = int(pd.to_numeric(row.get("player_id", 0), errors="coerce") or 0)
            nome = player_map.get(pid, row.get("apostador", "Desconhecido"))
            if "fundo" in str(nome).lower(): nome = "🏢 FUNDO BOLÃO"

            # HTML Bolinhas
            html_balls = ""
            for n in lista_aposta:
                css = "ball-hit" if n in draw_set else "ball-miss"
                html_balls += f"<div class='lottery-ball {css}'>{n:02d}</div>"

            # Estilo Card
            css_card = ""
            cor_pts = "#ccc"
            if acertos == 6: css_card="card-sena"; cor_pts="#FFD700"
            elif acertos == 5: css_card="card-quina"; cor_pts="#4CAF50"
            elif acertos == 4: css_card="card-quadra"; cor_pts="#2196F3"

            resultados.append({
                "nome": nome, "html": html_balls, "acertos": acertos,
                "css": css_card, "cor_pts": cor_pts, "qtd": len(lista_aposta)
            })

        # Ordena: Acertos > Qtd Dezenas (Menos dezenas com mais acertos = mais sorte)
        resultados.sort(key=lambda x: (x['acertos'], -x['qtd']), reverse=True)

        # PLACAR (MÉTRICAS)
        senas = len([r for r in resultados if r['acertos'] == 6])
        quinas = len([r for r in resultados if r['acertos'] == 5])
        quadras = len([r for r in resultados if r['acertos'] == 4])

        if senas > 0: st.balloons(); st.success(f"🎉 {senas} SENA(S)!")
        
        # Placar Compacto
        c1, c2, c3 = st.columns(3)
        c1.metric("Sena (6)", senas)
        c2.metric("Quina (5)", quinas)
        c3.metric("Quadra (4)", quadras)
        
        st.write("")

        # LISTA DE CARDS (MOBILE OPTIMIZED)
        for r in resultados:
            st.markdown(f"""
            <div class="player-card {r['css']}">
                <div class="card-header">
                    <div class="card-name">{r['nome']} <small style='color:#aaa; font-weight:normal;'>({r['qtd']} dz)</small></div>
                    <div class="card-points" style="color: {r['cor_pts']};">{r['acertos']} pts</div>
                </div>
                <div class="card-dezenas">
                    {r['html']}
                </div>
            </div>
            """, unsafe_allow_html=True)

else:
    st.info("Aguardando sorteio...")
