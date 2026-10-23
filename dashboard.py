import customtkinter as ctk
from tkinter import ttk
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from db import obter_sessao

class DashboardFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        
        self.tabview_dash = ctk.CTkTabview(self)
        self.tabview_dash.pack(fill="both", expand=True)

        self.tab_geral = self.tabview_dash.add("Visão Geral")
        self.tab_tempo = self.tabview_dash.add("Análise Temporal")
        self.tab_auditoria = self.tabview_dash.add("Auditoria & Desperdício")
        
        # Setup da Aba de Auditoria
        self.frame_audit_esq = ctk.CTkFrame(self.tab_auditoria, fg_color="transparent")
        self.frame_audit_esq.pack(side="left", fill="both", expand=True)
        
        self.frame_audit_dir = ctk.CTkFrame(self.tab_auditoria, fg_color="transparent")
        self.frame_audit_dir.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        # --- CORREÇÃO DO FUNDO BRANCO NAS TABELAS ---
        bg = "#2b2b2b" if ctk.get_appearance_mode() == "Dark" else "#ffffff"
        fg = "white" if bg == "#2b2b2b" else "black"
        style = ttk.Style()
        style.theme_use("default") 
        style.configure("Treeview", background=bg, foreground=fg, fieldbackground=bg, borderwidth=0)
        style.map('Treeview', background=[('selected', '#1f538d')])
        
        # --- TABELA 1: TOP 10 EXTENSOS ---
        self.frame_t1 = ctk.CTkFrame(self.frame_audit_dir)
        self.frame_t1.pack(fill="both", expand=True, pady=(0, 5))
        ctk.CTkLabel(self.frame_t1, text="Top 10 Documentos Mais Extensos (Volume Único)", font=ctk.CTkFont(weight="bold", size=13)).pack(pady=(5, 2))
        
        scroll_y1 = ttk.Scrollbar(self.frame_t1)
        scroll_y1.pack(side="right", fill="y")
        self.tree_top10 = ttk.Treeview(self.frame_t1, columns=("Data", "Usuario", "Pags", "Doc"), show="headings", yscrollcommand=scroll_y1.set)
        scroll_y1.config(command=self.tree_top10.yview)
        
        for c, w in zip(("Data", "Usuario", "Pags", "Doc"), (90, 100, 50, 200)):
            self.tree_top10.heading(c, text=c)
            self.tree_top10.column(c, width=w, anchor="center" if c != "Doc" else "w")
        self.tree_top10.pack(fill="both", expand=True, padx=5, pady=5)

        # --- TABELA 2: TOP 10 DUPLICADOS (NOVA AUDITORIA) ---
        self.frame_t2 = ctk.CTkFrame(self.frame_audit_dir)
        self.frame_t2.pack(fill="both", expand=True, pady=(5, 0))
        ctk.CTkLabel(self.frame_t2, text="Top 10 Impressões Duplicadas (Desperdício)", font=ctk.CTkFont(weight="bold", size=13)).pack(pady=(5, 2))
        
        scroll_y2 = ttk.Scrollbar(self.frame_t2)
        scroll_y2.pack(side="right", fill="y")
        self.tree_repetidos = ttk.Treeview(self.frame_t2, columns=("Qtd", "Usuario", "Total Pags", "Doc"), show="headings", yscrollcommand=scroll_y2.set)
        scroll_y2.config(command=self.tree_repetidos.yview)
        
        for c, w in zip(("Qtd", "Usuario", "Total Pags", "Doc"), (45, 100, 75, 220)):
            self.tree_repetidos.heading(c, text=c)
            self.tree_repetidos.column(c, width=w, anchor="center" if c != "Doc" else "w")
        self.tree_repetidos.pack(fill="both", expand=True, padx=5, pady=5)

    def extrair_extensao(self, doc):
        # Se não tiver ponto, assumimos que é impressão direta de software ou navegador
        if not isinstance(doc, str) or '.' not in doc: return 'Outros / Web'
        ext = doc.split('.')[-1].lower().strip()
        # Se a "extensão" tiver mais de 5 letras, não é um ficheiro real
        if len(ext) > 5 or not ext.isalnum(): return 'Outros / Web'
        return f".{ext}"

    def gerar_graficos(self):
        sessao, engine = obter_sessao()
        try:
            query = '''SELECT l.data_hora, l.terminal, COALESCE(m.nome_real, l.usuario) as nome_final, 
                       COALESCE(m.departamento, 'Sem Setor') as departamento, l.impressora, l.paginas, l.documento 
                       FROM logs_impressao l 
                       LEFT JOIN mapeamento_terminais m ON UPPER(l.terminal) = UPPER(m.terminal)'''
            df = pd.read_sql(query, engine)
        except Exception: return
        finally: sessao.close()

        if df.empty: return

        # Limpar gráficos e tabelas antigas
        for widget in self.tab_geral.winfo_children(): widget.destroy()
        for widget in self.tab_tempo.winfo_children(): widget.destroy()
        for widget in self.frame_audit_esq.winfo_children(): widget.destroy()
        for item in self.tree_top10.get_children(): self.tree_top10.delete(item)
        for item in self.tree_repetidos.get_children(): self.tree_repetidos.delete(item)

        bg = "#2b2b2b" if ctk.get_appearance_mode() == "Dark" else "#ffffff"
        txt = "white" if bg == "#2b2b2b" else "black"

        # ==========================================
        # 1. VISÃO GERAL
        # ==========================================
        df_dept = df.groupby('departamento')['paginas'].sum().sort_values(ascending=True)
        df_impressoras = df.groupby('impressora')['paginas'].sum().sort_values(ascending=False)
        df_usuarios_all = df.groupby('nome_final')['paginas'].sum().sort_values(ascending=True)

        fig_geral, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(10, 6)); fig_geral.patch.set_facecolor(bg)
        
        ax1.set_facecolor(bg)
        barras_dept = ax1.barh(df_dept.index, df_dept.values, color='#9B59B6')
        for b in barras_dept:
            w = b.get_width()
            if w > 0: ax1.annotate(f"{int(w)}", xy=(w, b.get_y() + b.get_height()/2), xytext=(5, 0), textcoords="offset points", ha='left', va='center', color=txt, fontsize=10, weight='bold')
        ax1.set_title('Consumo por Setor', color=txt, fontsize=11, pad=10); ax1.tick_params(colors=txt)
        for s in ax1.spines.values(): s.set_edgecolor(txt)
        ax1.spines['top'].set_visible(False); ax1.spines['right'].set_visible(False)
        ax1.set_xlim(right=ax1.get_xlim()[1] * 1.15)
        
        ax2.set_facecolor(bg)
        ax2.pie(df_impressoras.values, labels=df_impressoras.index, autopct='%1.1f%%', startangle=90, colors=['#3498DB', '#E67E22', '#F1C40F', '#95A5A6'], textprops={'color': txt, 'weight': 'bold'}, wedgeprops={'edgecolor': bg, 'linewidth': 2})
        ax2.set_title('Divisão por Equipamento', color=txt, fontsize=11, pad=10)

        ax3.set_facecolor(bg)
        barras_top = ax3.barh(df_usuarios_all.tail(5).index, df_usuarios_all.tail(5).values, color='#E74C3C')
        for b in barras_top:
            w = b.get_width()
            if w > 0: ax3.annotate(f"{int(w)}", xy=(w, b.get_y() + b.get_height()/2), xytext=(5, 0), textcoords="offset points", ha='left', va='center', color=txt, fontsize=10, weight='bold')
        ax3.set_title('Top 5: Mais Impressões', color=txt, fontsize=11, pad=10, weight='bold'); ax3.tick_params(colors=txt)
        for s in ax3.spines.values(): s.set_edgecolor(txt)
        ax3.spines['top'].set_visible(False); ax3.spines['right'].set_visible(False)
        ax3.set_xlim(right=ax3.get_xlim()[1] * 1.15)

        ax4.set_facecolor(bg)
        barras_bot = ax4.barh(df_usuarios_all.head(5).index, df_usuarios_all.head(5).values, color='#2FA572')
        for b in barras_bot:
            w = b.get_width()
            if w > 0: ax4.annotate(f"{int(w)}", xy=(w, b.get_y() + b.get_height()/2), xytext=(5, 0), textcoords="offset points", ha='left', va='center', color=txt, fontsize=10, weight='bold')
        ax4.set_title('Top 5: Menos Impressões', color=txt, fontsize=11, pad=10, weight='bold'); ax4.tick_params(colors=txt)
        for s in ax4.spines.values(): s.set_edgecolor(txt)
        ax4.spines['top'].set_visible(False); ax4.spines['right'].set_visible(False)
        ax4.set_xlim(right=ax4.get_xlim()[1] * 1.15)

        fig_geral.tight_layout(); FigureCanvasTkAgg(fig_geral, master=self.tab_geral).draw(); FigureCanvasTkAgg(fig_geral, master=self.tab_geral).get_tk_widget().pack(fill="both", expand=True)

        # ==========================================
        # 2. ANÁLISE TEMPORAL 
        # ==========================================
        df['data_hora'] = pd.to_datetime(df['data_hora'])
        
        df_dia = df.groupby(df['data_hora'].dt.strftime('%d/%m'))['paginas'].sum().sort_index()
        df_acumulado = df_dia.cumsum()
        
        df['hora'] = df['data_hora'].dt.hour
        df_hora = df.groupby('hora')['paginas'].sum().sort_index()

        fig_tempo, (ax_evol, ax_hora) = plt.subplots(2, 1, figsize=(10, 8))
        fig_tempo.patch.set_facecolor(bg)

        # Gráfico Superior
        ax_evol.set_facecolor(bg)
        x_dias = range(len(df_dia))
        
        ax_evol.bar(x_dias, df_dia.values, color='#316b93', label='Volume Diário', alpha=0.9)
        ax_evol.plot(x_dias, df_dia.values, marker='o', color='#0088ff', linewidth=2, label='Tendência Diária')
        ax_evol.plot(x_dias, df_acumulado.values, marker='o', color='#e74c3c', linewidth=2, label='Evolução Acumulada')
        
        ax_evol.set_xticks(x_dias)
        ax_evol.set_xticklabels(df_dia.index, rotation=45, color=txt)
        ax_evol.set_title('Evolução Diária e Crescimento Acumulado', color=txt, pad=15)
        ax_evol.tick_params(colors=txt)
        for s in ax_evol.spines.values(): s.set_edgecolor(txt)
        ax_evol.spines['top'].set_visible(False); ax_evol.spines['right'].set_visible(False)
        
        for i, v in enumerate(df_dia.values):
            ax_evol.text(i, v/2, str(int(v)), ha='center', va='center', color='white', weight='bold') 
            ax_evol.text(i, df_acumulado.values[i] + (df_acumulado.max()*0.03), str(int(df_acumulado.values[i])), ha='center', va='bottom', color=txt, weight='bold') 
        
        ax_evol.legend(loc='upper left', frameon=False, labelcolor=txt)

        # Gráfico Inferior
        ax_hora.set_facecolor(bg)
        barras_hora = ax_hora.bar(df_hora.index, df_hora.values, color='#e67e22')
        
        ax_hora.set_xticks(df_hora.index)
        ax_hora.set_xticklabels([f"{int(h)}h" for h in df_hora.index], color=txt)
        ax_hora.set_title('Horários de Maior Sobrecarga (Picos do Dia)', color=txt, pad=15)
        ax_hora.tick_params(colors=txt)
        for s in ax_hora.spines.values(): s.set_edgecolor(txt)
        ax_hora.spines['top'].set_visible(False); ax_hora.spines['right'].set_visible(False)
        
        for b in barras_hora:
            h = b.get_height()
            ax_hora.text(b.get_x() + b.get_width()/2, h + (df_hora.max()*0.02), str(int(h)), ha='center', va='bottom', color=txt, weight='bold')

        fig_tempo.tight_layout(); FigureCanvasTkAgg(fig_tempo, master=self.tab_tempo).draw(); FigureCanvasTkAgg(fig_tempo, master=self.tab_tempo).get_tk_widget().pack(fill="both", expand=True)

        # ==========================================
        # 3. AUDITORIA & DESPERDÍCIO (Rosca Limpa + Legenda Detalhada)
        # ==========================================
        df['extensao'] = df['documento'].apply(self.extrair_extensao)
        df_ext = df.groupby('extensao')['paginas'].sum().sort_values(ascending=False).head(6)
        
        fig_audit, ax_audit = plt.subplots(figsize=(7, 5))
        fig_audit.patch.set_facecolor(bg)
        ax_audit.set_facecolor(bg)
        
        if not df_ext.empty:
            # 1. Prepara os textos da legenda já com a percentagem incorporada
            total_paginas = df_ext.sum()
            legend_labels = [f"{idx} - {val/total_paginas*100:.1f}%" for idx, val in df_ext.items()]

            # 2. Desenha a rosca completamente limpa (sem autopct)
            wedges, texts = ax_audit.pie(
                df_ext.values, 
                startangle=90, 
                colors=['#E74C3C', '#8E44AD', '#3498DB', '#1ABC9C', '#F39C12', '#95A5A6'], 
                wedgeprops={'edgecolor': bg, 'linewidth': 2, 'width': 0.4}
            )
            
            # 3. Coloca a legenda formatada à direita
            ax_audit.legend(
                wedges, legend_labels,
                title="Formatos & Volume",
                loc="center left",
                bbox_to_anchor=(0.95, 0.5),
                frameon=False,
                labelcolor=txt
            )
                     
        ax_audit.set_title('Volume por Tipo de Ficheiro', color=txt, fontsize=12, pad=10, weight='bold')
        fig_audit.tight_layout()
        FigureCanvasTkAgg(fig_audit, master=self.frame_audit_esq).draw()
        FigureCanvasTkAgg(fig_audit, master=self.frame_audit_esq).get_tk_widget().pack(fill="both", expand=True)
      
        # 3A. Tabela Top 10 Extensos
        top_10 = df.nlargest(10, 'paginas')
        for _, r in top_10.iterrows():
            d_str = r['data_hora'].strftime("%d/%m %H:%M")
            self.tree_top10.insert("", "end", values=(d_str, r['nome_final'], int(r['paginas']), r['documento']))

        # 3B. Tabela Top 10 Duplicados
        df_duplicados = df.groupby(['documento', 'nome_final']).agg(
            vezes=('documento', 'count'),
            paginas_totais=('paginas', 'sum')
        ).reset_index()
        
        df_duplicados = df_duplicados[df_duplicados['vezes'] > 1].sort_values(by=['vezes', 'paginas_totais'], ascending=[False, False]).head(10)
        
        for _, r in df_duplicados.iterrows():
            self.tree_repetidos.insert("", "end", values=(f"{int(r['vezes'])}x", r['nome_final'], int(r['paginas_totais']), r['documento']))