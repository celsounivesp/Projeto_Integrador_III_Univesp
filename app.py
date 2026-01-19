# -*- coding: utf-8 -*-
"""
app.py - Versão FINAL E CORRETA (Com exceção para Baldeação da Escola Petrópolis)

- A Escola Petrópolis (VOLTA-3) não é mais tratada como baldeação (FORCED OVERRIDE).
- Lógica de Desambiguação para "escola" ativada.
- CORRIGIDO: Adicionado TRIM() em AMBOS os lados do JOIN e no WHERE das consultas SQL.
- CORRIGIDO: Lógica de find_route_to_destination_smart invertida para priorizar termos.
- ATUALIZADO: Adicionados 6 novos destinos ao MAPA_DESTINOS_PONTOID.
- ATUALIZADO: Texto de erro (ERROR_NO_ROUTE_TEXT) refinado para acessibilidade.
- ATUALIZADO: Lógica "Acolhida" - "Juracy" e "Praça/Noiva" agora são flexíveis.
"""
import os
import re
import uuid
import time
import json
import asyncio
import sqlite3
from datetime import datetime, timedelta, timezone
import unicodedata 

# [LEGADO] Import do Pandas mantido para as funções legadas
import pandas as pd

import zoneinfo
from flask import Flask, render_template, url_for, jsonify, request

# TTS: edge-tts é opcional
try:
    import edge_tts
except Exception:
    edge_tts = None

# [LEGADO] Google Maps (mantido do seu original)
try:
    import googlemaps
except Exception:
    googlemaps = None

# -------------------------------------------------------------------------
# CONFIG / PATHS
# -------------------------------------------------------------------------
app = Flask(__name__, static_folder="static", template_folder="templates")
# --- Production safety: explicitly disable Flask debug mode here ---
app.config['DEBUG'] = False
import os
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', app.config.get('SECRET_KEY', 'troque-essa-chave-local'))
# --- end production safety block ---

APP_DIR = os.path.dirname(__file__)
DATABASE_PATH = os.path.join(APP_DIR, "horarios_calculados.db")
DATABASE_PATH_LEGACY = os.path.join(APP_DIR, "horarios.db") 
DATA_DIR = os.path.join(APP_DIR, "data")
TTS_DIR = os.path.join(APP_DIR, "static", "tts")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TTS_DIR, exist_ok=True)

# Timezone Brasil
BRAZIL_TZ = zoneinfo.ZoneInfo("America/Sao_Paulo")
try:
    TIME_OFFSET_MINUTES = int(os.getenv("TIME_OFFSET_MINUTES", "0"))
except Exception:
    TIME_OFFSET_MINUTES = 0

# -------------------------------------------------------------------------
# PONTOS, VOZ E TEXTOS
# -------------------------------------------------------------------------

# --- Mapeamento de Pontos (Trajeto) ---
PONTO_IDA_AVISTAR_ID = "IDA-8"
PONTO_VOLTA_AVISTAR_ID = "VOLTA-5"
PONTO_IDA_EXIBIR = "RUA SEGISFREDO PAULINO DE ALMEIDA, N° 30"
PONTO_VOLTA_EXIBIR = "AVENIDA ANTONIA PAZINATO STURION, N° 697"

# (ATUALIZADO) Mapeamento de palavras-chave com todos os 19 destinos
MAPA_DESTINOS_PONTOID = {
    # Destinos Antigos (Corrigidos para lógica Acolhida)
    "juracy": "IDA-15",
    "escola juracy": "IDA-15", # Mantém a busca por "escola juracy"
    "unimed": "IDA-7",
    "hospital": "IDA-7",
    "tpi": "IDA-1",
    "terminal": "IDA-1",
    "piracicamirim": "IDA-1",
    "cot": "IDA-2",
    "ortopedia": "IDA-2",
    "colombo": "IDA-3",
    "sachs": "IDA-4",
    "noiva": "IDA-11",
    "praça": "IDA-11", # Lógica Acolhida
    "praça noiva": "IDA-11", # Lógica Acolhida
    "mario": "IDA-14",
    "lazaro": "VOLTA-2",
    "petropolis": "VOLTA-3",
    "escola petropolis": "VOLTA-3", # Mantém a busca por "escola petropolis"
    "aldrovando": "VOLTA-4",
    "anhanguera": "VOLTA-6",
    "formar": "VOLTA-7",
    "instituto": "VOLTA-7",

    # --- 6 NOVOS DESTINOS ADICIONADOS ---
    "atacadão": "IDA-5",
    "mercedes": "IDA-6",
    "segisfredo 320": "IDA-9",
    "segisfredo 460": "IDA-10",
    "praça noiva da colina": "IDA-12", # Mantém o específico
    "eulalio": "IDA-13",
}

