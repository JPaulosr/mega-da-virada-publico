import streamlit as st
import pandas as pd
import altair as alt
import sys, os
import itertools

# Garante path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from utils_mb import load_bets, _to_int_list

st.set_page_config(page_title="Estatísticas do Grupo", page_icon="📊", layout="wide")
st.title("📊 Estatísticas e Curiosidades")

bets = load_bets()

if bets.empty:
    st.info("Cadastre apostas para ver as estatísticas.")
    st.stop()

# --- PROCESSAMENTO DOS NÚMEROS ---
todas_dezenas = []
bets['lista_numeros'] = bets['numeros'].apply(lambda x: _to_int_list(str(x)))

for lista in bets['lista_numeros']:
    todas_dezenas.extend(lista)

# Conta frequência de cada número (1 a 60)
freq = pd.Series(todas_dezenas).value_counts().sort_index()
df_freq = pd.DataFrame({"Dezena": range(1, 61)})
df_freq["Vezes"] = df_freq["Dezena"].map(freq).fillna(0).astype(int)

# --- 1. NÚMEROS MAIS E MENOS JOGADOS (6 DEZENAS) ---
c1, c2, c3 = st.columns(3)

# Pega os 6 mais frequentes e ordena numericamente para formar jogo
mais_jogados_raw = df_freq.sort_values("Vezes", ascending=False).head(6)["Dezena"].tolist()
mais_jogados = sorted(mais_jogados_raw)

# Pega os 6 menos frequentes (mas que tenham > 0 votos) e ordena
menos_jogados_raw = df_freq[df_freq["Vezes"] > 0].sort_values("Vezes", ascending=True).head(6)["Dezena"].tolist()
menos_jogados = sorted(menos_jogados_raw)

esquecidos = df_freq[df_freq["Vezes"] == 0]["Dezena"].tolist()

c1.metric("🔥 Jogo Quente (Mais Jogados)", str(mais_jogados).replace("[","").replace("]",""))
c2.metric("❄️ Jogo Frio (Menos Jogados)", str(menos_jogados).replace("[","").replace("]",""))
c3.metric("⚠️ Esquecidos (Ninguém jogou)", len(esquecidos), help=str(esquecidos))

if esquecidos:
    with st.expander("Ver números esquecidos"):
        st.write(f"Ninguém jogou nestes: {str(esquecidos)}")
else:
    st.success("Parabéns! O grupo cobriu todos os 60 números da Mega!")

st.divider()

# --- 2. RADAR DE COINCIDÊNCIAS (ATUALIZADO) ---
st.subheader("👯 Radar de Coincidências")
st.caption("Verifica jogos idênticos e semelhanças (Quinas, Quadras, Ternos e Duques em comum).")

# Prepara dados para comparação
bets['tuple_numeros'] = bets['lista_numeros'].apply(lambda x: tuple(sorted(x)))

# A. JOGOS IDÊNTICOS (6 iguais)
duplicados = bets[bets.duplicated('tuple_numeros', keep=False)]

if not duplicados.empty:
    st.error(f"🚨 ALERTA: Encontramos {len(duplicados)} apostas com as mesmas 6 dezenas!")
    grupos_dup = duplicados.groupby('tuple_numeros')['apostador'].apply(list).reset_index()
    for _, row in grupos_dup.iterrows():
        nums_fmt = " - ".join([f"{n:02d}" for n in row['tuple_numeros']])
        nomes_fmt = ", ".join([f"**{n}**" for n in row['apostador']])
        st.warning(f"🔢 {nums_fmt}\n\n👥 Jogadores: {nomes_fmt}")
else:
    st.success("✅ Nenhum jogo idêntico (6 dezenas). Todos são únicos.")

st.write("")

# B. JOGOS PARECIDOS (5, 4, 3, 2)
st.markdown("### 🔍 Detetive de Semelhanças")

# Listas para armazenar pares
pares_quina = []  # 5
pares_quadra = [] # 4
pares_terno = []  # 3
pares_duque = []  # 2

# Lista de jogos para comparação
lista_jogos = []
for idx, row in bets.iterrows():
    lista_jogos.append({
        "id": row.get("id", idx),
        "nome": row["apostador"],
        "nums": set(row["lista_numeros"])
    })

