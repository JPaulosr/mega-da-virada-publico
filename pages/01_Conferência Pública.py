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
# CSS MOBILE-FIRST (VISUAL TV)
# ==========================================
st.markdown("""
<style>
    /* Ajustes gerais para Mobile */
    .block-container { 
        padding-top: 1rem; 
        padding-bottom: 3rem; 
        padding-left: 0.5rem; 
        padding-right: 0.5rem; 
    }
    
    /* Bolinhas de Sorteio (Estilo TV 3D) */
    .lottery-ball {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 40px; height: 40px;
        border-radius: 50%;
        background: radial-gradient(circle at 30% 30%, #ffffff, #e0e0e0);
        color: #333;
        font-weight: bold;
        font-size: 16px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
        margin: 3px;
        border: 1px solid #ccc;
    }
    
    /* Bolinha Acerto (Verde Brilhante) */
    .ball-hit {
        background: radial-gradient(circle at 30% 30%, #4CAF50, #1B5E20);
        color: white; 
        border: 1px solid #004D40; 
        text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
        transform: scale(1.1);
        z-index: 2;
    }
    
    /* Bolinha Erro (Opaca) */
    .ball-miss { 
        background: #333; 
        color: #777; 
        border: 1px solid #444; 
        opacity: 0.6;
        box-shadow: none;
    }

    /* CARD DE JOGADOR (Material Design) */
    .player-card {
        background-color: #1e1e1e;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 12px;
        border: 1px solid #333;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        position: relative;
        overflow: hidden;
    }
    
    /* Faixa lateral colorida baseada no prêmio */
    .card-sena { border-left: 6px solid #FFD700; background: linear-gradient(90deg, rgba(255, 215, 0, 0.1), transparent); }
    .card-quina { border-left: 6px solid #4CAF50; background: linear-gradient(90deg, rgba(76, 175, 80, 0.1), transparent); }
    .card-quadra { border-left: 6px solid #2196F3; background: linear-gradient(90deg, rgba(33, 150, 243, 0.1), transparent); }
    .card-normal { border-left: 6px solid #555; }

    /* Layout Interno do Card */
    .card-header {
        display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;
    }
    .card-name { font-size: 16px; font-weight: bold; color: #fff; line-height: 1.2; }
    .card-sub { font-size: 12px; color: #aaa; margin-top: 2px; }
    .card-points { 
        font-size: 22px; font-weight: 900; 
        background: #000; padding: 5px 10px; border-radius: 8px;
        min-width: 40px; text-align: center;
    }
    .card-dezenas { display: flex; flex-wrap: wrap; gap: 2px; }

    /* Painel de Sorteio (Topo) */
    .draw-panel {
        background: #111; 
        padding: 20px; 
        border-radius: 16px; 
        text-align: center; 
        margin-bottom: 20px; 
        border: 1px solid #333;
        box-shadow: 0 0 20px rgba(0,0,0,0.5) inset;
    }
    .draw-title { font-size: 12px; text-transform: uppercase; letter-spacing: 2px; color: #888; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# LÓGICA
# ==========================================
if "public_draw" not in st.session_state:
    st.session_state["public_draw"] = []

# ==========================================
# UI - TOPO (SORTEIO)
# ==========================================
st.markdown("<h2 style='text-align: center; margin-bottom: 5px;'>🤞 Conferência da Sorte</h2>", unsafe_allow_html=True)

picked = st.session_state["public_draw"]

# --- PAINEL DE RESULTADO ---
with st.container():
    st.markdown('<div class="draw-panel">', unsafe_allow_html=True)
    st.markdown('<div class="draw-title">Dezenas Sorteada</div>', unsafe_allow_html=True)
    if picked:
        # Mostra as bolinhas bonitas
        html = "".join([f"<div class='lottery-ball ball-hit' style='width:45px; height:45px; font-size:18px;'>{n:02d}</div>" for n in sorted(picked)])
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.caption("Aguardando sorteio...")
    st.markdown('</div>', unsafe_allow_html=True)

# --- INPUT (OTIMIZADO PARA MOBILE) ---
# Usamos Multiselect porque é nativo e não quebra no celular
col_sel, col_btn = st.columns([4, 1])
with col_sel:
    novos_numeros = st.multiselect(
        "Simular Resultado (Escolha 6)", 
        options=list(range(1, 61)),
        default=picked,
        format_func=lambda x: f"{x:02d}",
        placeholder="Digite ou selecione os números...",
        max_selections=6
    )

# Atualiza estado
if novos_numeros != st.session_state["public_draw"]:
    st.session_state["public_draw"] = sorted(novos_numeros)
    st.rerun()

if st.button("Limpar", type="secondary", use_container_width=True):
    st.session_state["public_draw"] = []
    st.rerun()

# ==========================================
# RESULTADOS (CARDS)
# ==========================================
st.divider()

if len(picked) == 6:
    # Carrega dados
    try:
        bets = load_bets()
        players = load_players()
    except Exception:
        st.error("Erro ao conectar no banco.")
        st.stop()

    if bets.empty:
        st.info("Nenhuma aposta cadastrada.")
    else:
        # Mapa de nomes
        player_map = {}
        if not players.empty:
            players["player_id"] = pd.to_numeric(players["player_id"], errors='coerce').fillna(0).astype(int)
            player_map = players.set_index("player_id")["nome"].to_dict()

        draw_set = set(picked)
        resultados = []

        for _, row in bets.iterrows():
            str_nums = str(row["numeros"]).replace("[","").replace("]","").replace(","," ")
            lista_aposta = _to_int_list(str_nums)
            
            # Processa acertos
            stats = check_bet_results(lista_aposta, draw_set)
            acertos = stats['best_hits']
            
            # Nome
            pid = int(pd.to_numeric(row.get("player_id", 0), errors="coerce") or 0)
            nome = player_map.get(pid, row.get("apostador", "Desconhecido"))
            if "fundo" in str(nome).lower(): nome = "🏢 FUNDO BOLÃO"

            # HTML Bolinhas (Miniaturas para o card)
            html_balls = ""
            for n in lista_aposta:
                css = "ball-hit" if n in draw_set else "ball-miss"
                html_balls += f"<div class='lottery-ball {css}' style='width:30px; height:30px; font-size:12px;'>{n:02d}</div>"

            # Estilo do Card
            css_class = "card-normal"
            cor_pts = "#555"
            label_premio = ""
            
            if acertos == 6: 
                css_class="card-sena"; cor_pts="#FFD700"; label_premio="SENA 🏆"
            elif acertos == 5: 
                css_class="card-quina"; cor_pts="#4CAF50"; label_premio="QUINA 🥈"
            elif acertos == 4: 
                css_class="card-quadra"; cor_pts="#2196F3"; label_premio="QUADRA 🥉"

            resultados.append({
                "nome": nome, "html": html_balls, "acertos": acertos,
                "css": css_class, "cor_pts": cor_pts, "label": label_premio,
                "qtd": len(lista_aposta)
            })

        # Ordena: Acertos > Qtd Dezenas
        resultados.sort(key=lambda x: (x['acertos'], -x['qtd']), reverse=True)

        # --- PLACAR ---
        senas = len([r for r in resultados if r['acertos'] == 6])
        quinas = len([r for r in resultados if r['acertos'] == 5])
        quadras = len([r for r in resultados if r['acertos'] == 4])

        if senas > 0: 
            st.balloons()
            st.success(f"🎉 TEMOS {senas} SENA(S)!")
        
        # Dashboard Compacto
        c1, c2, c3 = st.columns(3)
        c1.metric("Sena (6)", senas)
        c2.metric("Quina (5)", quinas)
        c3.metric("Quadra (4)", quadras)
        
        st.write("")

        # --- LISTA DE CARDS ---
        st.caption(f"Conferindo {len(resultados)} jogos...")
        
        for r in resultados:
            premio_html = f"<div style='color: {r['cor_pts']}; font-size: 11px; font-weight: bold; margin-top: 4px;'>{r['label']}</div>" if r['label'] else ""
            
            st.markdown(f"""
            <div class="player-card {r['css']}">
                <div class="card-header">
                    <div>
                        <div class="card-name">{r['nome']}</div>
                        <div class="card-sub">{r['qtd']} dezenas</div>
                    </div>
                    <div style="text-align: center;">
                        <div class="card-points" style="color: {r['cor_pts']}; border: 1px solid {r['cor_pts']};">
                            {r['acertos']}
                        </div>
                        {premio_html}
                    </div>
                </div>
                <div class="card-dezenas">
                    {r['html']}
                </div>
            </div>
            """, unsafe_allow_html=True)

else:
    st.info("👆 Selecione as 6 dezenas acima para conferir.")