# (NOVO E CORRIGIDO) Mapeamento de desambiguação
DESAMBIGUACAO_MAP = {
    "escola": [
        {"nome_exibido": "Escola Juracy", "query_busca": "escola juracy"},
        {"nome_exibido": "Escola Petrópolis", "query_busca": "escola petropolis"}
    ]
}

# --- Configurações de Voz (TTS) ---
VOICE_ID = "pt-BR-FranciscaNeural"
VOICE_SPEED = "-5%"
WELCOME_TEXT = "Olá! Bem-vindo ao Trajeto Inclusivo. Toque no microfone e diga seu destino."
WELCOME_BACK_TEXT = "Bem vindo de volta. Toque no botão ao centro da tela e diga onde deseja ir."

# (VERSÃO FINAL APROVADA - Com Localização dos Botões)
ERROR_NO_ROUTE_TEXT = "Desculpe, não encontrei uma rota para este destino a partir deste ponto. Na parte inferior da tela, há duas opções. Para ligar e pedir ajuda à Pira Mobilidade, aperte o botão da esquerda. Para tentar um novo destino, aperte o botão da direita."

# --- Configurações de Contato (Fundido) ---
CONTACT_PHONE = "+551908001218484" 
CONTACT_PHONE_DISPLAY = "0800 121 8484"
CONTACT_EMAIL = "celsolinno@gmail.com" 
CONTACT_NOTE = "Se preferir, ligue para nós ou envie um e-mail. Você também pode pedir que retornemos o contato preenchendo o formulário abaixo."

# --- [LEGADO] Configs do Google Maps ---
ORIGIN_ADDRESS_LEGACY = "Av. Antonia Pazinato Sturion, 830 - Parque Santa Cecilia, Piracicaba - SP, 13420-640"
LINE_WHITELIST_LEGACY = {"203", "246"}
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()

gmaps_client = None
if GOOGLE_MAPS_API_KEY and googlemaps:
    try:
        gmaps_client = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
    except Exception as e:
        print(f"[Maps] AVISO: falhou ao iniciar cliente Google Maps:", e)
else:
    print("[WARN] GOOGLE_MAPS_API_KEY ausente ou biblioteca 'googlemaps' não instalada. Fallback online desativado.")


# Controles de Áudio (welcome)
WELCOME_AUDIO_FILENAME = "_welcome_audio.mp3"
WELCOME_AUDIO_PATH = os.path.join(TTS_DIR, WELCOME_AUDIO_FILENAME)
WELCOME_PLAYED = False
LAST_WELCOME_GENERATED = 0.0
WELCOME_DEBOUNCE_SECONDS = 1.0

# -------------------------------------------------------------------------
# UTILITÁRIOS de texto/hora
# -------------------------------------------------------------------------
def _strip_accents(s: str) -> str:
    if not s: return ""
    s = str(s)
    s = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch))

def _norm_text(s: str) -> str:
    if not s: return ""
    s2 = _strip_accents(s).lower().strip()
    s2 = re.sub(r"[\s_/\\\-]+", " ", s2)
    return s2

def _to_time(hhmmss: str):
    from datetime import datetime
    return datetime.strptime(hhmmss, "%H:%M:%S").time()

def _now_brazil() -> datetime:
    return datetime.now(BRAZIL_TZ) + timedelta(minutes=TIME_OFFSET_MINUTES)

def _time_to_minutes_until(hhmmss: str, now: datetime = None) -> int:
    try:
        if now is None:
            now = _now_brazil()
        elif now.tzinfo is None:
            now = now.replace(tzinfo=BRAZIL_TZ)
            
        assert now is not None, "now não deveria ser None aqui" # Para o Pylance
            
        alvo_naive = datetime.combine(now.date(), _to_time(hhmmss))
        alvo = alvo_naive.replace(tzinfo=now.tzinfo)
        
        if alvo <= now:
            alvo += timedelta(days=1)
            
        mins = int(round((alvo - now).total_seconds() / 60.0))
        return mins
    except Exception as e:
        print(f"[TIMER] erro ao calcular tempo para '{hhmmss}': {e}")
        return 10**9

# -------------------------------------------------------------------------
# [LEGADO] DATABASE BUILD (Mantido 100% para referência futura)
# -------------------------------------------------------------------------
# AVISO: O CÓDIGO ABAIXO NÃO É MAIS USADO PELO APP.
# O app agora depende do 'horarios_calculados.db'
# e do script 'gerar_banco.py'.

def _normalize_time_to_hhmmss_LEGACY(val):
    if pd.isna(val): return None
    s = str(val).strip()
    if not s: return None
    m = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$", s)
    if m:
        h, mi, ss = int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)
        return f"{h:02d}:{mi:02d}:{ss:02d}"
    try:
        f = float(s.replace(",", "."))
        if f >= 1: return f"{int(f):02d}:00:00"
        secs = int(round(f * 24 * 3600))
        h, m_rem = divmod(secs, 3600)
        m2, s2 = divmod(m_rem, 60)
        return f"{h % 24:02d}:{m2:02d}:{s2:02d}"
    except Exception:
        return None

