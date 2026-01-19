# Salve este arquivo como: gerar_banco.py
# Execute-o UMA VEZ com: python gerar_banco.py

import sqlite3
import os
from datetime import datetime, timedelta
# --- constante de fallback inserida automaticamente ---
globals().get("LINE_WHITELIST_LEGACY", []) = []  # lista vazia por padrão
# -----------------------------------------------


# --- 1. CONFIGURAÃ‡Ã•ES PRINCIPAIS ---

DB_NAME = "horarios_calculados.db"
LINHA_COD = "203"

# Intervalos (em segundos)
BASE_INTERVALO_S = 150  # 2 minutos e 30 segundos
PICO_ACRESCIMO = 0.30   # +30%
INTER_ACRESCIMO = 0.10  # +10%

# Pontos de Ã”nibus (Nomes e Ordem)
PONTOS_IDA = [
    "TPI - TERMINAL PIRACICAMIRIM",
    "COT - CENTRO DE ORTOPEDIA E TRAUMATOLOGIA",
    "CENTRO CULTURAL E RECREATIVO CRISTOVÃƒO COLOMBO",
    "AVENIDA PROFESSOR ALBERTO VOLLET SACHS",
    "AVENIDA CÃSSIO PASCHOAL PADOVANI",  # Ponto 5
    "AVENIDA CÃSSIO PASCHOAL PADOVANI",
    "HOSPITAL UNIMED",
    "RUA SEGISFREDO PAULINO DE ALMEIDA",  # Ponto 8 (ReferÃªncia Avistar Ida)
    "RUA SEGISFREDO PAULINO DE ALMEIDA",
    "RUA SEGISFREDO PAULINO DE ALMEIDA",
    "PRAÃ‡A NOIVA DA COLINA",
    "PRAÃ‡A NOIVA DA COLINA",
    "RUA PROFESSOR EULÃLIO DE ARRUDA MELLO",
    "RUA MÃRIO SOARES DE BARROS",
    "ESCOLA JURACY NEVES DE MELLO FERRACIU" # Ponto 15 (Final Ida)
]

PONTOS_VOLTA = [
    "ESCOLA JURACY NEVES DE MELLO FERRACIU", # Ponto 1 (InÃ­cio Volta)
    "RUA LÃZARO GOMES DA CRUZ",
    "ESCOLA MUNICIPAL DO JARDIM PETRÃ“POLIS",
    "RUA ALDROVANDO FLEURI PIRES CORRÃŠA-ÃREA VERDE",
    "AVENIDA ANTONIA PAZINATO STURION",  # Ponto 5 (ReferÃªncia Avistar Volta)
    "RUA ANHANGUERA",
    "INSTITUTO FORMAR",
    "TPI - TERMINAL PIRACICAMIRIM" # Ponto 8 (Final Volta)
]

# HorÃ¡rios de Partida (Baseado nos PDFs)
PARTIDAS_IDA = {
    "DU": ["05:10", "05:40", "06:10", "06:40", "07:10", "07:45", "08:15", "09:50", "10:20", "10:50", "11:20", "11:50", "12:20", "12:50", "13:20", "13:50", "14:25", "14:55", "15:25", "15:55", "16:25", "16:57", "17:29", "18:01", "18:33", "19:05", "20:30", "21:00", "21:30", "22:00", "22:40", "23:10", "23:40"],
    "SAB": ["06:25", "07:55", "10:25", "11:55", "13:25", "14:55", "16:25", "17:55", "19:25", "22:00"],
    "DOM": ["06:25", "07:55", "10:25", "11:55", "13:25", "14:55", "16:25", "17:55", "19:25", "22:00"]
}

PARTIDAS_VOLTA = {
    "DU": ["04:55", "05:25", "05:55", "06:25", "06:55", "07:30", "08:00", "08:30", "10:05", "10:35", "11:05", "11:35", "12:05", "12:35", "13:05", "13:35", "14:05", "14:40", "15:10", "15:40", "16:10", "16:42", "17:14", "17:46", "18:18", "18:49", "19:20", "20:45", "21:15", "21:45", "22:20", "22:55", "23:25"],
    "SAB": ["04:55", "06:40", "08:10", "10:40", "12:10", "13:40", "15:10", "16:40", "18:10", "19:40", "22:15"],
    "DOM": ["04:55", "06:40", "08:10", "10:40", "12:10", "13:40", "15:10", "16:40", "18:10", "19:40", "22:15"]
}


