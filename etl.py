# etl.py
import pandas as pd
from sqlalchemy.engine import Engine
from typing import Tuple

def processar_csv_para_banco(caminho_csv: str, engine: Engine) -> Tuple[int, int]:
    """
    Processa o arquivo CSV e insere apenas os dados não existentes,
    ignorando documentos bloqueados (testes).
    Retorna uma tupla: (qtd_importados, qtd_ignorados)
    """
    # 1. Ler o CSV novo
    df_novo = pd.read_csv(caminho_csv, sep=';', encoding='utf-8')
    df_novo['DataHora'] = pd.to_datetime(df_novo['DataHora'], format='%d/%m/%Y %H:%M:%S', errors='coerce')
    df_novo.columns = ['data_hora', 'terminal', 'usuario', 'impressora', 'paginas', 'documento']
    
    # --- REGRA DE AUDITORIA: BLOQUEIO DE DOCUMENTOS DE TESTE ---
    # Ignora ficheiros específicos para não poluir as métricas reais
    documentos_bloqueados = ['Lembretes_RH_21102026.pdf', 'Print Document']
    df_novo = df_novo[~df_novo['documento'].isin(documentos_bloqueados)]
    # -----------------------------------------------------------
    
    # 2. Ler o que já existe no banco de dados
    query = "SELECT data_hora, terminal, usuario, impressora, documento FROM logs_impressao"
    df_existente = pd.read_sql(query, engine)
    
    # 3. Filtrar os dados (Evitar duplicidades)
    if not df_existente.empty:
        df_existente['data_hora'] = pd.to_datetime(df_existente['data_hora'])
        
        # Cruza as planilhas: o '_merge' dirá de onde o dado veio
        df_cruzado = df_novo.merge(
            df_existente, 
            on=['data_hora', 'terminal', 'usuario', 'impressora', 'documento'], 
            how='left', 
            indicator=True
        )
        
        # Pega apenas os dados que estão APENAS no CSV novo ('left_only')
        df_final = df_cruzado[df_cruzado['_merge'] == 'left_only'].drop(columns=['_merge'])
        
        qtd_ignorados = len(df_novo) - len(df_final)
    else:
        df_final = df_novo
        qtd_ignorados = 0
        
    qtd_importados = len(df_final)
    
    # 4. Inserir no banco de dados apenas se houver registros novos
    if qtd_importados > 0:
        df_final.to_sql('logs_impressao', con=engine, if_exists='append', index=False)
        
    return qtd_importados, qtd_ignorados