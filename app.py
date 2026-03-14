import streamlit as st
import pandas as pd
import json
import math
import base64
from pathlib import Path
import streamlit.components.v1 as components
from supabase import create_client, Client

# ══════════════════════════════════════════════════════════════════════════════
# ██  CONFIG PAGINA  ███████████████████████████████████████████████████████████
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Calcetto Analytics",
    page_icon="⚽",
    layout="wide"
)

# Percorso base del progetto (dove si trova app.py)
BASE_DIR = Path(__file__).parent

# ══════════════════════════════════════════════════════════════════════════════
# ██  CSS GLOBALE  █████████████████████████████████████████████████████████████
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bangers&family=Nunito:wght@400;600;800&display=swap');

[data-testid="stAppViewContainer"] { background: #FFFFFF; }
[data-testid="stSidebar"]          { background: #EBEEF4; }
h1, h2, h3 { font-family: 'Bangers', cursive; letter-spacing: 3px; }

.player-header {
    background: #EBEEF4; border-radius: 16px;
    padding: 24px 32px; margin-bottom: 8px;
    position: relative; overflow: hidden;
}
.player-header::before {
    content: ''; position: absolute; top: -30px; right: -30px;
    width: 160px; height: 160px;
    background: #f7c948; border-radius: 50%; opacity: 0.12;
}
.player-name {
    font-family: 'Bangers', cursive; font-size: 6rem;
    letter-spacing: 6px; color: #1e90ff; line-height: 1; margin: 0;
}
.player-sub {
    font-family: 'Nunito', sans-serif; font-size: 0.9rem;
    color: #8888aa; letter-spacing: 3px;
    text-transform: uppercase; margin-top: 6px;
}
.avatar-frame {
    background: linear-gradient(160deg, #1e90ff, #1e90ff);
    border-radius: 20px; padding: 8px;
    box-shadow: 6px 6px 0px #1a1a2e; display: inline-block;
}
.stat-card {
    background: white; border: 3px solid #1a1a2e;
    border-radius: 14px; box-shadow: 4px 4px 0px #1a1a2e;
    padding: 16px 20px; text-align: center; margin-bottom: 4px;
}
.stat-value { font-family: 'Bangers', cursive; font-size: 3rem; color: #1a1a2e; line-height: 1; }
.stat-label { font-family: 'Nunito', sans-serif; font-size: 0.72rem; font-weight: 800;
              color: #888; text-transform: uppercase; letter-spacing: 2px; margin-top: 2px; }
.stat-accent       { color: #e84040; }
.stat-accent-blue  { color: #2255dd; }
.stat-accent-green { color: #22aa66; }

.bar-section {
    background: white; border: 3px solid #1a1a2e;
    border-radius: 14px; box-shadow: 4px 4px 0px #1a1a2e; padding: 22px 26px;
}
.bar-title { font-family: 'Bangers', cursive; font-size: 1.4rem;
             letter-spacing: 2px; color: #1a1a2e; margin-bottom: 4px; }
.bar-row { margin-bottom: 14px; }
.bar-meta { display: flex; justify-content: space-between; font-family: 'Nunito', sans-serif;
            font-size: 0.78rem; font-weight: 800; color: #444;
            text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }
.bar-track { background: #eee; border: 2px solid #1a1a2e; border-radius: 8px;
             height: 14px; overflow: hidden; }
.bar-fill  { height: 100%; border-radius: 6px; }

.badge {
    display: inline-block; background: #f7c948;
    border: 2px solid #1a1a2e; border-radius: 20px;
    padding: 3px 14px; font-family: 'Nunito', sans-serif;
    font-size: 0.78rem; font-weight: 800; color: #1a1a2e;
    letter-spacing: 1px; box-shadow: 2px 2px 0px #1a1a2e; margin-top: 10px;
}

/* Card giocatore in sidebar */
.player-card {
    background: white; border: 2px solid #1a1a2e;
    border-radius: 10px; padding: 10px 14px;
    margin-bottom: 6px; cursor: pointer;
    transition: all 0.15s;
    font-family: 'Nunito', sans-serif; font-weight: 800;
    font-size: 0.85rem; color: #1a1a2e;
    box-shadow: 2px 2px 0px #1a1a2e;
}
.player-card:hover { background: #1e90ff; color: white; }
.player-card.active { background: #1a1a2e; color: #f7c948; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# ██  CARICA JSON GIOCATORI  ███████████████════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data
def load_giocatori_config():
    json_path = BASE_DIR / "assets" / "giocatori" / "giocatori.json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {g["nome"]: g for g in data["giocatori"]}

giocatori_config = load_giocatori_config()
nomi_giocatori   = sorted(giocatori_config.keys())


# ══════════════════════════════════════════════════════════════════════════════
# ██  CONNESSIONE DB  ██████████════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

@st.cache_data(ttl=60)
def load_data():
    response = supabase.table("statistiche").select("*").execute()
    df = pd.DataFrame(response.data)
    df_agg = df.groupby("giocatore").agg(
        presenze = ("presenze", "sum"),
        gol      = ("gol",      "sum"),
        assist   = ("assist",   "sum"),
        pagella  = ("pagella",  "mean"),
    ).reset_index()
    df_agg["media_gol"]     = (df_agg["gol"]    / df_agg["presenze"]).round(2)
    df_agg["media_assist"]  = (df_agg["assist"]  / df_agg["presenze"]).round(2)
    df_agg["media_pagella"] = df_agg["pagella"].round(2)
    return df_agg

@st.cache_data(ttl=60)
def load_storico(nome_giocatore):
    response = (supabase.table("statistiche")
                .select('"data di gioco", gol, assist, pagella')
                .eq("giocatore", nome_giocatore)
                .execute())
    return pd.DataFrame(response.data)


# ══════════════════════════════════════════════════════════════════════════════
# ██  SIDEBAR — selezione giocatore  ███════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style='font-family:Bangers,cursive;font-size:2rem;
                letter-spacing:4px;color:#1a1a2e;margin-bottom:4px'>
        ⚽ CALCETTO
    </div>
    <div style='font-family:Nunito,sans-serif;font-size:0.75rem;
                color:#8888aa;letter-spacing:2px;margin-bottom:20px'>
        ANALYTICS DASHBOARD
    </div>
    """, unsafe_allow_html=True)

    if "giocatore_selezionato" not in st.session_state:
        st.session_state.giocatore_selezionato = None

    opzioni = ["— Seleziona un giocatore —"] + [
        giocatori_config[n]["nome_display"] for n in nomi_giocatori
    ]
    if st.session_state.giocatore_selezionato in (None, "classifiche", "modifica"):
        idx_corrente = 0
    else:
        cfg_sel      = giocatori_config[st.session_state.giocatore_selezionato]
        idx_corrente = opzioni.index(cfg_sel["nome_display"])

    scelta = st.selectbox(
        "👤 Giocatore",
        options=opzioni,
        index=idx_corrente,
        label_visibility="collapsed"
    )

    if scelta == "— Seleziona un giocatore —":
        if st.session_state.giocatore_selezionato not in (None, "classifiche", "modifica"):
            st.session_state.giocatore_selezionato = None
            st.rerun()
    else:
        nome_sel = next(n for n in nomi_giocatori
                        if giocatori_config[n]["nome_display"] == scelta)
        if st.session_state.giocatore_selezionato != nome_sel:
            st.session_state.giocatore_selezionato = nome_sel
            st.session_state.bar_mode  = "totali"
            st.session_state.plot_mode = "tutte"
            st.rerun()

    st.markdown("<div style='margin-top:10px'></div>", unsafe_allow_html=True)
    is_classifiche = st.session_state.giocatore_selezionato == "classifiche"
    if st.button("🏆 CLASSIFICHE", use_container_width=True,
                 type="primary" if is_classifiche else "secondary"):
        st.session_state.giocatore_selezionato = "classifiche"
        st.rerun()

    is_modifica = st.session_state.giocatore_selezionato == "modifica"
    if st.button("✏️ MODIFICA DATI", use_container_width=True,
                 type="primary" if is_modifica else "secondary"):
        st.session_state.giocatore_selezionato = "modifica"
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ██  CONTENUTO PRINCIPALE  ████════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
sel = st.session_state.giocatore_selezionato

# ── HOME ──────────────────────────────────────────────────────────────────────
if sel is None:
    st.markdown("""
    <div style='text-align:center;padding:60px 0 20px'>
        <div style='font-family:Bangers,cursive;font-size:5rem;
                    letter-spacing:6px;color:#1a1a2e'>⚽ CALCETTO</div>
        <div style='font-family:Bangers,cursive;font-size:2rem;
                    letter-spacing:4px;color:#1e90ff'>ANALYTICS</div>
        <div style='font-family:Nunito,sans-serif;font-size:1rem;
                    color:#8888aa;margin-top:16px'> 
            Clicca un giocatore nella sidebar per visualizzare le sue statistiche, o vai alle classifiche generali!
        </div>
    </div>
    """, unsafe_allow_html=True)
# ── CLASSIFICHE ───────────────────────────────────────────────────────────────
elif sel == "classifiche":
    df = load_data()

    METRICHE = {
        "⚽ Gol":               ("gol",          "GOL TOTALI"),
        "⚽ Gol per partita":   ("media_gol",    "GOL / PARTITA"),
        "🎯 Assist":            ("assist",        "ASSIST TOTALI"),
        "🎯 Assist per partita":("media_assist", "ASSIST / PARTITA"),
    }

    st.markdown("""
    <div style='font-family:Bangers,cursive;font-size:3rem;
                letter-spacing:4px;color:#1a1a2e;margin-bottom:4px'>
        🏆 CLASSIFICHE
    </div>
    """, unsafe_allow_html=True)

    metrica_label = st.selectbox(
        "Metrica",
        options=list(METRICHE.keys()),
        index=0,
        label_visibility="collapsed"
    )
    colonna, titolo_col = METRICHE[metrica_label]

    df_rank = df.sort_values(colonna, ascending=False).reset_index(drop=True)
    top3  = df_rank.head(3).to_dict("records")
    resto = df_rank.iloc[3:10].to_dict("records")

    ordine_podio  = [top3[1], top3[0], top3[2]] if len(top3) == 3 else top3
    altezze_podio = [160, 210, 120]
    colori_podio  = ["#C0C0C0", "#FFD700", "#CD7F32"]
    posizioni_num = [2, 1, 3]

    def img_to_b64(nome_giocatore):
        if nome_giocatore in giocatori_config:
            path = BASE_DIR / giocatori_config[nome_giocatore]["avatar"]
        else:
            path = Path("")
        if not path.exists():
            path = BASE_DIR / "assets" / "avatar" / "Default.png"
        try:
            ext  = path.suffix.lower().replace(".", "")
            mime = "jpeg" if ext in ("jpg", "jpeg") else ext
            with open(path, "rb") as f:
                data = base64.b64encode(f.read()).decode()
            return f"data:image/{mime};base64,{data}"
        except Exception:
            return ""

    blocchi_podio = ""
    for gioc, h, colore, pos in zip(ordine_podio, altezze_podio, colori_podio, posizioni_num):
        nome_g  = gioc["giocatore"]
        valore  = gioc[colonna]
        display = giocatori_config[nome_g]["nome_display"] if nome_g in giocatori_config else nome_g.upper()
        b64     = img_to_b64(nome_g)
        val_str = (f"{valore:.2f}" if isinstance(valore, float) and valore != int(valore)
                   else str(int(valore)) if isinstance(valore, float) else str(valore))

        img_tag = (
            f'<img src="{b64}" style="width:80px;height:80px;object-fit:cover;border-radius:50%;border:3px solid {colore};box-shadow:0 2px 8px rgba(0,0,0,0.15)"/>'
            if b64 else
            f'<div style="width:80px;height:80px;border-radius:50%;background:#eee;border:3px solid {colore};display:flex;align-items:center;justify-content:center;font-size:2rem;">🧑</div>'
        )

        blocchi_podio += f"""
        <div style="display:flex;flex-direction:column;align-items:center;
                    justify-content:flex-end;flex:1;gap:0;">
            <div style="font-family:'Bangers',cursive;font-size:1.6rem;
                        color:#1a1a2e;letter-spacing:1px;margin-bottom:6px">
                {val_str}
            </div>
            {img_tag}
            <div style="font-family:'Bangers',cursive;font-size:1rem;
                        letter-spacing:2px;color:#1a1a2e;margin:6px 0 0">
                {display}
            </div>
            <div style="width:100%;height:{h}px;background:{colore};
                        border-radius:8px 8px 0 0;margin-top:8px;
                        display:flex;align-items:center;justify-content:center;
                        box-shadow:inset 0 2px 8px rgba(0,0,0,0.10);">
                <span style="font-family:'Bangers',cursive;font-size:2.5rem;
                              color:rgba(0,0,0,0.20)">
                    {pos}
                </span>
            </div>
        </div>"""

    podio_html = f"""<!DOCTYPE html><html>
<head>
<link href="https://fonts.googleapis.com/css2?family=Bangers&family=Nunito:wght@700;800&display=swap" rel="stylesheet"/>
<style>body{{margin:0;background:transparent;}}</style>
</head><body>
<div style="background:white;border:3px solid #1a1a2e;border-radius:14px;
            box-shadow:4px 4px 0px #1a1a2e;padding:32px 40px 0;max-width:700px;margin:0 auto;">
  <div style="font-family:'Bangers',cursive;font-size:1.2rem;letter-spacing:2px;
              color:#8888aa;margin-bottom:24px;text-transform:uppercase">
      {titolo_col}
  </div>
  <div style="display:flex;align-items:flex-end;gap:12px;justify-content:center;">
      {blocchi_podio}
  </div>
</div>
</body></html>"""

    components.html(podio_html, height=500)
# ------------classifica restante -------------
    st.markdown("<br>", unsafe_allow_html=True)
    if resto:
        righe = ""
        for i, gioc in enumerate(resto):
            nome_g  = gioc["giocatore"]
            valore  = gioc[colonna]
            display = giocatori_config[nome_g]["nome_display"] if nome_g in giocatori_config else nome_g.upper()
            val_str = (f"{valore:.2f}" if isinstance(valore, float) and valore != int(valore)
                       else str(int(valore)) if isinstance(valore, float) else str(valore))
            bg = "#f8f9fc" if i % 2 == 0 else "white"
            righe += f"""
            <div style="display:flex;justify-content:space-between;align-items:center;
                        padding:12px 20px;background:{bg};border-bottom:1px solid #eee;">
                <div style="display:flex;align-items:center;gap:14px;">
                    <span style="font-family:'Bangers',cursive;font-size:1.2rem;
                                 color:#aaa;min-width:28px">{i+4}</span>
                    <span style="font-family:'Bangers',cursive;font-size:1.2rem;
                                 letter-spacing:1px;color:#1a1a2e">{display}</span>
                </div>
                <span style="font-family:'Nunito',sans-serif;font-weight:800;
                             font-size:1rem;color:#1e90ff">{val_str}</span>
            </div>"""

        st.components.v1.html(f"""
        <div style="background:white;border:3px solid #1a1a2e;border-radius:14px;
                    box-shadow:4px 4px 0px #1a1a2e;overflow:hidden;">
            <div style="padding:14px 20px;border-bottom:2px solid #1a1a2e;">
                <span style="font-family:'Bangers',cursive;font-size:1.2rem;
                             letter-spacing:2px;color:#1a1a2e">CLASSIFICA RESTANTE</span>
            </div>
            {righe}
        </div>
        """, height=500)

# ── MODIFICA DATI ─────────────────────────────────────────────────────────────
elif sel == "modifica":
# --- PSW PROTETTA ---
    st.markdown("""
    <div style='font-family:Bangers,cursive;font-size:3rem;
                letter-spacing:4px;color:#1a1a2e;margin-bottom:4px'>
        ✏️ MODIFICA DATI
    </div>
    """, unsafe_allow_html=True)

    if "admin_autenticato" not in st.session_state:
        st.session_state.admin_autenticato = False

    if not st.session_state.admin_autenticato:
        st.markdown("""
        <div style="background:#EBEEF4;border:3px solid #1a1a2e;border-radius:14px;
                    box-shadow:4px 4px 0px #1a1a2e;padding:32px;max-width:400px;margin:40px auto;">
            <div style="font-family:'Bangers',cursive;font-size:1.5rem;
                        letter-spacing:2px;color:#1a1a2e;margin-bottom:16px">
                🔒 AREA PROTETTA
            </div>
            <div style="font-family:'Nunito',sans-serif;font-size:0.85rem;
                        color:#8888aa;margin-bottom:8px">
                Inserisci la password per accedere alla modifica dei dati.
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_pwd, _ = st.columns([1, 2])
        with col_pwd:
            pwd = st.text_input("Password", type="password", label_visibility="collapsed",
                                placeholder="Password admin...")
            if st.button("ACCEDI", use_container_width=True, type="primary"):
                if pwd == st.secrets.get("ADMIN_PASSWORD", ""):
                    st.session_state.admin_autenticato = True
                    st.rerun()
                else:
                    st.error("Password errata.")

    else:
        col_title, col_logout = st.columns([4, 1])
        with col_logout:
            if st.button("🔓 Esci", type="secondary"):
                st.session_state.admin_autenticato = False
                st.rerun()

        @st.cache_data(ttl=10)
        def load_partite_raw():
            response = supabase.table("statistiche").select("*").order("id").execute()
            return pd.DataFrame(response.data)

        tab_add, tab_edit, tab_del = st.tabs([
            "➕ AGGIUNGI PAGELLA",
            "✏️ MODIFICA PAGELLA",
            "🗑️ ELIMINA PAGELLA"
        ])

        with tab_add:
            st.markdown("<br>", unsafe_allow_html=True)
            nomi_db = sorted([g["nome"] for g in giocatori_config.values()])

            with st.form("form_aggiungi"):
                st.markdown("**Dati della nuova pagella**")
                c1, c2, c3 = st.columns(3)
                with c1:
                    gioc_new = st.selectbox("Giocatore", nomi_db)
                    data_new = st.date_input("Data partita")
                with c2:
                    gol_new    = st.number_input("Gol",    min_value=0, step=1, value=0)
                    assist_new = st.number_input("Assist", min_value=0, step=1, value=0)
                with c3:
                    pagella_new  = st.slider("Pagella", min_value=1.0, max_value=10.0, value=7.0, step=0.5)
                    presenze_new = 1

                submitted = st.form_submit_button("💾 SALVA PARTITA", type="primary", use_container_width=True)
                if submitted:
                    try:
                        supabase.table("statistiche").insert({
                            "data di gioco": data_new.strftime("%m/%d/%y"),
                            "giocatore":     gioc_new,
                            "presenze":      presenze_new,
                            "gol":           int(gol_new),
                            "assist":        int(assist_new),
                            "pagella":       float(pagella_new),
                        }).execute()
                        load_data.clear()
                        load_storico.clear()
                        load_partite_raw.clear()
                        st.success(f"✅ Partita di {gioc_new} del {data_new} salvata!")
                    except Exception as e:
                        st.error(f"Errore: {e}")

        with tab_edit:
            st.markdown("<br>", unsafe_allow_html=True)
            df_raw = load_partite_raw()
            df_raw = df_raw.sort_values("id", ascending=False).reset_index(drop=True)  # Ordina per ID decrescente

            if df_raw.empty:
                st.info("Nessuna partita nel database.")
            else:
                opzioni_righe = [
                    f"{row.get('data di gioco','?')} — {row['giocatore']} —  {int(row['gol'])}G - {int(row['assist'])}A - {row['pagella']}⭐"
                    for _, row in df_raw.iterrows()
                ]
                scelta_riga = st.selectbox("Seleziona partita da modificare",
                                           opzioni_righe, label_visibility="collapsed")
                idx_sel = opzioni_righe.index(scelta_riga)
                riga    = df_raw.iloc[idx_sel]

                with st.form("form_modifica"):
                    st.markdown(f"**Modifica partita ID {riga['id']}**")
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        gioc_ed = st.selectbox(
                            "Giocatore",
                            sorted([g["nome"] for g in giocatori_config.values()]),
                            index=sorted([g["nome"] for g in giocatori_config.values()]).index(riga["giocatore"])
                            if riga["giocatore"] in [g["nome"] for g in giocatori_config.values()] else 0
                        )
                        data_ed = st.text_input("Data (mm/dd/yy)", value=riga.get("data di gioco", ""))
                    with c2:
                        gol_ed    = st.number_input("Gol",    min_value=0, step=1, value=int(riga["gol"]))
                        assist_ed = st.number_input("Assist", min_value=0, step=1, value=int(riga["assist"]))
                    with c3:
                        pagella_ed = st.slider("Pagella", min_value=1.0, max_value=10.0,
                                               value=float(riga["pagella"]), step=0.5)

                    submitted_ed = st.form_submit_button("💾 AGGIORNA", type="primary", use_container_width=True)
                    if submitted_ed:
                        try:
                            supabase.table("statistiche").update({
                                "data di gioco": data_ed,
                                "giocatore":     gioc_ed,
                                "gol":           int(gol_ed),
                                "assist":        int(assist_ed),
                                "pagella":       float(pagella_ed),
                            }).eq("id", int(riga["id"])).execute()
                            load_data.clear()
                            load_storico.clear()
                            load_partite_raw.clear()
                            st.success(f"✅ Partita ID {riga['id']} aggiornata!")
                        except Exception as e:
                            st.error(f"Errore: {e}")

        with tab_del:
            st.markdown("<br>", unsafe_allow_html=True)
            df_raw2 = load_partite_raw()
            df_raw2 = df_raw2.sort_values("id", ascending=False).reset_index(drop=True)  # Ordina per ID decrescente

            if df_raw2.empty:
                st.info("Nessuna partita nel database.")
            else:
                opzioni_del = [
                    f"{row.get('data di gioco','?')} — {row['giocatore']} —  {int(row['gol'])}G - {int(row['assist'])}A - {row['pagella']}⭐"
                    for _, row in df_raw2.iterrows()
                ]
                scelta_del = st.selectbox("Seleziona partita da eliminare",
                                          opzioni_del, label_visibility="collapsed",
                                          key="del_select")
                idx_del  = opzioni_del.index(scelta_del)
                riga_del = df_raw2.iloc[idx_del]

                st.markdown(f"""
                <div style="background:#fff3f3;border:2px solid #e84040;border-radius:10px;
                            padding:14px 20px;margin:12px 0;font-family:'Nunito',sans-serif;
                            font-size:0.9rem;color:#1a1a2e;">
                    <strong>Stai per eliminare:</strong><br>
                    Giocatore: <b>{riga_del['giocatore']}</b> &nbsp;|&nbsp;
                    Data: <b>{riga_del.get('data di gioco','?')}</b> &nbsp;|&nbsp;
                    Gol: <b>{int(riga_del['gol'])}</b> &nbsp;|&nbsp;
                    Assist: <b>{int(riga_del['assist'])}</b> &nbsp;|&nbsp;
                    Pagella: <b>{riga_del['pagella']}</b>
                </div>
                """, unsafe_allow_html=True)

                conferma = st.checkbox("⚠️ Confermo di voler eliminare questa partita")
                if st.button("🗑️ ELIMINA", type="primary", disabled=not conferma):
                    try:
                        supabase.table("statistiche").delete().eq("id", int(riga_del["id"])).execute()
                        load_data.clear()
                        load_storico.clear()
                        load_partite_raw.clear()
                        st.success(f"✅ Partita ID {riga_del['id']} eliminata.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Errore: {e}")

# ── PAGINA GIOCATORE ──────────────────────────────────────────────────────────
else:
    cfg          = giocatori_config[sel]
    NOME         = cfg["nome"]
    NOME_DISPLAY = cfg["nome_display"]
    RUOLO        = cfg["ruolo"]
    POSIZIONI    = cfg["posizioni"]
    ATTRIBUTI    = cfg["attributi"]
    AVATAR_PATH  = BASE_DIR / cfg["avatar"]
    DEFAULT_PATH = BASE_DIR / "assets" / "avatar" / "Default.png"

    df      = load_data()
    storico = load_storico(NOME)

    if df[df["giocatore"] == NOME].empty:
        st.warning(f"Nessun dato trovato per '{NOME}' nel database.")
        st.stop()

    p = df[df["giocatore"] == NOME].iloc[0]

    max_gol    = int(df["gol"].max())
    max_assist = int(df["assist"].max())
    max_pag    = float(df["media_pagella"].max())
    max_pres   = int(df["presenze"].max())
    max_mg     = float(df["media_gol"].max())
    max_ma     = float(df["media_assist"].max())

    mask         = df["giocatore"] == NOME
    rank_gol     = int(df["gol"].rank(ascending=False)[mask].values[0])
    rank_assist  = int(df["assist"].rank(ascending=False)[mask].values[0])
    rank_pagella = int(df["media_pagella"].rank(ascending=False)[mask].values[0])

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="player-header">
        <p class="player-name">{NOME_DISPLAY}</p>
        <p class="player-sub">{RUOLO} · Calcetto Analytics</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_avatar, col_stats = st.columns([1, 2], gap="large")

    # ── Avatar ────────────────────────────────────────────────────────────────
    with col_avatar:
        img_path = AVATAR_PATH if AVATAR_PATH.exists() else DEFAULT_PATH
        st.markdown('<div class="avatar-frame">', unsafe_allow_html=True)
        st.image(str(img_path), width="stretch")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown(f"""
        <div style="text-align:center;margin-top:14px">
            <span class="badge">⚽ {int(p['presenze'])} PRESENZE</span>
        </div>""", unsafe_allow_html=True)

    # ── Stats + barre ─────────────────────────────────────────────────────────
    with col_stats:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value stat-accent">{int(p['gol'])}</div>
                <div class="stat-label">⚽ Gol</div>
                <div style="font-family:'Nunito',sans-serif;font-size:0.7rem;color:#aaa;margin-top:4px">#{rank_gol} nel gruppo</div>
            </div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value stat-accent-blue">{int(p['assist'])}</div>
                <div class="stat-label">🎯 Assist</div>
                <div style="font-family:'Nunito',sans-serif;font-size:0.7rem;color:#aaa;margin-top:4px">#{rank_assist} nel gruppo</div>
            </div>""", unsafe_allow_html=True)
        with c3:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value stat-accent-green">{float(p['media_pagella']):.1f}</div>
                <div class="stat-label">⭐ Voto medio</div>
                <div style="font-family:'Nunito',sans-serif;font-size:0.7rem;color:#aaa;margin-top:4px">#{rank_pagella} nel gruppo</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if "bar_mode" not in st.session_state:
            st.session_state.bar_mode = "totali"

        col_t1, col_t2, _ = st.columns([1, 1, 3])
        with col_t1:
            if st.button("TOTALI", use_container_width=True,
                         type="primary" if st.session_state.bar_mode == "totali" else "secondary"):
                st.session_state.bar_mode = "totali"
                st.rerun()
        with col_t2:
            if st.button("PER PARTITA", use_container_width=True,
                         type="primary" if st.session_state.bar_mode == "per_partita" else "secondary"):
                st.session_state.bar_mode = "per_partita"
                st.rerun()

        if st.session_state.bar_mode == "totali":
            val_gol, max_g, label_gol = int(p['gol']),           max_gol,    "GOL TOTALI"
            val_ass, max_a, label_ass = int(p['assist']),         max_assist, "ASSIST TOTALI"
        else:
            val_gol, max_g, label_gol = float(p['media_gol']),   max_mg,     "GOL / PARTITA"
            val_ass, max_a, label_ass = float(p['media_assist']), max_ma,     "ASSIST / PARTITA"

        def bar(label, val, max_val, color):
            pct = round((val / max_val) * 100) if max_val > 0 else 0
            dv  = f"{val:.2f}" if isinstance(val, float) else str(val)
            dm  = f"{max_val:.2f}" if isinstance(max_val, float) else str(max_val)
            return (
                f"<div class='bar-row'>"
                f"<div class='bar-meta'><span>{label}</span><span>{dv} / {dm}</span></div>"
                f"<div class='bar-track'>"
                f"<div class='bar-fill' style='width:{pct}%;background:{color}'></div>"
                f"</div></div>"
            )

        st.markdown(f"""
        <div class="bar-section">
            <div class="bar-title">CONFRONTO CON IL GRUPPO</div>
            {bar(label_gol, val_gol, max_g,  "#e84040")}
            {bar(label_ass, val_ass, max_a,  "#2255dd")}
            {bar("VOTO MEDIO", float(p['media_pagella']), max_pag,  "#22aa66")}
            {bar("PRESENZE",   int(p['presenze']),        max_pres, "#f09a1a")}
        </div>
        """, unsafe_allow_html=True)

    # ── Campo + Radar ─────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    col_campo, col_radar = st.columns([1, 1], gap="large")

    def rgba(v, r=230, g=80, b=30):
        return f"rgba({r},{g},{b},{0.06 + v * 0.88:.2f})"

    with col_campo:
        campo_html = f"""<!DOCTYPE html><html>
<head>
<link href="https://fonts.googleapis.com/css2?family=Bangers&family=Nunito:wght@700;800&display=swap" rel="stylesheet"/>
<style>body{{margin:0;background:transparent;}}</style>
</head><body>
<div style="background:white;border:3px solid #1a1a2e;border-radius:14px;
            box-shadow:4px 4px 0px #1a1a2e;padding:22px 26px;max-width:460px;margin:0 auto;">
  <div style="font-size:1.4rem;letter-spacing:2px;color:#1a1a2e;
              font-family:'Bangers',cursive;margin-bottom:14px">ZONA DI GIOCO</div>
  <div style="max-width:320px;margin:0 auto;">
  <svg viewBox="0 0 420 560" xmlns="http://www.w3.org/2000/svg" style="width:100%;display:block;border-radius:10px;">
    <defs>
      <pattern id="s" x="0" y="0" width="60" height="560" patternUnits="userSpaceOnUse">
        <rect x="0"  y="0" width="30" height="560" fill="#2d8a4e"/>
        <rect x="30" y="0" width="30" height="560" fill="#328f52"/>
      </pattern>
    </defs>
    <rect width="420" height="560" fill="url(#s)" rx="10"/>
    <rect x="0"   y="0" width="105" height="560" fill="{rgba(POSIZIONI['ala_sinistra'])}"/>
    <rect x="315" y="0" width="105" height="560" fill="{rgba(POSIZIONI['ala_destra'])}"/>
    <rect x="105" y="0"   width="210" height="280" fill="{rgba(POSIZIONI['punta'])}"/>
    <rect x="105" y="280" width="210" height="186" fill="{rgba(POSIZIONI['difensore_centrale'])}"/>
    <rect x="153" y="478" width="114" height="77"  fill="{rgba(POSIZIONI['portiere'])}"/>
    <rect x="5" y="5" width="410" height="550" fill="none" stroke="white" stroke-width="2.5" rx="8" opacity="0.95"/>
    <line x1="5" y1="280" x2="415" y2="280" stroke="white" stroke-width="2" opacity="0.95"/>
    <circle cx="210" cy="280" r="55" fill="none" stroke="white" stroke-width="2" opacity="0.95"/>
    <circle cx="210" cy="280" r="3"  fill="white" opacity="0.95"/>
    <rect x="97"  y="5"   width="226" height="88" fill="none" stroke="white" stroke-width="2" opacity="0.95"/>
    <rect x="163" y="5"   width="94"  height="34" fill="none" stroke="white" stroke-width="2" opacity="0.95"/>
    <rect x="178" y="1"   width="64"  height="8"  fill="none" stroke="white" stroke-width="3"/>
    <circle cx="210" cy="116" r="3" fill="white" opacity="0.95"/>
    <path d="M 148 93 A 62 62 0 0 0 272 93" fill="none" stroke="white" stroke-width="2" opacity="0.95"/>
    <rect x="97"  y="467" width="226" height="88" fill="none" stroke="white" stroke-width="2" opacity="0.95"/>
    <rect x="163" y="521" width="94"  height="34" fill="none" stroke="white" stroke-width="2" opacity="0.95"/>
    <rect x="178" y="551" width="64"  height="8"  fill="none" stroke="white" stroke-width="3"/>
    <circle cx="210" cy="444" r="3" fill="white" opacity="0.95"/>
    <path d="M 148 467 A 62 62 0 0 1 272 467" fill="none" stroke="white" stroke-width="2" opacity="0.95"/>
    <circle cx="210" cy="510" r="16" fill="#1a1a2e" opacity="0.55"/>
    <text x="210" y="515" text-anchor="middle" font-family="Nunito,sans-serif" font-size="11" font-weight="800" fill="white">POR</text>
    <circle cx="210" cy="373" r="16" fill="#1a1a2e" opacity="0.55"/>
    <text x="210" y="378" text-anchor="middle" font-family="Nunito,sans-serif" font-size="11" font-weight="800" fill="white">DIF</text>
    <circle cx="52"  cy="280" r="16" fill="#1a1a2e" opacity="0.55"/>
    <text x="52"  y="285" text-anchor="middle" font-family="Nunito,sans-serif" font-size="11" font-weight="800" fill="white">ALA</text>
    <circle cx="368" cy="280" r="16" fill="#1a1a2e" opacity="0.55"/>
    <text x="368" y="285" text-anchor="middle" font-family="Nunito,sans-serif" font-size="11" font-weight="800" fill="white">ALA</text>
    <circle cx="210" cy="145" r="16" fill="#1a1a2e" opacity="0.55"/>
    <text x="210" y="150" text-anchor="middle" font-family="Nunito,sans-serif" font-size="11" font-weight="800" fill="white">PUN</text>
  </svg>
  </div>
  <div style="display:flex;align-items:center;gap:10px;margin-top:14px;justify-content:center;">
    <span style="font-family:'Nunito',sans-serif;font-size:0.70rem;color:#888;letter-spacing:1px;font-weight:700;">POCO</span>
    <div style="width:110px;height:11px;border-radius:6px;border:1.5px solid #ddd;
                background:linear-gradient(to right,rgba(230,80,30,0.06),rgba(230,80,30,0.94));"></div>
    <span style="font-family:'Nunito',sans-serif;font-size:0.70rem;color:#888;letter-spacing:1px;font-weight:700;">MOLTO</span>
  </div>
</div>
</body></html>"""
        components.html(campo_html, height=680)

    with col_radar:
        labels_r = list(ATTRIBUTI.keys())
        values_r = list(ATTRIBUTI.values())
        n      = len(labels_r)
        CX, CY = 250, 265
        R_MAX  = 155
        angles = [math.pi * (-0.5 + 2 * i / n) for i in range(n)]

        def polar(val, angle):
            r = (val / 100) * R_MAX
            return CX + r * math.cos(angle), CY + r * math.sin(angle)

        def ring_points(pct):
            pts = [polar(pct, a) for a in angles]
            return " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)

        player_pts = " ".join(
            f"{polar(v, a)[0]:.1f},{polar(v, a)[1]:.1f}"
            for v, a in zip(values_r, angles)
        )

        def label_pos(angle, offset=38):
            r = R_MAX + offset
            return CX + r * math.cos(angle), CY + r * math.sin(angle)

        spokes = "".join(
            f'<line x1="{CX}" y1="{CY}" x2="{polar(100,a)[0]:.1f}" y2="{polar(100,a)[1]:.1f}" stroke="#ddd" stroke-width="1.5"/>'
            for a in angles
        )
        rings = "".join(
            f'<polygon points="{ring_points(pct)}" fill="none" stroke="#ddd" stroke-width="1.2"/>'
            for pct in [25, 50, 75, 100]
        )
        label_els = ""
        for lbl, val, angle in zip(labels_r, values_r, angles):
            lx, ly = label_pos(angle)
            anchor = "end" if lx < CX - 10 else ("start" if lx > CX + 10 else "middle")
            dy_lbl = -14 if ly < CY - 10 else (14 if ly > CY + 10 else 0)
            label_els += f"""
            <text x="{lx:.1f}" y="{ly+dy_lbl:.1f}" text-anchor="{anchor}"
                  font-family="Bangers,cursive" font-size="15" letter-spacing="1" fill="#1a1a2e">{lbl}</text>
            <text x="{lx:.1f}" y="{ly+dy_lbl+17:.1f}" text-anchor="{anchor}"
                  font-family="Nunito,sans-serif" font-size="12" font-weight="800" fill="#1e90ff">{val}</text>"""

        radar_html = f"""<!DOCTYPE html><html>
<head>
<link href="https://fonts.googleapis.com/css2?family=Bangers&family=Nunito:wght@700;800&display=swap" rel="stylesheet"/>
<style>body{{margin:0;background:transparent;}}</style>
</head><body>
<div style="background:white;border:3px solid #1a1a2e;border-radius:14px;
            box-shadow:4px 4px 0px #1a1a2e;padding:22px 26px;max-width:460px;margin:0 auto;">
  <div style="font-size:1.4rem;letter-spacing:2px;color:#1a1a2e;
              font-family:'Bangers',cursive;margin-bottom:14px">ATTRIBUTI</div>
  <svg viewBox="0 0 500 520" xmlns="http://www.w3.org/2000/svg" style="width:100%;display:block;overflow:visible;">
    {rings}{spokes}
    <polygon points="{player_pts}" fill="rgba(30,144,255,0.18)"
             stroke="#1e90ff" stroke-width="2.5" stroke-linejoin="round"/>
    {"".join(f'<circle cx="{polar(v,a)[0]:.1f}" cy="{polar(v,a)[1]:.1f}" r="5" fill="#1e90ff" stroke="white" stroke-width="2"/>' for v,a in zip(values_r,angles))}
    {label_els}
    <text x="{CX+4}" y="{CY-R_MAX*0.25-2:.0f}" font-family="Nunito,sans-serif" font-size="10" fill="#ccc" font-weight="700">25</text>
    <text x="{CX+4}" y="{CY-R_MAX*0.50-2:.0f}" font-family="Nunito,sans-serif" font-size="10" fill="#ccc" font-weight="700">50</text>
    <text x="{CX+4}" y="{CY-R_MAX*0.75-2:.0f}" font-family="Nunito,sans-serif" font-size="10" fill="#ccc" font-weight="700">75</text>
    <text x="{CX+4}" y="{CY-R_MAX-2:.0f}"      font-family="Nunito,sans-serif" font-size="10" fill="#ccc" font-weight="700">100</text>
  </svg>
</div>
</body></html>"""
        components.html(radar_html, height=680)

    # ── Grafico andamento temporale ───────────────────────────────────────────
    # ✅ INDENTATO dentro l'else della pagina giocatore
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="background:white;border:3px solid #1a1a2e;border-radius:14px;
                box-shadow:4px 4px 0px #1a1a2e;padding:22px 26px;margin-bottom:8px;">
      <div style="font-family:'Bangers',cursive;font-size:1.4rem;letter-spacing:2px;
                  color:#1a1a2e;">ANDAMENTO PARTITE</div>
    </div>
    """, unsafe_allow_html=True)

    if "plot_mode" not in st.session_state:
        st.session_state.plot_mode = "tutte"

    pm_cols = st.columns([1, 1, 1, 1, 4])
    for col_btn, op, lbl in zip(pm_cols[:4],
                                ["gol", "assist", "pagella", "tutte"],
                                ["⚽ GOL", "🎯 ASSIST", "⭐ VOTO", "📊 TUTTE"]):
        with col_btn:
            if st.button(lbl, key=f"plot_{op}_{NOME}", use_container_width=True,
                         type="primary" if st.session_state.plot_mode == op else "secondary"):
                st.session_state.plot_mode = op
                st.rerun()

    modo = st.session_state.plot_mode

    if storico.empty:
        st.info("Nessuna partita registrata per questo giocatore.")
    else:
        storico_plot = storico.rename(columns={"data di gioco": "data"}).copy()
        try:
            storico_plot["data"] = pd.to_datetime(storico_plot["data"], format="%m/%d/%y", errors="coerce")
            if storico_plot["data"].isna().all():
                raise ValueError
        except ValueError:
            storico_plot["data"] = pd.to_datetime(storico_plot["data"], format="%d/%m/%y", errors="coerce")

        storico_plot = storico_plot.dropna(subset=["data"]).sort_values("data").reset_index(drop=True)

        # ✅ FIX: json.dumps produce JSON valido (virgolette doppie, None→null)
        labels_js  = json.dumps([d.strftime("%d/%m/%y") for d in storico_plot["data"]])

        if modo == "gol":
            datasets_js = json.dumps([{
                "label": "Gol",
                "data": storico_plot["gol"].tolist(),
                "borderColor": "#e84040",
                "backgroundColor": "rgba(232,64,64,0.12)",
                "borderWidth": 2.5,
                "pointRadius": 5,
                "pointBackgroundColor": "#e84040",
                "tension": 0.35,
                "fill": True
            }])
        elif modo == "assist":
            datasets_js = json.dumps([{
                "label": "Assist",
                "data": storico_plot["assist"].tolist(),
                "borderColor": "#2255dd",
                "backgroundColor": "rgba(34,85,221,0.12)",
                "borderWidth": 2.5,
                "pointRadius": 5,
                "pointBackgroundColor": "#2255dd",
                "tension": 0.35,
                "fill": True
            }])
        elif modo == "pagella":
            datasets_js = json.dumps([{
                "label": "Voto",
                "data": storico_plot["pagella"].tolist(),
                "borderColor": "#22aa66",
                "backgroundColor": "rgba(34,170,102,0.12)",
                "borderWidth": 2.5,
                "pointRadius": 5,
                "pointBackgroundColor": "#22aa66",
                "tension": 0.35,
                "fill": True
            }])
        else:  # tutte
            datasets_js = json.dumps([
                {
                    "label": "Gol",
                    "data": storico_plot["gol"].tolist(),
                    "borderColor": "#e84040",
                    "backgroundColor": "rgba(0,0,0,0)",
                    "borderWidth": 2.5,
                    "pointRadius": 4,
                    "pointBackgroundColor": "#e84040",
                    "tension": 0.35,
                    "fill": False,
                    "yAxisID": "y_goals"
                },
                {
                    "label": "Assist",
                    "data": storico_plot["assist"].tolist(),
                    "borderColor": "#2255dd",
                    "backgroundColor": "rgba(0,0,0,0)",
                    "borderWidth": 2.5,
                    "pointRadius": 4,
                    "pointBackgroundColor": "#2255dd",
                    "tension": 0.35,
                    "fill": False,
                    "yAxisID": "y_goals"
                },
                {
                    "label": "Voto",
                    "data": storico_plot["pagella"].tolist(),
                    "borderColor": "#22aa66",
                    "backgroundColor": "rgba(0,0,0,0)",
                    "borderWidth": 2.5,
                    "pointRadius": 4,
                    "pointBackgroundColor": "#22aa66",
                    "tension": 0.35,
                    "fill": False,
                    "yAxisID": "y_pagella",
                    "borderDash": [5, 3]
                }
            ])

        # ✅ FIX: scales come dict Python → json.dumps (None → null corretto)
        if modo == "tutte":
            scales_dict = {
                "x": {
                    "grid": {"color": "rgba(0,0,0,0.06)"},
                    "ticks": {"font": {"family": "Nunito", "size": 11, "weight": "700"}, "color": "#888"}
                },
                "y_goals": {
                    "type": "linear",
                    "position": "left",
                    "min": 0,
                    "grid": {"color": "rgba(0,0,0,0.06)"},
                    "ticks": {"font": {"family": "Nunito", "size": 11, "weight": "700"}, "color": "#888", "stepSize": 1}
                },
                "y_pagella": {
                    "type": "linear",
                    "position": "right",
                    "min": 0,
                    "max": 10,
                    "grid": {"drawOnChartArea": False},
                    "ticks": {"font": {"family": "Nunito", "size": 11, "weight": "700"}, "color": "#22aa66"}
                }
            }
        else:
            y_min = 5 if modo == "pagella" else 0
            y_max = 10 if modo == "pagella" else None  # None → null in JSON
            scales_dict = {
                "x": {
                    "grid": {"color": "rgba(0,0,0,0.06)"},
                    "ticks": {"font": {"family": "Nunito", "size": 11, "weight": "700"}, "color": "#888"}
                },
                "y": {
                    "min": y_min,
                    "max": y_max,
                    "grid": {"color": "rgba(0,0,0,0.06)"},
                    "ticks": {"font": {"family": "Nunito", "size": 11, "weight": "700"}, "color": "#888", "stepSize": 1}
                }
            }

        scales_js = json.dumps(scales_dict)

        plot_html = f"""<!DOCTYPE html><html>
<head>
<link href="https://fonts.googleapis.com/css2?family=Bangers&family=Nunito:wght@700;800&display=swap" rel="stylesheet"/>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>body{{margin:0;background:transparent;}} .wrap{{background:white;border:3px solid #1a1a2e;border-radius:14px;box-shadow:4px 4px 0px #1a1a2e;padding:22px 26px;}}</style>
</head><body>
<div class="wrap"><canvas id="chart" height="90"></canvas></div>
<script>
new Chart(document.getElementById('chart').getContext('2d'), {{
    type: 'line',
    data: {{ labels: {labels_js}, datasets: {datasets_js} }},
    options: {{
        responsive: true,
        interaction: {{ mode: 'index', intersect: false }},
        plugins: {{
            legend: {{ labels: {{ font: {{ family: 'Bangers', size: 14 }}, color: '#1a1a2e', usePointStyle: true }} }},
            tooltip: {{ backgroundColor: '#1a1a2e', titleFont: {{ family: 'Bangers', size: 14 }}, bodyFont: {{ family: 'Nunito', size: 12, weight: '700' }}, padding: 10, cornerRadius: 8 }}
        }},
        scales: {scales_js}
    }}
}});
</script></body></html>"""

        components.html(plot_html, height=500)