# --- 2. LÃ“GICA DE CÃLCULO DE HORÃRIO ---

def parse_time(time_str):
    """Converte 'HH:MM' para um objeto time."""
    try:
        return datetime.strptime(time_str, '%H:%M').time()
    except ValueError:
        # Tenta corrigir horÃ¡rios como '18:18' (do PDF) que podem nÃ£o ter 2 dÃ­gitos
        parts = time_str.split(':')
        if len(parts) == 2:
            return datetime.strptime(f"{int(parts[0]):02d}:{int(parts[1]):02d}", '%H:%M').time()
    return None


def get_intervalo_segundos(horario_atual, dia_semana):
    """Calcula o intervalo (150s, 165s ou 195s) baseado nas regras."""
    
    time_atual = horario_atual.time()
    
    if dia_semana == "DOM":
        return BASE_INTERVALO_S # Domingo Ã© sempre normal

    # Regras de SÃ¡bado
    if dia_semana == "SAB":
        # Pico ManhÃ£ (06:30 - 09:00)
        if (parse_time("06:30") <= time_atual <= parse_time("09:00")):
            return round(BASE_INTERVALO_S * (1 + PICO_ACRESCIMO))
        # IntermediÃ¡rio AlmoÃ§o (11:00 - 13:00)
        if (parse_time("11:00") <= time_atual <= parse_time("13:00")):
            return round(BASE_INTERVALO_S * (1 + INTER_ACRESCIMO))
        return BASE_INTERVALO_S # Normal

    # Regras de Dia Ãštil (DU)
    if dia_semana == "DU":
        # Pico ManhÃ£ (06:30 - 09:00)
        if (parse_time("06:30") <= time_atual <= parse_time("09:00")):
            return round(BASE_INTERVALO_S * (1 + PICO_ACRESCIMO))
        # IntermediÃ¡rio AlmoÃ§o (11:00 - 13:00)
        if (parse_time("11:00") <= time_atual <= parse_time("13:00")):
            return round(BASE_INTERVALO_S * (1 + INTER_ACRESCIMO))
        # Pico Tarde (16:30 - 19:00)
        if (parse_time("16:30") <= time_atual <= parse_time("19:00")):
            return round(BASE_INTERVALO_S * (1 + PICO_ACRESCIMO))
        return BASE_INTERVALO_S # Normal

    return BASE_INTERVALO_S


