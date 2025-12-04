import pandas as pd
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import uuid
import ast
from itertools import combinations

# --- CONFIGURAÇÃO ---
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
SHEET_NAME = "DB_Bolao_Mega" 
PRICE_PER_GAME = 6.00

@st.cache_resource
def get_db_connection():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME)
        return sheet
    except Exception as e:
        st.error(f"Erro Conexão: {e}")
        return None

# --- AUXILIARES ---
def money(val):
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def _to_int_list(data):
    """
    Converte dados variados (string, lista, set, tupla) em lista de inteiros.
    Remove caracteres indesejados como chaves {}, colchetes [] e aspas.
    """
    # 1. Se já for lista, set ou tupla, tenta converter direto
    if isinstance(data, (list, tuple, set)):
        try:
            return sorted([int(x) for x in data if str(x).strip().isdigit()])
        except:
            pass # Se falhar, tenta converter via string abaixo

    # 2. Tratamento de string (Remove {}, [], '', "")
    s = str(data).replace("[", "").replace("]", "").replace("{", "").replace("}", "").replace("'", "").replace('"', "").replace(",", " ")
    try:
        return sorted([int(x) for x in s.split() if x.strip().isdigit()])
    except:
        return []

# --- LEITURA ---
@st.cache_data(ttl=60)
def load_data(tab_name):
    sh = get_db_connection()
    if sh:
        try:
            return pd.DataFrame(sh.worksheet(tab_name).get_all_records())
        except: pass
    return pd.DataFrame()

def load_players():
    df = load_data("jogadores")
    if not df.empty:
        df.columns = df.columns.str.strip().str.lower()
    
    # Garante colunas mínimas
    req = ["player_id", "nome", "telefone"]
    for c in req:
        if c not in df.columns: df[c] = ""
            
    if "player_id" in df.columns:
        df["player_id"] = pd.to_numeric(df["player_id"], errors='coerce').fillna(0).astype(int)
    
    return df[req]

def load_bets():
    df = load_data("apostas")
    req = ["id", "player_id", "apostador", "numeros", "custo_total", "conferido", "ts", "descricao"]
    if df.empty: df = pd.DataFrame(columns=req)
    for c in req:
        if c not in df.columns: df[c] = ""
    
    if "conferido" in df.columns:
        df["conferido"] = df["conferido"].astype(str).str.upper().isin(["TRUE", "VERDADEIRO", "1", "SIM"])
    
    # Recalcula qtd_numeros real
    if "numeros" in df.columns:
        df["qtd_numeros"] = df["numeros"].apply(lambda x: len(_to_int_list(x)))
    
    df["n_jogos"] = 1
    return df

def load_contributions():
    df = load_data("contribuicoes")
    if df.empty: return pd.DataFrame(columns=["id", "player_id", "valor", "pago", "ts", "nome", "obs"])
    
    if "pago" in df.columns:
        df["pago"] = df["pago"].astype(str).str.upper().isin(["TRUE", "VERDADEIRO", "1", "SIM"])
    if "data" in df.columns: df = df.rename(columns={"data": "ts"})
    if "id" in df.columns and "contrib_id" not in df.columns: df["contrib_id"] = df["id"]
        
    players = load_players()
    if not players.empty and "player_id" in df.columns:
        df["player_id"] = pd.to_numeric(df["player_id"], errors='coerce').fillna(0).astype(int)
        df = df.merge(players[["player_id", "nome"]], on="player_id", how="left")
        df["nome"] = df["nome"].fillna("Desconhecido")
    elif "nome" not in df.columns:
        df["nome"] = "Desconhecido"
        
    return df

# --- SALVAMENTO BLINDADO (FIX JSON) ---
def save_to_sheet(tab_name, df):
    if df is None or df.empty:
        if tab_name == "jogadores": return # Proteção contra zerar
    
    sh = get_db_connection()
    if sh:
        ws = sh.worksheet(tab_name)
        df_save = df.copy()
        
        # Remove colunas extras
        aux_cols = ["qtd_numeros", "n_jogos", "nome", "contrib_id"]
        if tab_name != "jogadores":
            df_save = df_save.drop(columns=[c for c in aux_cols if c in df_save.columns])
        else:
            # Em jogadores, mantemos 'nome', removemos outros
            df_save = df_save.drop(columns=[c for c in ["qtd_numeros", "n_jogos", "contrib_id"] if c in df_save.columns])

        # Converte bool para texto
        for c in ["conferido", "pago"]:
            if c in df_save.columns: df_save[c] = df_save[c].astype(str).str.upper()
            
        # --- CORREÇÃO DO ERRO JSON ---
        df_save = df_save.fillna("") 
        # -----------------------------
            
        ws.clear()
        ws.update([df_save.columns.values.tolist()] + df_save.values.tolist())
        st.cache_data.clear()

def save_players(df): save_to_sheet("jogadores", df)
def save_bets(df): save_to_sheet("apostas", df)
def save_contributions(df): save_to_sheet("contribuicoes", df)

# --- NEGÓCIO ---

def add_player(nome, telefone=""):
    df = load_players()
    new_id = 1
    if not df.empty: new_id = df["player_id"].max() + 1
    new_row = {"player_id": new_id, "nome": nome, "telefone": telefone}
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_players(df)
    return True

def upsert_player(nome):
    """
    Busca um jogador pelo nome (case insensitive).
    Se existir, retorna o player_id.
    Se não existir, cria um novo e retorna o novo player_id.
    """
    df = load_players()
    nome_clean = str(nome).strip()
    
    # 1. Tenta achar existente
    if not df.empty:
        # Filtra case insensitive
        match = df[df["nome"].astype(str).str.lower() == nome_clean.lower()]
        if not match.empty:
            return int(match.iloc[0]["player_id"])
            
    # 2. Se não existe, cria
    new_id = 1
    if not df.empty:
        # Garante que é numérico
        max_id = pd.to_numeric(df["player_id"], errors='coerce').max()
        if pd.notna(max_id):
            new_id = int(max_id) + 1
            
    new_row = {"player_id": new_id, "nome": nome_clean, "telefone": ""}
    # Concatenar e salvar
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_players(df)
    return int(new_id)

