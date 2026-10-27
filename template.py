# template.py

def gerar_corpo_email(periodo, total_pags, custo_total):
    """
    Gera o texto do email de forma dinâmica.
    Pode alterar a mensagem abaixo livremente. As variáveis dentro de {} 
    serão substituídas automaticamente pelo sistema.
    """
    
    texto = f"""Olá,

Segue em anexo o pacote de relatórios de impressões da Viman Contabilidade referente ao período de {periodo}.

► Total de Páginas Impressas: {total_pags}
► Custo Estimado Total: {custo_total}

Ficheiros em anexo:
- Resumo_Financeiro_Mes.pdf (Consumo por Equipamento)
- Auditoria_Extensos_Mes.pdf (Documentos com mais páginas)
- Auditoria_Duplicados_Mes.pdf (Detecção de Desperdício)
- Base_Dados_Completa.xlsx (Registos Detalhados)

Atenciosamente,
Sistema de Auditoria Interna - Viman Contabilidade"""

    return texto