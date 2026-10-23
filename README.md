# 🖨️ Sistema Corporativo de Bilhetagem de Impressão

Um sistema *Desktop* avançado desenvolvido em Python (com interface moderna em CustomTkinter) focado em monitorização, auditoria financeira e análise de impacto ambiental (ESG) de parques de impressão corporativos.

Desenvolvido para gerir custos operacionais, rateios entre departamentos e automatizar o fecho financeiro mensal.

---

## ✨ Principais Funcionalidades

*   📊 **Dashboard de Business Intelligence (BI):** Gráficos interativos de consumo, rankings de utilizadores (Top 5), horários de pico e evolução diária.
*   💰 **Módulo Financeiro (Custeio):** Definição de custo (R$) individualizado por impressora, calculando automaticamente as despesas por utilizador e departamento.
*   🌱 **Métricas ESG:** Tradução automática do volume de impressões para impacto ambiental (Árvores consumidas, Litros de Água gastos e Pegada de CO2).
*   📄 **Exportação Flexível:** Geração de relatórios Sintéticos e Analíticos em **PDF** (via ReportLab) e **Excel (.xlsx)** (via Pandas).
*   🤖 **Automação de E-mail (Fecho Mensal):** Assistente inteligente que deteta a viragem do mês, empacota o PDF e Excel, e envia automaticamente por e-mail via SMTP.

---

## 📥 Estrutura e Importação do CSV

Para que o motor de ETL (Extract, Transform, Load) do sistema funcione perfeitamente, o sistema requer a importação de um ficheiro `.csv` (separado por vírgulas ou ponto e vírgula) contendo o log das impressões.

**As colunas esperadas pelo sistema são:**
1.  `data_hora` (Ex: 23/10/2026 09:30)
2.  `terminal` (Nome do Computador/IP, Ex: MICRO06)
3.  `usuario` (Login da rede, Ex: leticia.assis)
4.  `impressora` (Nome da fila de impressão, Ex: Contabil_Fiscal)
5.  `paginas` (Número inteiro, Ex: 4)
6.  `documento` (Nome do ficheiro impresso, Ex: relatorio_anual.pdf)

*(Pode extrair estes dados utilizando scripts de Powershell do Visualizador de Eventos do Windows Print Server, ou exportar de softwares como PaperCut).*

---

