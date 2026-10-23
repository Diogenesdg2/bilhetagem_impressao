from sqlalchemy import text
from db import obter_sessao

def limpar_registos_teste():
    sessao, engine = obter_sessao()
    try:
        with engine.begin() as conn:
            # Apaga especificamente os documentos de teste que aparecem na imagem
            resultado = conn.execute(text(
                "DELETE FROM logs_impressao WHERE documento IN ('Lembretes_RH_21102026.pdf', 'Print Document')"
            ))
            linhas_afetadas = resultado.rowcount
            
        print(f"✅ Limpeza concluída! Foram removidos {linhas_afetadas} registos de teste do banco de dados.")
    except Exception as e:
        print(f"Erro ao limpar o banco de dados: {e}")
    finally:
        sessao.close()

if __name__ == "__main__":
    limpar_registos_teste()