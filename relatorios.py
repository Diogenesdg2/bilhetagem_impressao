import pandas as pd
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

def f_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def exportar_resumo_impressoras_pdf(df: pd.DataFrame, caminho: str, periodo: str):
    if df.empty: raise ValueError("Não há dados.")
    def unificar_impressora(nome):
        if str(nome).strip().upper() in ['CONTABIL_FISCAL', 'CONTRATOS']: return 'Contábil/Fiscal & Contratos'
        return nome

    df['impressora_agrupada'] = df['impressora'].apply(unificar_impressora)
    resumo = df.groupby('impressora_agrupada').agg({'paginas': 'sum', 'custo_total': 'sum'}).reset_index().sort_values(by='paginas', ascending=False)
    total_pags, total_custo = resumo['paginas'].sum(), resumo['custo_total'].sum()

    pdf = SimpleDocTemplate(caminho, pagesize=A4)
    estilos = getSampleStyleSheet()
    elementos = [Paragraph("<b>Resumo Financeiro por Equipamento</b>", estilos['Title']), Spacer(1, 10), Paragraph(f"<b>Período:</b> {periodo}", estilos['Normal']), Spacer(1, 20)]
    
    dados = [['Equipamento (Impressora)', 'Total Páginas', 'Custo Total']]
    for _, r in resumo.iterrows(): dados.append([r['impressora_agrupada'], str(int(r['paginas'])), f_moeda(r['custo_total'])])
    dados.append(['TOTAL GERAL', str(int(total_pags)), f_moeda(total_custo)])

    tabela = Table(dados, colWidths=[250, 100, 120])
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0052cc")), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10), ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#2FA572")),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke), ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'), ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elementos.append(tabela); pdf.build(elementos)

def exportar_resumo_usuarios_pdf(df: pd.DataFrame, caminho: str, periodo: str, ordenacao: str):
    if df.empty: raise ValueError("Não há dados.")
    resumo = df.groupby(['nome_final', 'departamento']).agg({'paginas': 'sum', 'custo_total': 'sum'}).reset_index()
    resumo = resumo.sort_values(by='nome_final' if ordenacao == "Ordem Alfabética" else 'paginas', ascending=(ordenacao == "Ordem Alfabética"))
    total_pags, total_custo = resumo['paginas'].sum(), resumo['custo_total'].sum()

    pdf = SimpleDocTemplate(caminho, pagesize=A4)
    estilos = getSampleStyleSheet()
    elementos = [Paragraph("<b>Resumo Financeiro por Utilizador</b>", estilos['Title']), Spacer(1, 10), Paragraph(f"<b>Período:</b> {periodo} | <b>Ordem:</b> {ordenacao}", estilos['Normal']), Spacer(1, 20)]
    
    dados = [['Utilizador', 'Setor', 'Págs', 'Custo (R$)']]
    for _, r in resumo.iterrows(): dados.append([r['nome_final'], r['departamento'], str(int(r['paginas'])), f_moeda(r['custo_total'])])
    dados.append(['TOTAL GERAL', '-', str(int(total_pags)), f_moeda(total_custo)])

    tabela = Table(dados, colWidths=[180, 160, 60, 100])
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0052cc")), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('ALIGN', (0, 1), (1, -2), 'LEFT'), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10), ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#2FA572")),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke), ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'), ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elementos.append(tabela); pdf.build(elementos)

def exportar_relatorio_detalhado_pdf(df: pd.DataFrame, caminho: str, periodo: str, info_filtros: str):
    if df.empty: raise ValueError("Não há dados.")
    pdf = SimpleDocTemplate(caminho, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    estilos = getSampleStyleSheet()
    estilo_tabela = estilos['Normal']; estilo_tabela.fontSize = 8
    elementos = [Paragraph("<b>Auditoria Detalhada (Com Custeio)</b>", estilos['Title']), Spacer(1, 5), Paragraph(f"<b>Período:</b> {periodo} | <b>Filtros:</b> {info_filtros}", estilos['Normal']), Spacer(1, 10)]
    
    dados = [['Data/Hora', 'Terminal', 'Utilizador Real', 'Setor', 'Impressora', 'Págs', 'Custo', 'Documento']]
    total_pags, total_custo = 0, 0
    
    for _, row in df.iterrows():
        dados.append([pd.to_datetime(row['data_hora']).strftime("%d/%m/%Y %H:%M"), str(row['terminal']), str(row['nome_final']), str(row['departamento']), str(row['impressora']), str(int(row['paginas'])), f_moeda(row['custo_total']), Paragraph(str(row['documento']), estilo_tabela)])
        total_pags += int(row['paginas'])
        total_custo += float(row['custo_total'])

    dados.append(['TOTAL GERAL DO PERÍODO', '', '', '', '', str(int(total_pags)), f_moeda(total_custo), ''])

    tabela = Table(dados, colWidths=[80, 65, 110, 100, 80, 30, 50, 260])
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0052cc")), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (-1, 0), 8), ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('FONTSIZE', (0, 1), (-1, -2), 8), ('ALIGN', (0, 1), (4, -2), 'LEFT'),
        ('ALIGN', (5, 1), (6, -1), 'CENTER'), ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#2FA572")),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke), ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 9), ('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('SPAN', (0, -1), (4, -1))
    ]))
    elementos.append(tabela); pdf.build(elementos)

def exportar_auditoria_extensos_pdf(df, caminho, periodo):
    doc = SimpleDocTemplate(caminho, pagesize=landscape(A4), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elementos = []
    estilos = getSampleStyleSheet()
    estilo_normal = estilos["Normal"]
    estilo_titulo = estilos["Title"]

    elementos.append(Paragraph(f"Auditoria: Top Documentos Mais Extensos", estilo_titulo))
    elementos.append(Paragraph(f"Período: {periodo}", estilo_normal))
    elementos.append(Spacer(1, 20))

    dados = [["Data", "Utilizador", "Setor", "Páginas", "Documento"]]
    for _, r in df.iterrows():
        doc_text = Paragraph(str(r['Ficheiro']), estilo_normal)
        dados.append([str(r['Data']), str(r['Utilizador']), str(r['Setor']), str(r['Páginas']), doc_text])

    tabela = Table(dados, colWidths=[90, 110, 110, 50, 420])
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2FA572")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (4, 1), (4, -1), 'LEFT'), 
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#f4f4f4")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elementos.append(tabela)
    doc.build(elementos)

def exportar_auditoria_duplicados_pdf(df, caminho, periodo):
    doc = SimpleDocTemplate(caminho, pagesize=landscape(A4), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elementos = []
    estilos = getSampleStyleSheet()
    estilo_normal = estilos["Normal"]
    estilo_titulo = estilos["Title"]

    elementos.append(Paragraph(f"Auditoria: Top Impressões Duplicadas (Desperdício)", estilo_titulo))
    elementos.append(Paragraph(f"Período: {periodo}", estilo_normal))
    elementos.append(Spacer(1, 20))

    dados = [["Qtd", "Utilizador", "Setor", "Total Páginas", "Documento"]]
    for _, r in df.iterrows():
        doc_text = Paragraph(str(r['Ficheiro']), estilo_normal)
        dados.append([str(r['Qtd Impressões']), str(r['Utilizador']), str(r['Setor']), str(r['Total Páginas']), doc_text])

    tabela = Table(dados, colWidths=[60, 120, 120, 80, 400])
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#E74C3C")), 
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (4, 1), (4, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#f4f4f4")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elementos.append(tabela)
    doc.build(elementos)