def add_bet(apostador_nome, numeros_lista, custo_manual=None, descricao="Bolão", player_id=0):
    df = load_bets()
    custo = 0.0
    qtde = len(numeros_lista)
    if custo_manual: custo = float(custo_manual)
    else:
        if qtde == 6: custo = PRICE_PER_GAME
        elif qtde == 7: custo = 42.00
        elif qtde == 8: custo = 168.00
        elif qtde == 9: custo = 504.00
        
    new_row = {
        "id": str(uuid.uuid4()),
        "player_id": int(player_id),
        "apostador": apostador_nome,
        "numeros": str(sorted(numeros_lista)),
        "custo_total": custo,
        "conferido": False,
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "descricao": descricao
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_bets(df)

def delete_bets(bet_ids):
    df = load_bets()
    df = df[~df["id"].isin(bet_ids)]
    save_bets(df)

def add_contribution(player_id, valor, obs=""):
    df = load_contributions()
    new_row = {
        "id": str(uuid.uuid4()),
        "player_id": int(player_id),
        "valor": float(valor),
        "pago": True,
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "obs": obs
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_contributions(df)

def delete_contributions(contrib_ids):
    df = load_contributions()
    df = df[~df["id"].isin(contrib_ids)]
    save_contributions(df)

def toggle_bet_verified(bet_id):
    df = load_bets()
    if bet_id in df["id"].values:
        idx = df[df["id"] == bet_id].index[0]
        atual = bool(df.at[idx, "conferido"])
        df.at[idx, "conferido"] = not atual
        save_bets(df)
        return True
    return False

def balances():
    df_players = load_players()
    df_bets = load_bets()
    df_contrib = load_contributions()
    
    bal_data = []
    for pid in df_players["player_id"].unique():
        nome = df_players[df_players["player_id"]==pid]["nome"].iloc[0]
        
        credito = 0.0
        if not df_contrib.empty:
            df_c = df_contrib[df_contrib["player_id"] == pid]
            df_c["valor"] = pd.to_numeric(df_c["valor"], errors='coerce').fillna(0)
            credito = df_c[df_c["pago"] == True]["valor"].sum()
            
        debito = 0.0
        if not df_bets.empty:
            df_b = df_bets[df_bets["player_id"] == pid]
            df_b["custo_total"] = pd.to_numeric(df_b["custo_total"], errors='coerce').fillna(0)
            debito = df_b["custo_total"].sum()
            
        bal_data.append({
            "player_id": pid, "nome": nome,
            "total_pago": credito, "total_gasto": debito, "saldo": credito - debito
        })
    return pd.DataFrame(bal_data)

# --- FUNÇÃO ANTIGA (MANTIDA PARA COMPATIBILIDADE) ---
def score_bet_against_draw(bet_data, draw_data):
    """
    Retorna apenas o número de acertos (int).
    """
    bet_list = _to_int_list(bet_data)
    draw_list = _to_int_list(draw_data)
    hits = set(bet_list).intersection(set(draw_list))
    return len(hits)

# --- NOVA FUNÇÃO DETALHADA (ESSENCIAL PARA O PAINEL) ---
def check_bet_results(bet_data, draw_data):
    """
    Calcula prêmios considerando desdobramento (apostas > 6 números).
    Retorna dict: {'senas': int, 'quinas': int, 'quadras': int, 'best_hits': int}
    """
    bet_list = _to_int_list(bet_data)
    # Garante que draw_data seja uma lista limpa de inteiros, mesmo que venha como set ou string
    draw_list = _to_int_list(draw_data)
    draw_set = set(draw_list)
    
    # Se a aposta tem menos de 6, não tem como ganhar
    if len(bet_list) < 6:
        return {'senas': 0, 'quinas': 0, 'quadras': 0, 'best_hits': 0}
        
    # Se for aposta simples (6 números), cálculo direto
    if len(bet_list) == 6:
        hits = len(set(bet_list).intersection(draw_set))
        return {
            'senas': 1 if hits == 6 else 0,
            'quinas': 1 if hits == 5 else 0,
            'quadras': 1 if hits == 4 else 0,
            'best_hits': hits
        }
        
    # Aposta múltipla: desdobramento matemático
    results = {'senas': 0, 'quinas': 0, 'quadras': 0, 'best_hits': 0}
    
    # 1. Total de acertos brutos da aposta inteira
    total_hits = len(set(bet_list).intersection(draw_set))
    results['best_hits'] = total_hits
    
    # Se não acertou nem a quadra, sai
    if total_hits < 4:
        return results
        
    # 2. Desdobramento (Combinação de 6 em 6)
    for game in combinations(bet_list, 6):
        hits = len(set(game).intersection(draw_set))
        if hits == 6: results['senas'] += 1
        elif hits == 5: results['quinas'] += 1
        elif hits == 4: results['quadras'] += 1
        
    return results

def calculate_draw_stats(bets_df, draw_numbers):
    results = {'quadras': 0, 'quinas': 0, 'senas': 0}
    if bets_df is None or bets_df.empty: return results
    for _, row in bets_df.iterrows():
        # Usa a função detalhada para somar tudo
        res = check_bet_results(row['numeros'], draw_numbers)
        results['quadras'] += res['quadras']
        results['quinas'] += res['quinas']
        results['senas'] += res['senas']
    return results