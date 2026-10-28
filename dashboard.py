import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog, Menu
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends.backend_pdf import PdfPages
from tkcalendar import Calendar
from datetime import datetime
from db import obter_sessao

class DashboardFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        
        self.figuras_para_exportar = []
        self.df_atual = pd.DataFrame() 
        
        # --- BARRA DE FILTROS GLOBAL E EXPORTAÇÃO ---
        self.frame_filtros = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_filtros.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(self.frame_filtros, text="Data Inicial:").pack(side="left", padx=(0, 5))
        self.entry_data_ini = ctk.CTkEntry(self.frame_filtros, width=110, placeholder_text="DD/MM/AAAA")
        self.entry_data_ini.pack(side="left", padx=(0, 5))
        ctk.CTkButton(self.frame_filtros, text="📅", width=30, command=lambda: self.abrir_calendario(self.entry_data_ini)).pack(side="left", padx=(0, 15))

        ctk.CTkLabel(self.frame_filtros, text="Data Final:").pack(side="left", padx=(0, 5))
        self.entry_data_fim = ctk.CTkEntry(self.frame_filtros, width=110, placeholder_text="DD/MM/AAAA")
        self.entry_data_fim.pack(side="left", padx=(0, 5))
        ctk.CTkButton(self.frame_filtros, text="📅", width=30, command=lambda: self.abrir_calendario(self.entry_data_fim)).pack(side="left", padx=(0, 15))

        ctk.CTkButton(self.frame_filtros, text="Atualizar Dashboards 🔄", command=self.gerar_graficos, fg_color="#2FA572", hover_color="#1D7850", width=170).pack(side="left", padx=10)
        ctk.CTkButton(self.frame_filtros, text="Exportar PDF 📄", command=self.exportar_pdf, fg_color="#C0392B", hover_color="#922B21", width=130).pack(side="left", padx=(0, 10))
        ctk.CTkButton(self.frame_filtros, text="Limpar", command=self.limpar_filtros, fg_color="#555", hover_color="#333", width=80).pack(side="left")
        
        # --- ABAS ---
        self.tabview_dash = ctk.CTkTabview(self)
        self.tabview_dash.pack(fill="both", expand=True)

        self.tab_geral = self.tabview_dash.add("Visão Geral")
        self.tab_tempo = self.tabview_dash.add("Análise Temporal")
        self.tab_auditoria = self.tabview_dash.add("Auditoria & Desperdício")
        self.tab_financeiro = self.tabview_dash.add("Painel Financeiro")
        self.tab_processos = self.tabview_dash.add("Mapa de Processos")
        self.tab_seguranca = self.tabview_dash.add("Radar de Segurança")
        
        bg = "#2b2b2b" if ctk.get_appearance_mode() == "Dark" else "#ffffff"
        fg = "white" if bg == "#2b2b2b" else "black"
        style = ttk.Style()
        style.theme_use("default") 
        style.configure("Treeview", background=bg, foreground=fg, fieldbackground=bg, borderwidth=0)
        style.map('Treeview', background=[('selected', '#1f538d')])
        
        # --- SETUP: AUDITORIA ---
        self.frame_audit_esq = ctk.CTkFrame(self.tab_auditoria, fg_color="transparent")
        self.frame_audit_esq.pack(side="left", fill="both", expand=True)
        self.frame_audit_dir = ctk.CTkFrame(self.tab_auditoria, fg_color="transparent")
        self.frame_audit_dir.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        self.frame_t1 = ctk.CTkFrame(self.frame_audit_dir)
        self.frame_t1.pack(fill="both", expand=True, pady=(0, 5))
        ctk.CTkLabel(self.frame_t1, text="Top 10 Documentos Mais Extensos (Volume Único)", font=ctk.CTkFont(weight="bold", size=13)).pack(pady=(5, 2))
        
        scroll_y1 = ttk.Scrollbar(self.frame_t1)
        scroll_y1.pack(side="right", fill="y")
        self.tree_top10 = ttk.Treeview(self.frame_t1, columns=("Data", "Usuario", "Pags", "Doc"), show="headings", yscrollcommand=scroll_y1.set)
        scroll_y1.config(command=self.tree_top10.yview)
        for c, w in zip(("Data", "Usuario", "Pags", "Doc"), (90, 100, 50, 200)):
            self.tree_top10.heading(c, text=c); self.tree_top10.column(c, width=w, anchor="center" if c != "Doc" else "w")
        self.tree_top10.pack(fill="both", expand=True, padx=5, pady=5)

        self.frame_t2 = ctk.CTkFrame(self.frame_audit_dir)
        self.frame_t2.pack(fill="both", expand=True, pady=(5, 0))
        ctk.CTkLabel(self.frame_t2, text="Top 10 Impressões Duplicadas (Desperdício)", font=ctk.CTkFont(weight="bold", size=13)).pack(pady=(5, 2))
        
        scroll_y2 = ttk.Scrollbar(self.frame_t2)
        scroll_y2.pack(side="right", fill="y")
        self.tree_repetidos = ttk.Treeview(self.frame_t2, columns=("Qtd", "Usuario", "Total Pags", "Doc"), show="headings", yscrollcommand=scroll_y2.set)
        scroll_y2.config(command=self.tree_repetidos.yview)
        for c, w in zip(("Qtd", "Usuario", "Total Pags", "Doc"), (45, 100, 75, 220)):
            self.tree_repetidos.heading(c, text=c); self.tree_repetidos.column(c, width=w, anchor="center" if c != "Doc" else "w")
        self.tree_repetidos.pack(fill="both", expand=True, padx=5, pady=5)

        self.tree_top10.bind("<Double-1>", lambda e: self.abrir_detalhes(self.tree_top10, is_duplicado=False))
        self.tree_repetidos.bind("<Double-1>", lambda e: self.abrir_detalhes(self.tree_repetidos, is_duplicado=True))

        # --- SETUP: RADAR DE SEGURANÇA ---
        self.frame_seg = ctk.CTkFrame(self.tab_seguranca, fg_color="transparent")
        self.frame_seg.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(self.frame_seg, text="🚨 Alertas de Impressão (Fins de Semana, Almoço e Fora do Expediente)", font=ctk.CTkFont(weight="bold", size=15), text_color="#E74C3C").pack(pady=(10, 10))

        scroll_y_seg = ttk.Scrollbar(self.frame_seg)
        scroll_y_seg.pack(side="right", fill="y")
        self.tree_seg = ttk.Treeview(self.frame_seg, columns=("Data", "Usuario", "Motivo", "Pags", "Doc"), show="headings", yscrollcommand=scroll_y_seg.set)
        scroll_y_seg.config(command=self.tree_seg.yview)
        for c, w in zip(("Data", "Usuario", "Motivo", "Pags", "Doc"), (120, 120, 150, 50, 250)):
            self.tree_seg.heading(c, text=c)
            self.tree_seg.column(c, width=w, anchor="center" if c != "Doc" else "w")
        self.tree_seg.pack(fill="both", expand=True, padx=5, pady=5)

    def exportar_pdf(self):
        if not self.figuras_para_exportar:
            messagebox.showwarning("Aviso", "Nenhum gráfico para exportar. Clique em 'Atualizar Dashboards' primeiro.")
            return
            
        caminho_arquivo = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=[("Arquivo PDF", "*.pdf")],
            title="Salvar Relatório Gerencial",
            initialfile=f"Relatorio_Viman_{datetime.now().strftime('%d%m%Y_%H%M')}.pdf"
        )
        if not caminho_arquivo: return
            
        try:
            with PdfPages(caminho_arquivo) as pdf:
                for fig in self.figuras_para_exportar:
                    pdf.savefig(fig, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
            messagebox.showinfo("Sucesso", f"Relatório exportado com sucesso!\n{caminho_arquivo}")
        except Exception as e:
            messagebox.showerror("Erro", f"Ocorreu um erro ao gerar o PDF:\n{e}")

    def abrir_calendario(self, entry_alvo):
        janela_cal = ctk.CTkToplevel(self)
        janela_cal.title("Data")
        janela_cal.geometry("300x300")
        janela_cal.attributes("-topmost", True)
        janela_cal.grab_set()
        bg, fg = ("#2b2b2b", "white") if ctk.get_appearance_mode() == "Dark" else ("white", "black")
        cal = Calendar(janela_cal, selectmode='day', date_pattern='dd/mm/yyyy', background="#1f538d", headersbackground="#1f538d", normalbackground=bg, foreground=fg, normalforeground=fg, headersforeground="white")
        cal.pack(pady=10, padx=10, fill="both", expand=True)
        ctk.CTkButton(janela_cal, text="Confirmar 📅", command=lambda: [entry_alvo.delete(0, 'end'), entry_alvo.insert(0, cal.get_date()), janela_cal.destroy()]).pack(pady=10)

    def limpar_filtros(self):
        self.entry_data_ini.delete(0, 'end')
        self.entry_data_fim.delete(0, 'end')
        self.gerar_graficos()

    def abrir_detalhes_processo(self, categoria):
        if self.df_atual.empty: return
        df_cat = self.df_atual[self.df_atual['processo'] == categoria]
        if df_cat.empty: return

        df_docs = df_cat.groupby('documento').agg(vezes=('documento', 'count'), paginas=('paginas', 'sum')).reset_index()
        df_docs = df_docs.sort_values(by='paginas', ascending=False)

        janela_proc = ctk.CTkToplevel(self)
        janela_proc.title(f"Auditoria da Categoria: {categoria}")
        janela_proc.geometry("850x400")
        janela_proc.attributes("-topmost", True)
        
        ctk.CTkLabel(janela_proc, text=f"🔍 Detalhamento de Processo: {categoria}", font=ctk.CTkFont(weight="bold", size=14)).pack(pady=10)
        ctk.CTkLabel(janela_proc, text="Dica: Clique com o botão direito do rato sobre um documento para ver opções.", font=ctk.CTkFont(slant="italic", size=12), text_color="gray").pack(pady=(0, 5))

        frame_grid = ctk.CTkFrame(janela_proc)
        frame_grid.pack(fill="both", expand=True, padx=10, pady=10)
        
        scroll_y = ttk.Scrollbar(frame_grid)
        scroll_y.pack(side="right", fill="y")
        
        tree_proc = ttk.Treeview(frame_grid, columns=("Doc", "Vezes", "Pags"), show="headings", yscrollcommand=scroll_y.set)
        scroll_y.config(command=tree_proc.yview)
        
        tree_proc.heading("Doc", text="Nome do Documento")
        tree_proc.column("Doc", width=600, anchor="w")
        tree_proc.heading("Vezes", text="Qtd Impressões")
        tree_proc.column("Vezes", width=100, anchor="center")
        tree_proc.heading("Pags", text="Total Páginas")
        tree_proc.column("Pags", width=100, anchor="center")
        
        for _, r in df_docs.iterrows():
            tree_proc.insert("", "end", values=(r['documento'], f"{int(r['vezes'])}x", int(r['paginas'])))
            
        tree_proc.pack(fill="both", expand=True)

        # --- NOVO: MENU DE CONTEXTO (CLIQUE DIREITO) ---
        menu_contexto = Menu(janela_proc, tearoff=0, bg="#2b2b2b", fg="white", activebackground="#2FA572", activeforeground="white")
        
        def ver_relatorio():
            selecao = tree_proc.selection()
            if not selecao: return
            nome_doc = tree_proc.item(selecao[0], "values")[0]
            janela_proc.destroy() 
            app_principal = self.winfo_toplevel()
            if hasattr(app_principal, "pesquisar_nos_registros"):
                app_principal.pesquisar_nos_registros(nome_doc)
                
        def classificar_mapa():
            selecao = tree_proc.selection()
            if not selecao: return
            nome_doc = tree_proc.item(selecao[0], "values")[0]
            # Opcional: pode fechar o popup ou mantê-lo aberto. Vamos manter aberto por trás.
            app_principal = self.winfo_toplevel()
            if hasattr(app_principal, "abrir_janela_regras"):
                app_principal.abrir_janela_regras(pre_fill_valor=nome_doc)

        menu_contexto.add_command(label="📄 Ver no Relatório Detalhado", command=ver_relatorio)
        menu_contexto.add_command(label="🏷️ Classificar no Mapa de Processos", command=classificar_mapa)

        def ao_clicar_direito(event):
            item = tree_proc.identify_row(event.y)
            if item:
                tree_proc.selection_set(item)
                menu_contexto.post(event.x_root, event.y_root)

        tree_proc.bind("<Button-3>", ao_clicar_direito)
        
        # Mantém o duplo clique como atalho direto para o Relatório (mais rápido)
        tree_proc.bind("<Double-1>", lambda e: ver_relatorio())

    def abrir_detalhes(self, tree, is_duplicado):
        item_selecionado = tree.selection()
        if not item_selecionado: return
        
        valores = tree.item(item_selecionado[0], "values")
        usuario = valores[1]
        documento = valores[3]

        d_ini = self.entry_data_ini.get().strip()
        d_fim = self.entry_data_fim.get().strip()

        janela_det = ctk.CTkToplevel(self)
        janela_det.title(f"Histórico de Impressão - {usuario}")
        janela_det.geometry("700x300")
        janela_det.attributes("-topmost", True)
        
        ctk.CTkLabel(janela_det, text=f"Documento: {documento}", font=ctk.CTkFont(weight="bold", size=13), wraplength=650).pack(pady=(10, 5))

        frame_grid = ctk.CTkFrame(janela_det)
        frame_grid.pack(fill="both", expand=True, padx=10, pady=10)
        
        scroll_y = ttk.Scrollbar(frame_grid)
        scroll_y.pack(side="right", fill="y")
        
        tree_det = ttk.Treeview(frame_grid, columns=("Data", "Terminal", "Impressora", "Pags"), show="headings", yscrollcommand=scroll_y.set)
        scroll_y.config(command=tree_det.yview)
        
        for c, w in zip(("Data", "Terminal", "Impressora", "Pags"), (120, 150, 150, 50)):
            tree_det.heading(c, text=c)
            tree_det.column(c, width=w, anchor="center")
        tree_det.pack(fill="both", expand=True)

        sessao, engine = obter_sessao()
        try:
            query = f"""SELECT l.data_hora, l.terminal, l.impressora, l.paginas 
                        FROM logs_impressao l 
                        LEFT JOIN mapeamento_terminais m ON UPPER(l.terminal) = UPPER(m.terminal)
                        WHERE l.documento = '{documento}' 
                        AND COALESCE(m.nome_real, l.usuario) = '{usuario}'"""
            
            if d_ini: query += f" AND l.data_hora >= '{datetime.strptime(d_ini, '%d/%m/%Y').strftime('%Y-%m-%d 00:00:00')}'"
            if d_fim: query += f" AND l.data_hora <= '{datetime.strptime(d_fim, '%d/%m/%Y').strftime('%Y-%m-%d 23:59:59')}'"
            query += " ORDER BY l.data_hora DESC"

            df_detalhes = pd.read_sql(query, engine)
            
            for _, r in df_detalhes.iterrows():
                d_str = pd.to_datetime(r['data_hora']).strftime("%d/%m/%Y %H:%M:%S")
                tree_det.insert("", "end", values=(d_str, r['terminal'], r['impressora'], int(r['paginas'])))
        except Exception as e:
            print(f"Erro ao carregar detalhes: {e}")
        finally:
            sessao.close()

    def extrair_extensao(self, doc):
        if not isinstance(doc, str) or '.' not in doc: return 'Sistema / Web'
        ext = doc.split('.')[-1].lower().strip()
        if len(ext) > 5 or not ext.isalnum(): return 'Sistema / Web'
        return f".{ext}"

    def gerar_graficos(self):
        sessao, engine = obter_sessao()
        self.figuras_para_exportar = []
        
        try:
            d_ini = self.entry_data_ini.get().strip()
            d_fim = self.entry_data_fim.get().strip()

            query = '''SELECT l.data_hora, l.terminal, COALESCE(m.nome_real, l.usuario) as nome_final, 
                       COALESCE(m.departamento, 'Sem Setor') as departamento, l.impressora, l.paginas, l.documento 
                       FROM logs_impressao l 
                       LEFT JOIN mapeamento_terminais m ON UPPER(l.terminal) = UPPER(m.terminal) WHERE 1=1'''
            
            if d_ini: query += f" AND l.data_hora >= '{datetime.strptime(d_ini, '%d/%m/%Y').strftime('%Y-%m-%d 00:00:00')}'"
            if d_fim: query += f" AND l.data_hora <= '{datetime.strptime(d_fim, '%d/%m/%Y').strftime('%Y-%m-%d 23:59:59')}'"
                
            df = pd.read_sql(query, engine)
        except ValueError:
            messagebox.showerror("Erro de Filtro", "Formato de data inválido. Use DD/MM/AAAA.")
            return
        except Exception: return
        finally: sessao.close()

        self.df_atual = df

        for widget in self.tab_geral.winfo_children(): widget.destroy()
        for widget in self.tab_tempo.winfo_children(): widget.destroy()
        for widget in self.frame_audit_esq.winfo_children(): widget.destroy()
        for item in self.tree_top10.get_children(): self.tree_top10.delete(item)
        for item in self.tree_repetidos.get_children(): self.tree_repetidos.delete(item)
        for widget in self.tab_financeiro.winfo_children(): widget.destroy()
        for widget in self.tab_processos.winfo_children(): widget.destroy()
        for item in self.tree_seg.get_children(): self.tree_seg.delete(item)

        if df.empty: 
            bg = "#2b2b2b" if ctk.get_appearance_mode() == "Dark" else "#ffffff"
            ctk.CTkLabel(self.tab_geral, text="Nenhum dado encontrado para o período selecionado.", font=ctk.CTkFont(size=14, slant="italic")).pack(expand=True)
            return

        bg = "#2b2b2b" if ctk.get_appearance_mode() == "Dark" else "#ffffff"
        txt = "white" if bg == "#2b2b2b" else "black"

        # 1. VISÃO GERAL
        df_dept = df.groupby('departamento')['paginas'].sum().sort_values(ascending=True)
        df_impressoras = df.groupby('impressora')['paginas'].sum().sort_values(ascending=False)
        df_usuarios_all = df.groupby('nome_final')['paginas'].sum().sort_values(ascending=True)

        fig_geral, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(11, 7)); fig_geral.patch.set_facecolor(bg)
        
        ax1.set_facecolor(bg)
        barras_dept = ax1.barh(df_dept.index, df_dept.values, color='#9B59B6')
        for b in barras_dept:
            w = b.get_width()
            if w > 0: ax1.annotate(f"{int(w)}", xy=(w, b.get_y() + b.get_height()/2), xytext=(5, 0), textcoords="offset points", ha='left', va='center', color=txt, fontsize=10, weight='bold')
        ax1.set_title('Consumo por Setor', color=txt, fontsize=12, pad=10); ax1.tick_params(colors=txt)
        for s in ax1.spines.values(): s.set_edgecolor(txt)
        ax1.spines['top'].set_visible(False); ax1.spines['right'].set_visible(False); ax1.set_xlim(right=ax1.get_xlim()[1] * 1.15)
        
        ax2.set_facecolor(bg)
        ax2.pie(df_impressoras.values, labels=df_impressoras.index, autopct='%1.1f%%', startangle=90, colors=['#3498DB', '#E67E22', '#F1C40F', '#95A5A6'], textprops={'color': txt, 'weight': 'bold'}, wedgeprops={'edgecolor': bg, 'linewidth': 2})
        ax2.set_title('Divisão por Equipamento', color=txt, fontsize=12, pad=10)

        ax3.set_facecolor(bg)
        barras_top = ax3.barh(df_usuarios_all.tail(5).index, df_usuarios_all.tail(5).values, color='#E74C3C')
        for b in barras_top:
            w = b.get_width()
            if w > 0: ax3.annotate(f"{int(w)}", xy=(w, b.get_y() + b.get_height()/2), xytext=(5, 0), textcoords="offset points", ha='left', va='center', color=txt, fontsize=10, weight='bold')
        ax3.set_title('Top 5: Mais Impressões', color=txt, fontsize=12, pad=10, weight='bold'); ax3.tick_params(colors=txt)
        for s in ax3.spines.values(): s.set_edgecolor(txt)
        ax3.spines['top'].set_visible(False); ax3.spines['right'].set_visible(False); ax3.set_xlim(right=ax3.get_xlim()[1] * 1.15)

        ax4.set_facecolor(bg)
        barras_bot = ax4.barh(df_usuarios_all.head(5).index, df_usuarios_all.head(5).values, color='#2FA572')
        for b in barras_bot:
            w = b.get_width()
            if w > 0: ax4.annotate(f"{int(w)}", xy=(w, b.get_y() + b.get_height()/2), xytext=(5, 0), textcoords="offset points", ha='left', va='center', color=txt, fontsize=10, weight='bold')
        ax4.set_title('Top 5: Menos Impressões', color=txt, fontsize=12, pad=10, weight='bold'); ax4.tick_params(colors=txt)
        for s in ax4.spines.values(): s.set_edgecolor(txt)
        ax4.spines['top'].set_visible(False); ax4.spines['right'].set_visible(False); ax4.set_xlim(right=ax4.get_xlim()[1] * 1.15)

        fig_geral.tight_layout(); self.figuras_para_exportar.append(fig_geral)
        FigureCanvasTkAgg(fig_geral, master=self.tab_geral).draw(); FigureCanvasTkAgg(fig_geral, master=self.tab_geral).get_tk_widget().pack(fill="both", expand=True)

        # 2. ANÁLISE TEMPORAL 
        df['data_hora'] = pd.to_datetime(df['data_hora'])
        df_dia = df.groupby(df['data_hora'].dt.strftime('%d/%m'))['paginas'].sum().sort_index()
        df_acumulado = df_dia.cumsum()
        df['hora'] = df['data_hora'].dt.hour
        df_hora = df.groupby('hora')['paginas'].sum().sort_index()

        fig_tempo, (ax_evol, ax_hora) = plt.subplots(2, 1, figsize=(11, 8)); fig_tempo.patch.set_facecolor(bg)

        ax_evol.set_facecolor(bg)
        x_dias = range(len(df_dia))
        ax_evol.bar(x_dias, df_dia.values, color='#316b93', label='Volume Diário', alpha=0.9)
        ax_evol.plot(x_dias, df_dia.values, marker='o', color='#0088ff', linewidth=2, label='Tendência Diária')
        ax_evol.plot(x_dias, df_acumulado.values, marker='o', color='#e74c3c', linewidth=2, label='Evolução Acumulada')
        
        ax_evol.set_xticks(x_dias); ax_evol.set_xticklabels(df_dia.index, rotation=45, color=txt)
        ax_evol.set_title('Evolução Diária e Crescimento Acumulado', color=txt, pad=15)
        ax_evol.tick_params(colors=txt)
        for s in ax_evol.spines.values(): s.set_edgecolor(txt)
        ax_evol.spines['top'].set_visible(False); ax_evol.spines['right'].set_visible(False)
        for i, v in enumerate(df_dia.values):
            ax_evol.text(i, v/2, str(int(v)), ha='center', va='center', color='white', weight='bold') 
            ax_evol.text(i, df_acumulado.values[i] + (df_acumulado.max()*0.03), str(int(df_acumulado.values[i])), ha='center', va='bottom', color=txt, weight='bold') 
        ax_evol.legend(loc='upper left', frameon=False, labelcolor=txt)

        ax_hora.set_facecolor(bg)
        barras_hora = ax_hora.bar(df_hora.index, df_hora.values, color='#e67e22')
        ax_hora.set_xticks(df_hora.index); ax_hora.set_xticklabels([f"{int(h)}h" for h in df_hora.index], color=txt)
        ax_hora.set_title('Horários de Maior Sobrecarga (Picos do Dia)', color=txt, pad=15)
        ax_hora.tick_params(colors=txt)
        for s in ax_hora.spines.values(): s.set_edgecolor(txt)
        ax_hora.spines['top'].set_visible(False); ax_hora.spines['right'].set_visible(False)
        for b in barras_hora:
            h = b.get_height()
            ax_hora.text(b.get_x() + b.get_width()/2, h + (df_hora.max()*0.02), str(int(h)), ha='center', va='bottom', color=txt, weight='bold')

        fig_tempo.tight_layout(); self.figuras_para_exportar.append(fig_tempo)
        FigureCanvasTkAgg(fig_tempo, master=self.tab_tempo).draw(); FigureCanvasTkAgg(fig_tempo, master=self.tab_tempo).get_tk_widget().pack(fill="both", expand=True)

        # 3. AUDITORIA & DESPERDÍCIO
        df['extensao'] = df['documento'].apply(self.extrair_extensao)
        df_ext = df.groupby('extensao')['paginas'].sum().sort_values(ascending=False).head(6)
        
        fig_audit, ax_audit = plt.subplots(figsize=(7, 5)); fig_audit.patch.set_facecolor(bg); ax_audit.set_facecolor(bg)
        if not df_ext.empty:
            total_paginas = df_ext.sum()
            legend_labels = [f"{idx} - {val/total_paginas*100:.1f}%" for idx, val in df_ext.items()]
            wedges, texts = ax_audit.pie(df_ext.values, startangle=90, colors=['#E74C3C', '#8E44AD', '#3498DB', '#1ABC9C', '#F39C12', '#95A5A6'], wedgeprops={'edgecolor': bg, 'linewidth': 2, 'width': 0.4})
            ax_audit.legend(wedges, legend_labels, title="Formatos & Volume", loc="center left", bbox_to_anchor=(0.95, 0.5), frameon=False, labelcolor=txt)
                     
        ax_audit.set_title('Volume por Tipo de Ficheiro', color=txt, fontsize=12, pad=10, weight='bold')
        fig_audit.tight_layout(); self.figuras_para_exportar.append(fig_audit)
        FigureCanvasTkAgg(fig_audit, master=self.frame_audit_esq).draw(); FigureCanvasTkAgg(fig_audit, master=self.frame_audit_esq).get_tk_widget().pack(fill="both", expand=True)

        top_10 = df.nlargest(10, 'paginas')
        for _, r in top_10.iterrows():
            d_str = r['data_hora'].strftime("%d/%m %H:%M")
            self.tree_top10.insert("", "end", values=(d_str, r['nome_final'], int(r['paginas']), r['documento']))

        df_duplicados = df.groupby(['documento', 'nome_final']).agg(vezes=('documento', 'count'), paginas_totais=('paginas', 'sum')).reset_index()
        df_duplicados = df_duplicados[df_duplicados['vezes'] > 1].sort_values(by=['vezes', 'paginas_totais'], ascending=[False, False]).head(10)
        for _, r in df_duplicados.iterrows():
            self.tree_repetidos.insert("", "end", values=(f"{int(r['vezes'])}x", r['nome_final'], int(r['paginas_totais']), r['documento']))

        # 4. PAINEL FINANCEIRO
        dict_custos = {}
        sessao2, engine2 = obter_sessao()
        try:
            df_c = pd.read_sql("SELECT impressora, custo FROM custos_impressao", engine2)
            dict_custos = dict(zip(df_c['impressora'], df_c['custo']))
        except Exception: pass 
        finally: sessao2.close()

        def obter_custo(imp): return dict_custos.get(imp, 0.08)
        df['custo_total'] = df['paginas'] * df['impressora'].apply(obter_custo)

        df_custo_setor = df.groupby('departamento')['custo_total'].sum().sort_values(ascending=True)
        df_custo_imp = df.groupby('impressora')['custo_total'].sum().sort_values(ascending=True)
        custo_total_periodo = df['custo_total'].sum()

        lbl_header = ctk.CTkLabel(self.tab_financeiro, text=f"Custo Total no Período: R$ {custo_total_periodo:,.2f}".replace(',','X').replace('.',',').replace('X','.'), font=ctk.CTkFont(size=22, weight="bold"), text_color="#2FA572")
        lbl_header.pack(pady=(20, 10))

        fig_fin, (ax_fin1, ax_fin2) = plt.subplots(1, 2, figsize=(11, 5)); fig_fin.patch.set_facecolor(bg)

        ax_fin1.set_facecolor(bg)
        barras_fin1 = ax_fin1.barh(df_custo_setor.index, df_custo_setor.values, color='#8E44AD')
        for b in barras_fin1:
            w = b.get_width()
            if w > 0: ax_fin1.annotate(f"R$ {w:,.2f}".replace(',','X').replace('.',',').replace('X','.'), xy=(w, b.get_y() + b.get_height()/2), xytext=(5, 0), textcoords="offset points", ha='left', va='center', color=txt, fontsize=10, weight='bold')
        ax_fin1.set_title('Rateio de Custos por Setor', color=txt, fontsize=12, pad=10); ax_fin1.tick_params(colors=txt)
        for s in ax_fin1.spines.values(): s.set_edgecolor(txt)
        ax_fin1.spines['top'].set_visible(False); ax_fin1.spines['right'].set_visible(False); ax_fin1.set_xlim(right=ax_fin1.get_xlim()[1] * 1.30)

        ax_fin2.set_facecolor(bg)
        barras_fin2 = ax_fin2.barh(df_custo_imp.index, df_custo_imp.values, color='#E67E22')
        for b in barras_fin2:
            w = b.get_width()
            if w > 0: ax_fin2.annotate(f"R$ {w:,.2f}".replace(',','X').replace('.',',').replace('X','.'), xy=(w, b.get_y() + b.get_height()/2), xytext=(5, 0), textcoords="offset points", ha='left', va='center', color=txt, fontsize=10, weight='bold')
        ax_fin2.set_title('Custos por Equipamento', color=txt, fontsize=12, pad=10); ax_fin2.tick_params(colors=txt)
        for s in ax_fin2.spines.values(): s.set_edgecolor(txt)
        ax_fin2.spines['top'].set_visible(False); ax_fin2.spines['right'].set_visible(False); ax_fin2.set_xlim(right=ax_fin2.get_xlim()[1] * 1.30)

        fig_fin.tight_layout(); self.figuras_para_exportar.append(fig_fin)
        FigureCanvasTkAgg(fig_fin, master=self.tab_financeiro).draw(); FigureCanvasTkAgg(fig_fin, master=self.tab_financeiro).get_tk_widget().pack(fill="both", expand=True)

        # 5. MAPA DE PROCESSOS (DINÂMICO)
        sessao_reg, engine_reg = obter_sessao()
        try:
            from db import RegraClassificacao
            df_regras = pd.read_sql("SELECT categoria, tipo_regra, valor FROM regras_classificacao", engine_reg)
        except Exception:
            df_regras = pd.DataFrame(columns=['categoria', 'tipo_regra', 'valor'])
        finally:
            sessao_reg.close()

        if not df_regras.empty:
            regras_pasta = df_regras[df_regras['tipo_regra'] == 'Pasta'][['valor', 'categoria']].values.tolist()
            regras_kw = df_regras[df_regras['tipo_regra'] == 'Palavra-chave'][['valor', 'categoria']].values.tolist()
            regras_ext = df_regras[df_regras['tipo_regra'] == 'Extensão'][['valor', 'categoria']].values.tolist()
        else:
            regras_pasta, regras_kw, regras_ext = [], [], []

        def classificar_processo(doc):
            doc_min = str(doc).lower()
            for val, cat in regras_pasta:
                if val in doc_min: return cat
            for val, cat in regras_kw:
                if val in doc_min: return cat
            for val, cat in regras_ext:
                if val in doc_min: return cat
            return 'Outros'

        self.df_atual['processo'] = self.df_atual['documento'].apply(classificar_processo)
        df_proc = self.df_atual.groupby('processo')['paginas'].sum().sort_values(ascending=True)

        fig_proc, ax_proc = plt.subplots(figsize=(10, 5)); fig_proc.patch.set_facecolor(bg)
        ax_proc.set_facecolor(bg)

        if not df_proc.empty:
            barras_proc = ax_proc.barh(df_proc.index, df_proc.values, color='#3498DB')
            for b in barras_proc:
                w = b.get_width()
                if w > 0: ax_proc.annotate(f"{int(w)} págs", xy=(w, b.get_y() + b.get_height()/2), xytext=(5, 0), textcoords="offset points", ha='left', va='center', color=txt, fontsize=10, weight='bold')

        ax_proc.set_title('Consumo de Papel por Módulo do ERP (Dê um duplo clique na barra para detalhes)', color=txt, fontsize=12, pad=10)
        ax_proc.tick_params(colors=txt)
        for s in ax_proc.spines.values(): s.set_edgecolor(txt)
        ax_proc.spines['top'].set_visible(False); ax_proc.spines['right'].set_visible(False)
        if not df_proc.empty: ax_proc.set_xlim(right=ax_proc.get_xlim()[1] * 1.15)

        fig_proc.tight_layout(); self.figuras_para_exportar.append(fig_proc)
        
        canvas_proc = FigureCanvasTkAgg(fig_proc, master=self.tab_processos)
        canvas_proc.draw(); canvas_proc.get_tk_widget().pack(fill="both", expand=True)

        def on_click_proc(event):
            if event.dblclick and event.inaxes == ax_proc:
                if event.ydata is not None:
                    idx = int(round(event.ydata))
                    if 0 <= idx < len(df_proc.index):
                        categoria_clicada = df_proc.index[idx]
                        self.abrir_detalhes_processo(categoria_clicada)

        canvas_proc.mpl_connect('button_press_event', on_click_proc)

        # 6. RADAR DE SEGURANÇA / LGPD 
        df['dia_semana'] = df['data_hora'].dt.weekday
        
        def definir_alerta_seguranca(row):
            if row['dia_semana'] in [5, 6]: return "Fim de Semana"
            h, m = row['data_hora'].hour, row['data_hora'].minute
            minutos = (h * 60) + m
            if 660 <= minutos < 750: return "Horário de Almoço"
            elif not ((450 <= minutos < 660) or (750 <= minutos <= 1020)): return "Fora do Expediente"
            return ""
            
        df['motivo_alerta'] = df.apply(definir_alerta_seguranca, axis=1)
        df_risco = df[df['motivo_alerta'] != ""].sort_values('data_hora', ascending=False)
        
        for _, r in df_risco.iterrows():
            d_str = r['data_hora'].strftime("%d/%m/%Y %H:%M")
            self.tree_seg.insert("", "end", values=(d_str, r['nome_final'], r['motivo_alerta'], int(r['paginas']), r['documento']))