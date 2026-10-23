# dashboard.py
import customtkinter as ctk
from tkinter import messagebox, filedialog
import pandas as pd
from datetime import datetime
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from tkcalendar import Calendar

from db import obter_sessao

def f_moeda(v): return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

class DashboardFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        self.frame_filtros = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_filtros.pack(fill="x", pady=(0, 5))
        
        ctk.CTkLabel(self.frame_filtros, text="Inicial:").pack(side="left", padx=(0, 5))
        self.entrada_data_ini = ctk.CTkEntry(self.frame_filtros, width=90, placeholder_text="DD/MM/AAAA"); self.entrada_data_ini.pack(side="left", padx=(0, 2))
        ctk.CTkButton(self.frame_filtros, text="📅", width=30, command=lambda: self.abrir_calendario(self.entrada_data_ini)).pack(side="left", padx=(0, 10))
        
        ctk.CTkLabel(self.frame_filtros, text="Final:").pack(side="left", padx=(0, 5))
        self.entrada_data_fim = ctk.CTkEntry(self.frame_filtros, width=90, placeholder_text="DD/MM/AAAA"); self.entrada_data_fim.pack(side="left", padx=(0, 2))
        ctk.CTkButton(self.frame_filtros, text="📅", width=30, command=lambda: self.abrir_calendario(self.entrada_data_fim)).pack(side="left", padx=(0, 10))

        ctk.CTkLabel(self.frame_filtros, text="Dept:").pack(side="left", padx=(0, 5))
        self.cb_dept = ctk.CTkComboBox(self.frame_filtros, width=120, values=["Todos"]); self.cb_dept.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(self.frame_filtros, text="Utilizador:").pack(side="left", padx=(0, 5))
        self.cb_usuario = ctk.CTkComboBox(self.frame_filtros, width=130, values=["Todos"]); self.cb_usuario.pack(side="left", padx=(0, 15))

        ctk.CTkButton(self.frame_filtros, text="Aplicar 📊", command=self.gerar_graficos, width=90, fg_color="#0052cc", hover_color="#003d99").pack(side="left")
        ctk.CTkButton(self.frame_filtros, text="Limpar", command=self.limpar_filtros, width=70, fg_color="#555", hover_color="#333").pack(side="left", padx=10)

        ctk.CTkButton(self.frame_filtros, text="Excel 📊", command=self.exportar_excel, width=80, fg_color="#1D6F42", hover_color="#144D2E").pack(side="right", padx=5)
        self.lbl_custo = ctk.CTkLabel(self.frame_filtros, text="Custo Total: R$ 0,00", font=ctk.CTkFont(weight="bold", size=14), text_color="#2FA572")
        self.lbl_custo.pack(side="right", padx=15)

        # MÓDULO ESG (IMPACTO AMBIENTAL COM LEGENDA)
        self.frame_esg_container = ctk.CTkFrame(self)
        self.frame_esg_container.pack(fill="x", padx=5, pady=(0, 10))

        self.frame_esg_metrics = ctk.CTkFrame(self.frame_esg_container, fg_color="transparent")
        self.frame_esg_metrics.pack(fill="x", pady=(5, 0))

        self.lbl_esg_arvores = ctk.CTkLabel(self.frame_esg_metrics, text="🌳 Árvores: 0", font=ctk.CTkFont(weight="bold", size=13), text_color="#2ECC71")
        self.lbl_esg_arvores.pack(side="left", expand=True)

        self.lbl_esg_agua = ctk.CTkLabel(self.frame_esg_metrics, text="💧 Água: 0 L", font=ctk.CTkFont(weight="bold", size=13), text_color="#3498DB")
        self.lbl_esg_agua.pack(side="left", expand=True)

        self.lbl_esg_co2 = ctk.CTkLabel(self.frame_esg_metrics, text="☁️ Pegada CO2: 0 Kg", font=ctk.CTkFont(weight="bold", size=13), text_color="#95A5A6")
        self.lbl_esg_co2.pack(side="left", expand=True)

        # LEGENDA ADICIONADA AQUI
        self.lbl_esg_legenda = ctk.CTkLabel(self.frame_esg_container, text="*Métrica Base: 1 Árvore = 8.333 folhas | 1 Folha = 10 Litros de Água | 1 Folha = 15g de Emissão de CO2", font=ctk.CTkFont(size=11, slant="italic"), text_color="gray")
        self.lbl_esg_legenda.pack(pady=(2, 5))

        self.tabs_graficos = ctk.CTkTabview(self)
        self.tabs_graficos.pack(fill="both", expand=True)
        self.tab_geral = self.tabs_graficos.add("Visão Geral (Rankings)")
        self.tab_tempo = self.tabs_graficos.add("Análise Temporal e Evolução")
        self.df_atual = pd.DataFrame()
        self.carregar_comboboxes()

    def carregar_comboboxes(self):
        sessao, engine = obter_sessao()
        try:
            df = pd.read_sql('''SELECT DISTINCT COALESCE(m.departamento, 'Sem Setor') as dept, COALESCE(m.nome_real, l.usuario) as usr FROM logs_impressao l LEFT JOIN mapeamento_terminais m ON UPPER(l.terminal) = UPPER(m.terminal)''', engine)
            self.cb_dept.configure(values=["Todos"] + sorted([str(x) for x in df['dept'].dropna().unique() if str(x).strip()]))
            self.cb_usuario.configure(values=["Todos"] + sorted([str(x) for x in df['usr'].dropna().unique() if str(x).strip()]))
            self.cb_dept.set("Todos"); self.cb_usuario.set("Todos")
        except Exception: pass
        finally: sessao.close()

    def abrir_calendario(self, entry_alvo):
        janela_cal = ctk.CTkToplevel(self); janela_cal.title("Data"); janela_cal.geometry("300x300"); janela_cal.attributes("-topmost", True); janela_cal.grab_set()
        bg_color, fg_color = ("#2b2b2b", "white") if ctk.get_appearance_mode() == "Dark" else ("white", "black")
        cal = Calendar(janela_cal, selectmode='day', date_pattern='dd/mm/yyyy', background="#1f538d", headersbackground="#1f538d", normalbackground=bg_color, foreground=fg_color, normalforeground=fg_color, headersforeground="white")
        cal.pack(pady=10, padx=10, fill="both", expand=True)
        ctk.CTkButton(janela_cal, text="Confirmar 📅", command=lambda: [entry_alvo.delete(0, 'end'), entry_alvo.insert(0, cal.get_date()), janela_cal.destroy()]).pack(pady=10)

    def limpar_filtros(self):
        self.entrada_data_ini.delete(0, 'end'); self.entrada_data_fim.delete(0, 'end'); self.cb_dept.set("Todos"); self.cb_usuario.set("Todos")
        self.gerar_graficos()

    def exportar_excel(self):
        if self.df_atual.empty: return messagebox.showwarning("Aviso", "Não há dados para exportar.")
        cam = filedialog.asksaveasfilename(defaultextension=".xlsx", initialfile="Dashboard_Dados.xlsx", filetypes=[("Excel", "*.xlsx")])
        if cam: 
            self.df_atual.rename(columns={'data_hora': 'Data/Hora', 'usuario_final': 'Utilizador', 'departamento': 'Departamento', 'impressora': 'Impressora', 'paginas': 'Páginas', 'custo_total': 'Custo Estimado (R$)'}).to_excel(cam, index=False)
            messagebox.showinfo("Sucesso", "Excel exportado!")

    def gerar_graficos(self):
        for w in self.tab_geral.winfo_children(): w.destroy()
        for w in self.tab_tempo.winfo_children(): w.destroy()
        plt.close('all') 

        d_ini, d_fim, dept, usu = self.entrada_data_ini.get().strip(), self.entrada_data_fim.get().strip(), self.cb_dept.get().strip(), self.cb_usuario.get().strip()
        sessao, engine = obter_sessao()
        try:
            query = '''
                SELECT l.data_hora, COALESCE(m.nome_real, l.usuario) as usuario_final, COALESCE(m.departamento, 'Sem Setor') as departamento, l.impressora, l.paginas, COALESCE(i.custo_pagina, 0.0) as custo_pagina
                FROM logs_impressao l
                LEFT JOIN mapeamento_terminais m ON UPPER(l.terminal) = UPPER(m.terminal)
                LEFT JOIN configuracao_impressoras i ON UPPER(l.impressora) = UPPER(i.nome_impressora) WHERE 1=1
            '''
            if d_ini: query += f" AND l.data_hora >= '{datetime.strptime(d_ini, '%d/%m/%Y').strftime('%Y-%m-%d 00:00:00')}'"
            if d_fim: query += f" AND l.data_hora <= '{datetime.strptime(d_fim, '%d/%m/%Y').strftime('%Y-%m-%d 23:59:59')}'"
            if dept and dept != "Todos": query += f" AND LOWER(COALESCE(m.departamento, 'Sem Setor')) = LOWER('{dept}')"
            if usu and usu != "Todos": query += f" AND LOWER(COALESCE(m.nome_real, l.usuario)) = LOWER('{usu}')"

            df = pd.read_sql(query, engine)
            if df.empty: 
                self.lbl_custo.configure(text="Custo Total: R$ 0,00"); self.df_atual = df
                self.lbl_esg_arvores.configure(text="🌳 Árvores: 0")
                self.lbl_esg_agua.configure(text="💧 Água: 0 L")
                self.lbl_esg_co2.configure(text="☁️ Pegada CO2: 0 Kg")
                ctk.CTkLabel(self.tab_geral, text="Sem dados.", text_color="gray").pack(expand=True)
                return

            df['custo_total'] = df['paginas'] * df['custo_pagina']
            self.df_atual = df
            self.lbl_custo.configure(text=f"Custo Total: {f_moeda(df['custo_total'].sum())}")

            pags = df['paginas'].sum()
            arvores = pags / 8333.0
            agua = pags * 10.0
            co2 = pags * 0.015

            self.lbl_esg_arvores.configure(text=f"🌳 Árvores Consumidas: {arvores:.2f}")
            self.lbl_esg_agua.configure(text=f"💧 Consumo de Água: {agua:,.0f} L".replace(",", "X").replace(".", ",").replace("X", "."))
            self.lbl_esg_co2.configure(text=f"☁️ Pegada de CO2: {co2:,.1f} Kg".replace(",", "X").replace(".", ",").replace("X", "."))

            df['data_hora'] = pd.to_datetime(df['data_hora'])
            bg, txt = ('#2b2b2b', 'white') if ctk.get_appearance_mode() == "Dark" else ('#ebebeb', 'black')

            df_dept = df.groupby('departamento')['paginas'].sum().sort_values(ascending=True)
            df_impressoras = df.groupby('impressora')['paginas'].sum()
            df_usuarios_all = df.groupby('usuario_final')['paginas'].sum().sort_values(ascending=True)
            
            fig_geral, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(10, 6)); fig_geral.patch.set_facecolor(bg)
            
            ax1.set_facecolor(bg); ax1.barh(df_dept.index, df_dept.values, color='#9B59B6'); ax1.set_title('Consumo por Setor', color=txt, fontsize=11, pad=10); ax1.tick_params(colors=txt)
            for s in ax1.spines.values(): s.set_edgecolor(txt)
            ax1.spines['top'].set_visible(False); ax1.spines['right'].set_visible(False)
            
            ax2.set_facecolor(bg); ax2.pie(df_impressoras.values, labels=df_impressoras.index, autopct='%1.1f%%', startangle=90, colors=['#3498DB', '#E67E22', '#F1C40F', '#95A5A6'], textprops={'color': txt, 'weight': 'bold'}, wedgeprops={'edgecolor': bg, 'linewidth': 2}); ax2.set_title('Divisão por Impressora', color=txt, fontsize=11, pad=10)

            ax3.set_facecolor(bg); ax3.barh(df_usuarios_all.tail(5).index, df_usuarios_all.tail(5).values, color='#E74C3C'); ax3.set_title('Top 5: Mais Impressões', color=txt, fontsize=11, pad=10, weight='bold'); ax3.tick_params(colors=txt)
            for s in ax3.spines.values(): s.set_edgecolor(txt)
            ax3.spines['top'].set_visible(False); ax3.spines['right'].set_visible(False)

            ax4.set_facecolor(bg); ax4.barh(df_usuarios_all.head(5).index, df_usuarios_all.head(5).values, color='#2FA572'); ax4.set_title('Top 5: Menos Impressões', color=txt, fontsize=11, pad=10, weight='bold'); ax4.tick_params(colors=txt)
            for s in ax4.spines.values(): s.set_edgecolor(txt)
            ax4.spines['top'].set_visible(False); ax4.spines['right'].set_visible(False)

            fig_geral.tight_layout(); FigureCanvasTkAgg(fig_geral, master=self.tab_geral).draw(); FigureCanvasTkAgg(fig_geral, master=self.tab_geral).get_tk_widget().pack(fill="both", expand=True)

            fig_tempo, (ax5, ax6) = plt.subplots(2, 1, figsize=(10, 6)); fig_tempo.patch.set_facecolor(bg)
            df['data_apenas'] = df['data_hora'].dt.date
            df_dias = df.groupby('data_apenas')['paginas'].sum().sort_index(); rotulos_x = [d.strftime('%d/%m') for d in df_dias.index]
            df_dias_acumulado = df_dias.cumsum() 

            ax5.set_facecolor(bg)
            cor_b = '#316a92' if ctk.get_appearance_mode() == "Dark" else '#85b5d9' 
            barras_evo = ax5.bar(rotulos_x, df_dias.values, color=cor_b, label='Volume Diário')
            for b in barras_evo:
                h = b.get_height()
                if h > 0: ax5.annotate(f"{int(h)}", xy=(b.get_x() + b.get_width()/2, h/2), ha='center', va='center', color=txt, fontsize=10)

            ax5.plot(rotulos_x, df_dias.values, color='#0088ff', marker='o', linewidth=2.5, label='Tendência Diária')
            ax5.plot(rotulos_x, df_dias_acumulado.values, color='#E74C3C', marker='o', linewidth=2.5, label='Evolução Acumulada')
            if not df_dias_acumulado.empty: ax5.annotate(f"{int(df_dias_acumulado.values[-1])}", xy=(rotulos_x[-1], df_dias_acumulado.values[-1]), xytext=(0, 6), textcoords="offset points", ha='center', va='bottom', color=txt, weight='bold')

            ax5.set_title(f"Evolução Diária e Crescimento (Utilizador: {usu})" if usu != "Todos" else "Evolução Diária e Crescimento Acumulado", color=txt, fontsize=12, pad=10)
            ax5.tick_params(colors=txt, axis='x', rotation=45)
            for s in ax5.spines.values(): s.set_edgecolor(txt)
            ax5.spines['top'].set_visible(False); ax5.spines['right'].set_visible(False)
            leg = ax5.legend(loc='upper left', frameon=False)
            for t in leg.get_texts(): t.set_color(txt)

            df['hora'] = df['data_hora'].dt.hour
            df_horas = df.groupby('hora')['paginas'].sum()
            ax6.set_facecolor(bg)
            barras_h = ax6.bar(df_horas.index, df_horas.values, color='#E67E22')
            for b in barras_h:
                h = b.get_height()
                if h > 0: ax6.annotate(f"{int(h)}", xy=(b.get_x() + b.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', color=txt, fontsize=10)

            ax6.set_title('Horários de Maior Sobrecarga (Picos do Dia)', color=txt, fontsize=12, pad=10)
            ax6.tick_params(colors=txt)
            for s in ax6.spines.values(): s.set_edgecolor(txt)
            ax6.spines['top'].set_visible(False); ax6.spines['right'].set_visible(False)
            ax6.set_xticks(df_horas.index); ax6.set_xticklabels([f"{h}h" for h in df_horas.index])

            fig_tempo.tight_layout(); FigureCanvasTkAgg(fig_tempo, master=self.tab_tempo).draw(); FigureCanvasTkAgg(fig_tempo, master=self.tab_tempo).get_tk_widget().pack(fill="both", expand=True)
            
        except Exception as e: messagebox.showerror("Erro", str(e))
        finally: sessao.close()