def criar_banco():
    """FunÃ§Ã£o principal para criar e popular o banco de dados."""
    
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
        print(f"Banco de dados '{DB_NAME}' antigo removido.")

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    print("Criando tabelas 'Pontos' e 'HorariosGerados'...")
    
    # Tabela 1: Cadastro dos Pontos
    cur.execute("""
    CREATE TABLE IF NOT EXISTS Pontos (
        PontoID TEXT PRIMARY KEY,
        Sentido TEXT NOT NULL,
        Ordem INTEGER NOT NULL,
        NomePonto TEXT NOT NULL
    )
    """)

    # Tabela 2: Todos os horÃ¡rios calculados
    cur.execute("""
    CREATE TABLE IF NOT EXISTS HorariosGerados (
        HorarioID INTEGER PRIMARY KEY AUTOINCREMENT,
        PontoID TEXT NOT NULL,
        DiaSemana TEXT NOT NULL,
        Linha TEXT NOT NULL,
        HorarioPartida TEXT NOT NULL,
        HorarioChegadaEstimada TEXT NOT NULL,
        FOREIGN KEY (PontoID) REFERENCES Pontos (PontoID)
    )
    """)

    # Popular tabela 'Pontos'
    print("Populando tabela 'Pontos'...")
    pontos_para_inserir = []
    
    # Pontos de IDA
    for i, nome in enumerate(PONTOS_IDA):
        ordem = i + 1
        ponto_id = f"IDA-{ordem}"
        pontos_para_inserir.append((ponto_id, "IDA", ordem, nome))

    # Pontos de VOLTA
    for i, nome in enumerate(PONTOS_VOLTA):
        ordem = i + 1
        ponto_id = f"VOLTA-{ordem}"
        pontos_para_inserir.append((ponto_id, "VOLTA", ordem, nome))

    cur.executemany("INSERT INTO Pontos (PontoID, Sentido, Ordem, NomePonto) VALUES (?, ?, ?, ?)", pontos_para_inserir)

    # Popular tabela 'HorariosGerados'
    print("Calculando e populando 'HorariosGerados' (Isso pode levar um momento)...")
    
    # Data de hoje (usada apenas como base para cÃ¡lculos de data/hora)
    today = datetime.now().date()
    horarios_para_inserir = []

    # Processar IDA
    print("... Processando Rota IDA ...")
    for dia_semana, partidas in PARTIDAS_IDA.items():
        for partida_str in partidas:
            partida_time_obj = parse_time(partida_str)
            if not partida_time_obj:
                print(f"AVISO: Ignorando horÃ¡rio de partida invÃ¡lido: '{partida_str}'")
                continue

            current_datetime = datetime.combine(today, partida_time_obj)
            
            for i in range(len(PONTOS_IDA)):
                ponto_id = f"IDA-{i + 1}"
                
                # Para o primeiro ponto (Ponto 1), o horÃ¡rio de chegada Ã© o de partida
                if i > 0:
                    # Para os demais, calcula o intervalo e soma
                    intervalo_s = get_intervalo_segundos(current_datetime, dia_semana)
                    current_datetime += timedelta(seconds=intervalo_s)
                
                horarios_para_inserir.append((
                    ponto_id,
                    dia_semana,
                    LINHA_COD,
                    partida_str, # HorÃ¡rio de inÃ­cio da viagem (ex: 05:10)
                    current_datetime.strftime('%H:%M:%S') # HorÃ¡rio de chegada neste ponto
                ))

    # Processar VOLTA
    print("... Processando Rota VOLTA ...")
    for dia_semana, partidas in PARTIDAS_VOLTA.items():
        for partida_str in partidas:
            partida_time_obj = parse_time(partida_str)
            if not partida_time_obj:
                print(f"AVISO: Ignorando horÃ¡rio de partida invÃ¡lido: '{partida_str}'")
                continue
                
            current_datetime = datetime.combine(today, partida_time_obj)
            
            for i in range(len(PONTOS_VOLTA)):
                ponto_id = f"VOLTA-{i + 1}"
                
                if i > 0:
                    intervalo_s = get_intervalo_segundos(current_datetime, dia_semana)
                    current_datetime += timedelta(seconds=intervalo_s)
                
                horarios_para_inserir.append((
                    ponto_id,
                    dia_semana,
                    LINHA_COD,
                    partida_str,
                    current_datetime.strftime('%H:%M:%S')
                ))

    # Inserir tudo no banco de dados
    cur.executemany("""
        INSERT INTO HorariosGerados 
        (PontoID, DiaSemana, Linha, HorarioPartida, HorarioChegadaEstimada) 
        VALUES (?, ?, ?, ?, ?)
    """, horarios_para_inserir)

    # Criar Ãndices para performance
    print("Criando Ã­ndices...")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_horarios_ponto_dia ON HorariosGerados(PontoID, DiaSemana)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_horarios_chegada ON HorariosGerados(HorarioChegadaEstimada)")

    # Salvar
    conn.commit()
    conn.close()
    
    print("\n--- SUCESSO! ---")
    print(f"Banco de dados '{DB_NAME}' foi criado e populado.")
    print(f"Total de pontos cadastrados: {len(pontos_para_inserir)}")
    print(f"Total de horÃ¡rios calculados: {len(horarios_para_inserir)}")

if __name__ == "__main__":
    criar_banco()

