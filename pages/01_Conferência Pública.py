import streamlit as st
import pandas as pd
import sys
import os

# Garante path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from utils_mb import load_bets, load_players, check_bet_results, _to_int_list

st.set_page_config(page_title="Conferência Pública", page_icon="🤞", layout="wide")

# ==========================================
# ESTILO CSS PERSONALIZADO (VISUAL TV)
# ==========================================
st.markdown("""
<style>
    /* Fundo geral e fontes */
    .block-container { padding-top: 2rem; padding-bottom: 5rem; }
    
    /* Bolinhas de Sorteio (Seleção e Resultado) */
    .lottery-ball {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: radial-gradient(circle at 30% 30%, #ffffff, #e0e0e0);
        color: #333;
        font-weight: bold;
        font-size: 16px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
        margin: 2px;
        border: 1px solid #ccc;
    }
    
    /* Bolinha Selecionada / Acerto */
    .ball-hit {
        background: radial-gradient(circle at 30% 30%, #4CAF50, #2E7D32);
        color: white;
        border: 1px solid #1B5E20;
        box-shadow: 0 0 8px rgba(76, 175, 80, 0.6);
        transform: scale(1.1);
    }
    
    /* Bolinha Erro (nos resultados) */
    .ball-miss {
        background: #f0f0f0;
        color: #bbb;
        border: 1px solid #ddd;
        opacity: 0.6;
    }

    /* Botões de Seleção (Grid) */
    div.stButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: bold;
        border: 1px solid #444;
        transition: all 0.2s;
    }
    div.stButton > button:hover {
        border-color: #4CAF50;
        color: #4CAF50;
        transform: translateY(-2px);
    }

    /* Card de Jogador */
    .player-card {
        background-color: #262730;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
        border-left: 5px solid #555;
        transition: transform 0.2s;
    }
    .player-card:hover {
        transform: scale(1.01);
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }
    .card-sena { border-left-color: #FFD700; background-color: rgba(255, 215, 0, 0.1); }
    .card-quina { border-left-color: #4CAF50; background-color: rgba(76, 175, 80, 0.1); }
    .card-quadra { border-left-color: #2196F3; background-color: rgba(33, 150, 243, 0.1); }

    /* Destaque do Sorteio */
    .draw-display {
        background: linear-gradient(135deg, #1e1e1e, #2d2d2d);
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 20px;
        border: 1px solid #444;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# LÓGICA DE ESTADO
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
# UI - TOPO
# ==========================================
st.markdown("<h1 style='text-align: center;'>🤞 Conferência da Sorte</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #888;'>Simule o resultado ou confira o sorteio oficial em tempo real.</p>", unsafe_allow_html=True)

# --- PAINEL DE DESTAQUE (SORTEIO) ---
picked = st.session_state["public_draw"]

with st.container():
    st.markdown('<div class="draw-display">', unsafe_allow_html=True)
    if picked:
        html_balls = ""
        for n in picked:
            html_balls += f"<div class='lottery-ball ball-hit' style='width:50px; height:50px; font-size:20px; margin: 0 5px;'>{n:02d}</div>"
        st.markdown(html_balls, unsafe_allow_html=True)
    else:
        st.markdown("<h3 style='color:#555;'>Aguardando dezenas...</h3>", unsafe_allow_html=True)
    
    # Texto de status
    faltam = 6 - len(picked)
    if faltam > 0:
        st.caption(f"Selecione mais {faltam} número(s) abaixo")
    else:
        st.caption("✨ Sorteio Completo! Confira os ganhadores abaixo.")
        if st.button("🗑️ Limpar Sorteio"):
            st.session_state["public_draw"] = []
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- SELETOR DE NÚMEROS (EXPANDER) ---
# Só abre se não tiver selecionado os 6 ainda
start_open = len(picked) < 6
with st.expander("🔢 Selecionar Dezenas (Clique aqui)", expanded=start_open):
    for r in range(6):
        cols = st.columns(10)
        for c in range(10):
            n = r * 10 + (c + 1)
            is_sel = n in picked
            # Botão simples, o estilo é feito via CSS e tipo primary
            if cols[c].button(f"{n:02d}", key=f"btn_{n}", type="primary" if is_sel else "secondary"):
                toggle_num(n)
                st.rerun()

# ==========================================
# RESULTADOS
# ==========================================
st.divider()

if len(picked) == 6:
    bets = load_bets()
    players = load_players()
    
    # Mapa de nomes
    player_map = {}
    if not players.empty:
        players["player_id"] = pd.to_numeric(players["player_id"], errors='coerce').fillna(0).astype(int)
        player_map = players.set_index("player_id")["nome"].to_dict()

    if bets.empty:
        st.warning("📭 Nenhuma aposta cadastrada no sistema.")
    else:
        # Processamento
        resultados = []
        draw_set = set(picked)
        
        for _, row in bets.iterrows():
            str_nums = str(row["numeros"]).replace("[","").replace("]","").replace(","," ")
            lista_aposta = _to_int_list(str_nums)
            
            stats = check_bet_results(lista_aposta, draw_set)
            acertos = stats['best_hits']
            
            # Nome
            pid = int(pd.to_numeric(row.get("player_id", 0), errors="coerce") or 0)
            nome = player_map.get(pid, row.get("apostador", "Desconhecido"))
            if "fundo" in str(nome).lower(): nome = "🏢 FUNDO DO BOLÃO"

            # Gera HTML das bolinhas do jogo
            html_nums = ""
            for n in lista_aposta:
                classe = "ball-hit" if n in draw_set else "ball-miss"
                html_nums += f"<div class='lottery-ball {classe}'>{n:02d}</div>"

            # Classificação visual
            css_class = ""
            label_premio = ""
            if acertos == 6:
                css_class = "card-sena"
                label_premio = "🏆 SENA!"
            elif acertos == 5:
                css_class = "card-quina"
                label_premio = "🥈 QUINA"
            elif acertos == 4:
                css_class = "card-quadra"
                label_premio = "🥉 QUADRA"

            resultados.append({
                "Nome": nome,
                "Dezenas_HTML": html_nums,
                "Acertos": acertos,
                "CSS": css_class,
                "Label": label_premio,
                "Qtd_Dezenas": len(lista_aposta)
            })
            
        # Ordenação: Acertos (decrescente) -> Qtd Dezenas (crescente - mais difícil)
        resultados.sort(key=lambda x: (x['Acertos'], -x['Qtd_Dezenas']), reverse=True)
        
        # --- PLACAR GERAL (METRICS) ---
        st.subheader("📊 Placar do Grupo")
        
        # Confetes se tiver Sena!
        senas = len([r for r in resultados if r['Acertos'] == 6])
        quinas = len([r for r in resultados if r['Acertos'] == 5])
        quadras = len([r for r in resultados if r['Acertos'] == 4])
        
        if senas > 0:
            st.balloons()
            st.success(f"🎉 TEMOS {senas} SENA(S)! ESTAMOS RICOS! 🎉")
        elif quinas > 0:
            st.warning(f"🤩 TEMOS {quinas} QUINA(S)! Passou perto!")
        elif quadras > 0:
            st.info(f"🙂 Temos {quadras} Quadra(s). Já paga o churrasco!")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🏆 Sena (6)", senas)
        c2.metric("🥈 Quina (5)", quinas)
        c3.metric("🥉 Quadra (4)", quadras)
        c4.metric("🍀 Melhor Jogo", f"{max(r['Acertos'] for r in resultados)} acertos")
        
        st.write("")
        st.write("---")
        
        # --- LISTAGEM DETALHADA (CARDS) ---
        st.subheader("📋 Detalhe dos Jogos")
        
        for r in resultados:
            # Só mostra destaque se tiver >= 4 acertos, ou mostra todos sem destaque
            # Vamos mostrar todos, mas os vencedores ficam coloridos pelo CSS
            
            with st.container():
                st.markdown(f"""
                <div class="player-card {r['CSS']}">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                        <div>
                            <span style="font-size: 18px; font-weight: bold;">{r['Nome']}</span>
                            <span style="font-size: 12px; color: #888; margin-left: 10px;">({r['Qtd_Dezenas']} dezenas)</span>
                        </div>
                        <div style="text-align: right;">
                            <span style="font-size: 24px; font-weight: bold; color: { '#FFD700' if r['Acertos']==6 else '#eee' };">
                                {r['Acertos']} pts
                            </span>
                            <br>
                            <span style="font-size: 12px; font-weight: bold; color: #4CAF50;">{r['Label']}</span>
                        </div>
                    </div>
                    <div style="display: flex; flex-wrap: wrap;">
                        {r['Dezenas_HTML']}
                    </div>
                </div>
                """, unsafe_allow_html=True)

else:
    # Mensagem de espera bonita
    st.markdown("""
    <div style="text-align: center; padding: 50px; color: #666;">
        <h2>🎰 O Sorteio ainda não começou</h2>
        <p>Selecione as dezenas acima para simular resultados ou aguarde o sorteio oficial.</p>
    </div>
    """, unsafe_allow_html=True)