# Comparação combinatória
for a, b in itertools.combinations(lista_jogos, 2):
    iguais = a["nums"].intersection(b["nums"])
    qtd = len(iguais)
    
    # Se forem 6 iguais, já foi mostrado no alerta de duplicados acima
    if qtd == 6 and len(a["nums"]) == 6 and len(b["nums"]) == 6:
        continue

    item = {
        "j1": a["nome"],
        "j2": b["nome"],
        "comuns": sorted(list(iguais))
    }

    if qtd == 5:
        pares_quina.append(item)
    elif qtd == 4:
        pares_quadra.append(item)
    elif qtd == 3:
        pares_terno.append(item)
    elif qtd == 2:
        pares_duque.append(item)

# Exibição em Abas
tab5, tab4, tab3, tab2 = st.tabs([
    f"5️⃣ Quinas ({len(pares_quina)})", 
    f"4️⃣ Quadras ({len(pares_quadra)})", 
    f"3️⃣ Ternos ({len(pares_terno)})",
    f"2️⃣ Duques ({len(pares_duque)})"
])

def listar_pares(lista, emoji_b):
    if not lista:
        st.caption("Nenhum par encontrado nesta categoria.")
        return
    
    # Limita para não travar se tiver milhares de duques
    limit = 50
    if len(lista) > limit:
        st.caption(f"Mostrando os primeiros {limit} de {len(lista)} pares encontrados.")
        lista = lista[:limit]
        
    for p in lista:
        nums_str = str(p['comuns']).replace("[","").replace("]","")
        st.markdown(f"{emoji_b} **{p['j1']}** vs **{p['j2']}**: `{nums_str}`")

with tab5:
    st.caption("Jogos que bateram na trave de serem iguais (5 números em comum).")
    listar_pares(pares_quina, "🔥")

with tab4:
    st.caption("Jogos com 4 números em comum.")
    listar_pares(pares_quadra, "🔶")

with tab3:
    st.caption("Jogos com 3 números em comum.")
    with st.expander("Ver lista de Ternos"):
        listar_pares(pares_terno, "🔹")

with tab2:
    st.caption("Jogos com 2 números em comum (apenas curiosidade).")
    with st.expander("Ver lista de Duques"):
        listar_pares(pares_duque, "⚪")

st.divider()

# --- 3. MAPA DE CALOR (HEATMAP) ---
st.subheader("🗺️ Mapa de Calor do Bolão")

# Cria grade 6x10 para o visual
rows = []
for r in range(6):
    cols_data = []
    for c in range(10):
        num = r * 10 + (c + 1)
        qtd = df_freq.loc[df_freq["Dezena"]==num, "Vezes"].values[0]
        
        # Define cor baseada na quantidade
        max_v = df_freq['Vezes'].max()
        if max_v == 0: max_v = 1
        
        if qtd == 0:
            bg_color = "#1e1e1e"
            txt_color = "#555"
            border = "1px dashed #444"
        else:
            # Gradiente de vermelho/laranja
            alpha = 0.2 + (qtd / max_v * 0.8) # Mínimo 0.2 de opacidade se tiver 1 jogo
            bg_color = f"rgba(255, 75, 75, {alpha})" 
            txt_color = "white"
            border = "1px solid #ff4b4b"

        cols_data.append(f"""
            <div style="
                background-color: {bg_color};
                color: {txt_color};
                border: {border};
                width: 100%;
                height: 50px;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                border-radius: 8px;
                margin: 2px;
            ">
                <span style="font-size: 18px; font-weight: bold;">{num:02d}</span>
                <span style="font-size: 10px;">{qtd}x</span>
            </div>
        """)
    rows.append(cols_data)

# Renderiza HTML
for row_html in rows:
    cols = st.columns(10)
    for i, col in enumerate(cols):
        col.markdown(row_html[i], unsafe_allow_html=True)

st.divider()

# --- 4. GRÁFICO DE BARRAS ---
st.subheader("📊 Frequência Detalhada")
chart = alt.Chart(df_freq).mark_bar().encode(
    x=alt.X("Dezena:O", title="Dezena"),
    y=alt.Y("Vezes:Q", title="Qtd Apostas"),
    color=alt.condition(
        alt.datum.Vezes == 0,
        alt.value("gray"),  # A cor dos zerados
        alt.value("#ff4b4b")   # A cor dos jogados
    ),
    tooltip=["Dezena", "Vezes"]
).properties(height=300)

st.altair_chart(chart, use_container_width=True)