def _list_csv_candidates_LEGACY():
    try:
        files = [os.path.join(DATA_DIR, f) for f in os.listdir(DATA_DIR) if f.lower().endswith(".csv")]
        files.sort()
        return files
    except Exception as e:
        print(f"[DB Build Legado] Erro ao listar CSVs: {e}")
        return []

def _read_csv_robusto_LEGACY(path):
    encs = ["utf-8", "utf-8-sig", "latin-1"]
    for enc in encs:
        try:
            df = pd.read_csv(path, sep=None, engine="python", encoding=enc, dtype=str)
            if not df.empty:
                print(f"[DB Build Legado] Lido {os.path.basename(path)} (encoding={enc}, auto-sep). Linhas: {len(df)}")
                return df
        except Exception as e:
            pass
    raise RuntimeError(f"Falha ao ler {path}.")

def _pick_col_csv_LEGACY(headers, candidates):
    if headers is None: return None
    headers = list(headers)
    if not headers: return None
    norm_map = {_norm_text(h): h for h in headers}
    for cand in candidates:
        nc = _norm_text(cand)
        if nc in norm_map: return norm_map[nc]
    for h in headers:
        nh = _norm_text(h)
        for cand in candidates:
            if _norm_text(cand) in nh: return h
    return None

def build_database_from_csvs_LEGACY():
    print("[DB Build Legado] Criando banco de dados a partir de CSVs...")
    CSV_SOURCES = _list_csv_candidates_LEGACY()
    if not CSV_SOURCES:
        print(f"[DB Build Legado] AVISO: Nenhum CSV encontrado em {DATA_DIR}. O banco de dados ficara vazio.")
        print(f"                 Por favor, coloque seus arquivos .csv na pasta 'data'.")

    rows = []
    for path in CSV_SOURCES:
        try:
            df = _read_csv_robusto_LEGACY(path)
            col_ponto = _pick_col_csv_LEGACY(df.columns, ["PontoReferencia", "Ponto", "Parada", "Referencia", "Local"])
            col_hora = _pick_col_csv_LEGACY(df.columns, ["Horario", "Hora", "Saida", "Partida", "Time"])
            col_dia = _pick_col_csv_LEGACY(df.columns, ["Dia", "Calendario", "Tipo de dia", "Tipo"])
            col_sentido = _pick_col_csv_LEGACY(df.columns, ["Sentido", "Trajeto", "Destino", "Direcao"])
            col_linha = _pick_col_csv_LEGACY(df.columns, ["Linha", "Codigo", "Cód Linha", "Route"])

            if not col_ponto or not col_hora:
                print(f"[DB Build Legado] Ignorando {path}: faltam colunas mínimas (Ponto/Horário).")
                continue

            for _, r in df.iterrows():
                ponto_raw = (r.get(col_ponto, "") if col_ponto else "").strip()
                if not ponto_raw: continue
                horario = _normalize_time_to_hhmmss_LEGACY(r.get(col_hora))
                if not horario: continue
                
                dia_raw = (r.get(col_dia, "") if col_dia else "").strip() or "util"
                sentido_raw = (r.get(col_sentido, "") if col_sentido else "").strip()
                linha_raw = (r.get(col_linha, "") if col_linha else "203").strip()
                
                rows.append((
                    linha_raw, ponto_raw, dia_raw, horario, sentido_raw,
                    _norm_text(ponto_raw), _norm_text(dia_raw), _norm_text(sentido_raw)
                ))
        except Exception as e:
            print(f"[DB Build Legado] Falhou ler CSV {path}: {e}")
            continue

    if os.path.exists(DATABASE_PATH_LEGACY):
        os.remove(DATABASE_PATH_LEGACY)
        
    conn = sqlite3.connect(DATABASE_PATH_LEGACY)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE horarios(
            Linha TEXT,
            PontoReferencia TEXT,
            Dia TEXT,
            Horario TEXT,
            Sentido TEXT,
            PontoNorm TEXT,
            DiaNorm TEXT,
            SentidoNorm TEXT
        )
    """)
    if rows:
        cur.executemany("INSERT INTO horarios VALUES (?,?,?,?,?,?,?,?)", rows)
        cur.execute("CREATE INDEX idx_pontonorm ON horarios(PontoNorm)")
        print(f"[DB Build Legado] OK. {len(rows)} registros salvos em {DATABASE_PATH_LEGACY}")
    else:
        print("[DB Build Legado] AVISO: Banco de dados criado, mas esta vazio.")
    
    conn.commit()
    conn.close()

# -------------------------------------------------------------------------
# NOVA FUNÇÃO DE SETUP
# -------------------------------------------------------------------------
def setup_database():
    """
    Verifica se o novo banco de dados ('horarios_calculados.db') existe.
    Se não existir, avisa o usuário para rodar 'gerar_banco.py'.
    """
    if not os.path.exists(DATABASE_PATH):
        print("=" * 70)
        print(f"ERRO CRÍTICO: Banco de dados '{DATABASE_PATH}' não encontrado.")
        print("Por favor, execute o script 'python gerar_banco.py' primeiro.")
        print("Este script é necessário para calcular todos os horários dos pontos.")
        print("=" * 70)
    else:
        print(f"Sucesso: Banco de dados '{DATABASE_PATH}' encontrado e pronto para uso.")

# -------------------------------------------------------------------------
# [LEGADO] ROTAS E REGRAS (Mantido 100% para referência futura)
# -------------------------------------------------------------------------
# O código abaixo é a lógica ANTIGA, que causava os erros.
# Não é mais usado, mas está aqui para consulta.

def _get_norm_map_LEGACY(nomes_pontos):
    return { _norm_text(nome): i+1 for i, nome in enumerate(nomes_pontos) }

ROTA_IDA_PONTOS_LEGACY = [
    "TPI - TERMINAL PIRACAMIRIM", "COT - CENTRO DE ORTOPEDIA E TRAUMATOLOGIA",
    "CENTRO CULTURAL E RECREATIVO CRISTOVÃO COLOMBO", "AVENIDA PROFESSOR ALBERTO VOLLET SACHS",
    "AVENIDA CÁSSIO PASCHOAL PADOVANI", "AVENIDA CÁSSIO PASCHOAL PADOVANI",
    "HOSPITAL UNIMED", "RUA SEGISFREDO PAULINO DE ALMEIDA",
    "RUA SEGISFREDO PAULINO DE ALMEIDA", "RUA SEGISFREDO PAULINO DE ALMEIDA",
    "PRAÇA NOIVA DA COLINA", "PRAÇA NOIVA DA COLINA",
    "RUA PROFESSOR EULÁLIO DE ARRUDA MELLO", "RUA MÁRIO SOARES DE BARROS",
    "EE JURACY NEVES DE M FERRACIU"
]
ROTA_IDA_ORDEM_LEGACY = _get_norm_map_LEGACY(ROTA_IDA_PONTOS_LEGACY)

ROTA_VOLTA_PONTOS_LEGACY = [
    "ESCOLA JURACY NELLO FERRACIU", "RUA LÁZARO GOMES DA CRUZ",
    "ESCOLA MUNICIPAL DO JARDIM PETRÓPOLIS", "RUA ALDROVANDO FLEURI PIRES CORRÊA-ÁREA VERDE",
    "AVENIDA ANTONIA PAZINATO STURION", "RUA ANHANGUERA",
    "INSTITUTO FORMAR", "TPI - TERMINAL PIRACAMIRIM"
]
ROTA_VOLTA_ORDEM_LEGACY = _get_norm_map_LEGACY(ROTA_VOLTA_PONTOS_LEGACY)

PONTO_IDA_BUSCA_LEGACY = "RUA SEGISFREDO PAULINO DE ALMEIDA"
PONTO_VOLTA_BUSCA_LEGACY = "AVENIDA ANTONIA PAZINATO STURION"

NORMA_PONTO_IDA_BUSCA_LEGACY = _norm_text(PONTO_IDA_BUSCA_LEGACY)
NORMA_PONTO_VOLTA_BUSCA_LEGACY = _norm_text(PONTO_VOLTA_BUSCA_LEGACY)

ORDEM_PONTO_IDA_LEGACY = 8
ORDEM_PONTO_VOLTA_LEGACY = 5

PALAVRAS_CHAVE_DESTINOS_LEGACY = {
    "escola": "juracy", "juracy": "juracy", "unimed": "unimed", "hospital": "unimed",
    "tpi": "tpi", "terminal": "tpi", "piracicamirim": "tpi", "cot": "cot",
    "ortopedia": "cot", "colombo": "colombo", "sachs": "sachs", "cassio": "cassio",
    "noiva": "noiva", "mario": "mario", "lazaro": "lazaro", "petropolis": "petropolis",
    "aldrovando": "aldrovando", "anhanguera": "anhanguera", "formar": "formar",
    "instituto": "formar",
}

def find_route_to_destination_smart_LEGACY(destination_query: str): pass
def get_bus_directions_preferring_lines_LEGACY(gmaps_client, origin, destination, preferred_lines=LINE_WHITELIST_LEGACY): pass
def db_count_for_point_LEGACY(ponto_ref: str) -> int: pass
# ---------------------------------------------------------------------------
# FIM DA SEÇÃO LEGADA
# ---------------------------------------------------------------------------


# -------------------------------------------------------------------------
# ROTAS E REGRAS (LÓGICA NOVA E ATUALIZADA)
# -------------------------------------------------------------------------

# (MODIFICADO E CORRIGIDO) find_route_to_destination_smart
def find_route_to_destination_smart(destination_query: str):
    """
    Decide qual ponto de PARTIDA (Avistar Ida ou Volta) usar
    e se a rota é direta ou requer baldeação.
    
    LÓGICA CORRIGIDA:
    1. Primeiro, procura por termos específicos (ex: "escola juracy").
    2. Se não encontrar, procura por termos gerais no mapa (ex: "unimed").
    """
    if not destination_query:
        return None, None, None
    q_norm = _norm_text(destination_query)

    target_ponto_id = None

    # --- INÍCIO DA LÓGICA CORRIGIDA ---

    # 1. (NOVO) Primeiro, checa se é uma busca específica de "escola"
    if "escola" in q_norm:
        for opt in DESAMBIGUACAO_MAP["escola"]:
            if opt['query_busca'] in q_norm: # ex: "juracy" está em "escola juracy"
                # Verifica se a chave realmente existe no mapa principal
                if opt['query_busca'] in MAPA_DESTINOS_PONTOID:
                    target_ponto_id = MAPA_DESTINOS_PONTOID[opt['query_busca']] # Pega "IDA-15"
                    break
    
    # 2. (ANTIGO Passo 1) Se não achou (ou não era "escola"), procura no mapa geral
    if not target_ponto_id:
        # Lógica de busca por palavra-chave mais longa primeiro, para evitar o "break" errado
        # Ex: "terminal piracicamirim" (3 palavras) deve ser checado antes de "terminal" (1 palavra)
        
        # Classifica as chaves pelo comprimento, da mais longa para a mais curta
        palavras_ordenadas = sorted(MAPA_DESTINOS_PONTOID.keys(), key=len, reverse=True)
        
        for palavra in palavras_ordenadas:
            if palavra in q_norm:
                target_ponto_id = MAPA_DESTINOS_PONTOID[palavra]
                break # Agora o break é seguro, pois encontramos a correspondência mais longa primeiro
            
    # 3. Se ainda não achou, não há rota
    if not target_ponto_id:
        return None, None, None # Destino não mapeado

    # --- FIM DA LÓGICA CORRIGIDA ---

    # O resto da sua lógica de roteamento (que está correta)
    target_sentido = "IDA" if target_ponto_id.startswith("IDA") else "VOLTA"
    target_ordem = int(target_ponto_id.split('-')[1])
    
    avistar_ida_ordem = int(PONTO_IDA_AVISTAR_ID.split('-')[1]) # 8
    avistar_volta_ordem = int(PONTO_VOLTA_AVISTAR_ID.split('-')[1]) # 5

    # (CORREÇÃO CIRÚRGICA) OVERRIDE: Escola Petrópolis (VOLTA-3) não é baldeação.
    if target_ponto_id == "VOLTA-3":
        return PONTO_IDA_AVISTAR_ID, "DIRETA_IDA", target_ponto_id 

    # Lógica de Rota (sem mudança)
    if target_sentido == "IDA":
        if target_ordem < avistar_ida_ordem:
            return PONTO_VOLTA_AVISTAR_ID, "BALDEACAO_IDA", target_ponto_id
        else:
            return PONTO_IDA_AVISTAR_ID, "DIRETA_IDA", target_ponto_id
    else:
        if target_ordem < avistar_volta_ordem:
             return PONTO_IDA_AVISTAR_ID, "BALDEACAO_VOLTA", target_ponto_id
        else:
            return PONTO_VOLTA_AVISTAR_ID, "DIRETA_VOLTA", target_ponto_id
            
    return None, None, None

# -------------------------------------------------------------------------
# CONSULTA COM ETA (LÓGICA NOVA)
# -------------------------------------------------------------------------

def get_dia_semana(now: datetime):
    """Retorna 'DU', 'SAB' ou 'DOM'."""
    weekday = now.weekday()
    if weekday == 5: return "SAB"
    if weekday == 6: return "DOM"
    return "DU"

def query_proximas_por_sentido_com_eta(ponto_id: str):
    """Busca o próximo horário de chegada para um PONTOID específico."""
    if not ponto_id: return []
    if not os.path.exists(DATABASE_PATH): return []

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row 
    cur = conn.cursor()
    
    now = _now_brazil()
    now_time_str = now.strftime('%H:%M:%S')
    dia_semana_hoje = get_dia_semana(now)

    # 1. Tenta encontrar o próximo ônibus HOJE
    # (CORREÇÃO DEFINITIVA) Adiciona TRIM() em AMBOS os lados do JOIN e no WHERE
    cur.execute(
        """
        SELECT G.*, P.NomePonto, P.Sentido 
        FROM HorariosGerados G
        JOIN Pontos P ON TRIM(G.PontoID) = TRIM(P.PontoID)
        WHERE TRIM(G.PontoID) = ? AND G.DiaSemana = ? AND time(G.HorarioChegadaEstimada) > time(?)
        ORDER BY time(G.HorarioChegadaEstimada)
        LIMIT 1
        """,
        (ponto_id, dia_semana_hoje, now_time_str)
    )
    row = cur.fetchone()
    
    horario_chegada = None

    if row:
        horario_chegada = row["HorarioChegadaEstimada"]
    else:
        # 2. Se não há mais ônibus hoje, busca o primeiro de AMANHÃ
        amanha = now + timedelta(days=1)
        dia_semana_amanha = get_dia_semana(amanha)
        
        # (CORREÇÃO DEFINITIVA) Adiciona TRIM() em AMBOS os lados do JOIN e no WHERE
        cur.execute(
            """
            SELECT G.*, P.NomePonto, P.Sentido
            FROM HorariosGerados G
            JOIN Pontos P ON TRIM(G.PontoID) = TRIM(P.PontoID)
            WHERE TRIM(G.PontoID) = ? AND G.DiaSemana = ?
            ORDER BY time(G.HorarioChegadaEstimada)
            LIMIT 1
            """,
            (ponto_id, dia_semana_amanha)
        )
        row = cur.fetchone()
        if row:
            horario_chegada = row["HorarioChegadaEstimada"]

    conn.close()

    if not row or not horario_chegada:
        return [] # Não encontrou

    eta_min = _time_to_minutes_until(horario_chegada, now)
    
    return [{
        "sentido_raw": row["Sentido"], "linha": row["Linha"],
        "horario": horario_chegada[:5], "ponto_nome": row["NomePonto"],
        "ponto_id": ponto_id, "eta_min": eta_min,
    }]

# -------------------------------------------------------------------------
# TTS helpers (Nova lógica de loop asyncio)
# -------------------------------------------------------------------------
async def _speak_to_file_async(text: str, out_path: str):
    if edge_tts is None:
        raise RuntimeError("edge-tts não disponível")
    comm = edge_tts.Communicate(text, VOICE_ID, rate=VOICE_SPEED)
    await comm.save(out_path)

def tts_make(text: str) -> str:
    """Gera um arquivo MP3 e devolve a URL estática."""
    if not text:
        return ""
    if edge_tts is None:
        print("[TTS] edge-tts ausente; tts_make retornará string vazia.")
        return ""
    name = f"tts_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}.mp3"
    out_path = os.path.join(TTS_DIR, name)
    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        loop.run_until_complete(_speak_to_file_async(text, out_path))
    except Exception as e:
        print(f"[TTS] falhou: {e}")
        return ""
    
    if os.path.exists(out_path):
        return url_for("static", filename=f"tts/{name}")
    return ""

def get_or_create_welcome_audio(welcome_text_to_speak):
    global LAST_WELCOME_GENERATED
    LAST_WELCOME_GENERATED = time.time()
    if os.path.exists(WELCOME_AUDIO_PATH):
        return url_for("static", filename=f"tts/{WELCOME_AUDIO_FILENAME}")
    
    new_url = tts_make(welcome_text_to_speak)
    if new_url:
        try:
            tts_filename = new_url.split('/')[-1]
            os.rename(os.path.join(TTS_DIR, tts_filename), WELCOME_AUDIO_PATH)
            return url_for("static", filename=f"tts/{WELCOME_AUDIO_FILENAME}")
        except Exception as e:
            print(f"[TTS] Falha ao renomear cache de welcome: {e}")
            return new_url 
    return ""


# -------------------------------------------------------------------------
# ROTAS FLASK (Principais)
# -------------------------------------------------------------------------
@app.get("/")
def index():
    tts_url = get_or_create_welcome_audio(WELCOME_TEXT)
    return render_template("index_layout.html", tts_url=tts_url or "")

@app.post("/reset_welcome")
def reset_welcome():
    global WELCOME_PLAYED
    WELCOME_PLAYED = False
    return jsonify({"ok": True}), 200

# -------------------------------------------------------------------------
# ROTA /buscar (ATUALIZADA com Desambiguação)
# -------------------------------------------------------------------------
@app.route("/buscar", methods=["POST"])
def buscar():
    data = request.get_json(silent=True) or request.form or {}
    q = (data.get("q") or "").strip()
    if not q:
        tts_url = tts_make("Nenhum destino informado. Toque no microfone e fale o nome do destino.")
        return jsonify({"ok": False, "msg": "Nenhum destino informado.", "tts_url": tts_url}), 400

    q_norm = _norm_text(q)

    # (NOVO) Checagem de Desambiguação
    # Se o usuário falou SÓ "escola" (e não "escola juracy", etc.)
    palavra_ambigua_encontrada = None
    if len(q_norm.split()) <= 2: # Evita pegar "minha escola"
        for key in DESAMBIGUACAO_MAP.keys():
            if key == q_norm:
                palavra_ambigua_encontrada = key
                break
    
    if palavra_ambigua_encontrada:
        options = DESAMBIGUACAO_MAP[palavra_ambigua_encontrada]
        tts_text = f"Encontrei {len(options)} opções. Você quis dizer "
        tts_text += " ou ".join([opt['nome_exibido'] for opt in options]) + "?"
        
        tts_url = tts_make(tts_text)
        return jsonify({
            "ok": True,
            "needs_desambiguation": True, # Flag para o frontend
            "tts_url": tts_url,
            "options": options # Envia as opções (não usado, mas pode ser útil)
        }), 200
    
    # --- Fim da Checagem de Desambiguação ---

    # 1. Tenta a nova lógica de roteamento
    ponto_partida_id, tipo_rota, destino_ponto_id = find_route_to_destination_smart(q)

    if ponto_partida_id:
        # 2. Busca o próximo ônibus (nova lógica)
        picks = query_proximas_por_sentido_com_eta(ponto_partida_id)
        
        if picks:
            it = picks[0]
            
            # Pega o nome real do destino final (nova lógica)
            conn_dest = sqlite3.connect(DATABASE_PATH)
            conn_dest.row_factory = sqlite3.Row
            cur_dest = conn_dest.cursor()
            
            # (CORREÇÃO DEFINITIVA) Adiciona TRIM() na busca do nome do destino
            cur_dest.execute("SELECT NomePonto FROM Pontos WHERE TRIM(PontoID) = ?", (destino_ponto_id,))
            dest_info = cur_dest.fetchone()
            destino_real = dest_info["NomePonto"] if dest_info else q
            conn_dest.close()

            # 3. Monta a fala (nova lógica)
            if tipo_rota == "DIRETA_IDA":
                card_ponto = PONTO_IDA_EXIBIR
                card_sentido = "Sentido Jardim Noiva da Colina"
                fala_texto = f"Para {destino_real}, o próximo ônibus é o {card_sentido}, linha {it['linha']}, que chega em {it['eta_min']} minutos no ponto {card_ponto}."
            elif tipo_rota == "DIRETA_VOLTA":
                card_ponto = PONTO_VOLTA_EXIBIR
                card_sentido = "Sentido Terminal Piracicamirim"
                fala_texto = f"Para {destino_real}, o próximo ônibus é o {card_sentido}, linha {it['linha']}, que chega em {it['eta_min']} minutos no ponto {card_ponto}."
            elif tipo_rota == "BALDEACAO_IDA":
                card_ponto = PONTO_VOLTA_EXIBIR
                card_sentido = "Sentido Terminal Piracicamirim"
                fala_texto = f"Para {destino_real}, você precisa fazer baldeação. O próximo ônibus para o {card_sentido} sai do ponto {card_ponto} em {it['eta_min']} minutos. Desça no terminal e pegue o ônibus sentido Jardim Noiva da Colina."
            else: # BALDEACAO_VOLTA
                card_ponto = PONTO_IDA_EXIBIR
                card_sentido = "Sentido Jardim Noiva da Colina"
                fala_texto = f"Para {destino_real}, você precisa fazer baldeação. O próximo ônibus para o {card_sentido} sai do ponto {card_ponto} em {it['eta_min']} minutos."

            cards = [{"idx": 1, "sentido": card_sentido, "linha": it["linha"],
                      "horario": it["horario"], "eta": it["eta_min"],
                      "ponto": card_ponto, "destino": destino_real}]
            tts_url = tts_make(fala_texto.replace("N°", "número"))
            return jsonify({"ok": True, "fonte": "LOCAL", "tts_url": tts_url, "cards": cards}), 200

    # --- (NOVA LÓGICA DE ERRO) ---
    tts_url = tts_make(ERROR_NO_ROUTE_TEXT)
    return jsonify({
        "ok": False, 
        "msg": "Não há linha possível para o endereço solicitado a partir deste ponto.", 
        "tts_url": tts_url,
        "show_call_button": True # Nova flag para o frontend
    }), 200 # Retornamos 200 OK para o fetch tratar a resposta JSON

# -------------------------------------------------------------------------
# (NOVO) ROTAS DE CONTATO E ÁUDIO
# -------------------------------------------------------------------------

@app.get("/api/tts/welcome_back")
def api_tts_welcome_back():
    """Gera o áudio de 'bem-vindo de volta'."""
    tts_url = tts_make(WELCOME_BACK_TEXT)
    return jsonify({"ok": True, "tts_url": tts_url})

@app.get("/api/contato_info")
def api_contato_info():
    """Esta rota não é mais usada ativamente pelo JS, mas é mantida."""
    return jsonify({
        "phone": CONTACT_PHONE,
        "phone_display": CONTACT_PHONE_DISPLAY,
        "email": CONTACT_EMAIL,
        "note": CONTACT_NOTE
    })

@app.route("/api/request_contact", methods=["POST"])
def api_request_contact():
    """(CORRIGIDO) Recebe pedido de contato do SEU formulário."""
    try:
        payload = request.get_json(silent=True) or {}
    except Exception:
        payload = {}

    name = (payload.get("name") or "").strip()
    ddd = (payload.get("ddd") or "").strip()
    phone = (payload.get("phone") or "").strip()
    email = (payload.get("email") or "").strip()
    message = (payload.get("message") or "").strip()

    if not name or not ddd or not phone or not email or not message:
        return jsonify({"ok": False, "msg": "Todos os campos são obrigatórios."}), 400
    
    if len(ddd) != 2 or not ddd.isdigit():
        return jsonify({"ok": False, "msg": "DDD inválido."}), 400
        
    if len(phone) < 8 or not phone.isdigit():
        return jsonify({"ok": False, "msg": "Telefone inválido."}), 400

    received = {
        "ts": datetime.now().isoformat(),
        "name": name, 
        "phone_full": f"({ddd}) {phone}", 
        "email": email,
        "message": message
    }
    print("[Contato] Pedido recebido:", json.dumps(received, ensure_ascii=False))

    return jsonify({"ok": True, "msg": "Mensagem recebida. Obrigado pelo seu contato."}), 200

# -------------------------------------------------------------------------
# DEBUG endpoints (Atualizados para o novo DB)
# -------------------------------------------------------------------------
@app.get("/api/db_check")
def api_db_check():
    """Verifica o banco de dados NOVO (horarios_calculados.db)"""
    path = DATABASE_PATH
    exists = os.path.exists(path.strip())
    info = {"exists": exists, "path": path, "rows_pontos": 0, "rows_horarios": 0, "error": ""}
    if exists:
        try:
            conn = sqlite3.connect(path)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM Pontos")
            info["rows_pontos"] = int(cur.fetchone()[0])
            cur.execute("SELECT COUNT(*) FROM HorariosGerados")
            info["rows_horarios"] = int(cur.fetchone()[0])
            conn.close()
        except Exception as e:
            info["error"] = str(e)
    else:
        info["error"] = f"'{DATABASE_PATH}' não encontrado. Execute 'python gerar_banco.py'."
    return jsonify(info)

@app.get("/debug_time")
def debug_time():
    now = _now_brazil()
    return jsonify({
        "utc_now_iso": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(),
        "brazil_now_iso": now.isoformat(),
        "dia_semana_calculado": get_dia_semana(now),
        "TIME_OFFSET_MINUTES": TIME_OFFSET_MINUTES
    })

@app.get("/dump_point")
def dump_point():
    """Busca horários no NOVO banco de dados"""
    p = (request.args.get("p") or "").strip().upper()
    if not p:
        return jsonify({"ok": False, "msg": "forneça ?p=<PontoID> (ex: IDA-8 ou VOLTA-5)"}), 400
    if not (p.startswith("IDA-") or p.startswith("VOLTA-")):
         return jsonify({"ok": False, "msg": "PontoID deve ser no formato IDA-X ou VOLTA-X"}), 400
    if not os.path.exists(DATABASE_PATH):
        return jsonify({"ok": False, "msg": "DB '{DATABASE_PATH}' não existe."}), 500

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # (CORREÇÃO DEFINITIVA) Adiciona TRIM() na busca de debug
    cur.execute("SELECT * FROM HorariosGerados WHERE TRIM(PontoID) = ? ORDER BY DiaSemana, time(HorarioChegadaEstimada)", (p,))
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    
    now = _now_brazil()
    proximo = query_proximas_por_sentido_com_eta(p)
    
    return jsonify({
        "ok": True, 
        "query_ponto_id": p, 
        "now": now.isoformat(), 
        "proximo_onibus_calculado": proximo[0] if proximo else "Nenhum ônibus encontrado",
        "total_horarios_para_este_ponto": len(rows),
        "todos_horarios": rows
    }), 200
    
# -------------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------------
if __name__ == "__main__":
    # Verifica/cria DB se necessário (só logs)
    setup_database()
    # Usa porta do ambiente quando disponível (ex.: Render fornece \)
    import os
    port = int(os.environ.get("PORT", 8000))
    # NÃO habilite debug em produção — mantenha debug=False
    app.run(host="0.0.0.0", port=port, debug=False)
