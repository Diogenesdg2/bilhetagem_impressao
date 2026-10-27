import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
from datetime import datetime, timedelta
from tkcalendar import Calendar
import matplotlib.pyplot as plt

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import tempfile
import os

from db import obter_sessao, MapeamentoTerminal, ConfiguracaoImpressora, ConfiguracaoSistema, HistoricoEnvio
from etl import processar_csv_para_banco
from dashboard import DashboardFrame

def f_moeda(v): return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AppImpressoes(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Viman Contabilidade - Sistema de Bilhetagem Automático")
        self.geometry("1350x780") 
        self.protocol("WM_DELETE_WINDOW", self.encerrar_sistema)
        
        self.frame_header = ctk.CTkFrame(self, fg_color="transparent"); self.frame_header.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(self.frame_header, text="Controlo Mensal de Impressões", font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")
        self.switch_tema = ctk.CTkSwitch(self.frame_header, text="Modo Escuro", command=self.alternar_tema); self.switch_tema.pack(side="right"); self.switch_tema.select()
        
        self.frame_toolbar = ctk.CTkFrame(self, fg_color="transparent"); self.frame_toolbar.pack(fill="x", padx=20, pady=5)
        ctk.CTkButton(self.frame_toolbar, text="Importar CSV 📂", command=self.importar_arquivo_csv, fg_color="#2FA572", hover_color="#1D7850", width=140).pack(side="left")
        ctk.CTkButton(self.frame_toolbar, text="Setores e Vínculos 👤", command=self.abrir_janela_mapeamento, fg_color="#0052cc", hover_color="#003d99", width=170).pack(side="left", padx=10)
        ctk.CTkButton(self.frame_toolbar, text="Custos de Impressão 🖨️", command=self.abrir_janela_custos, fg_color="#E67E22", hover_color="#D35400", width=180).pack(side="left", padx=(0, 10))
        
        ctk.CTkButton(self.frame_toolbar, text="⚙️ Configurações", command=self.abrir_janela_configuracoes, fg_color="#8E44AD", hover_color="#732D91", width=160).pack(side="left")

        self.titulos_originais_rel = {"Data": "Data", "Term": "Terminal", "Nome": "Nome", "Setor": "Departamento", "Imp": "Imp", "Pags": "Pags", "Custo": "Custo (R$)", "Doc": "Doc"}

        self.tabview_principal = ctk.CTkTabview(self)
        self.tabview_principal.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.tab_dashboard = self.tabview_principal.add("📊 Dashboard Visuais")
        self.tab_relatorio = self.tabview_principal.add("📄 Registos Detalhados")
        self.tab_exportacao = self.tabview_principal.add("📑 Central de Relatórios")
        
        self.visao_dashboard = DashboardFrame(self.tab_dashboard); self.visao_dashboard.pack(fill="both", expand=True)
        
        self.montar_aba_relatorio()
        self.montar_aba_exportacao()
        self.carregar_valores_comboboxes() 
        self.visao_dashboard.gerar_graficos()
        self.carregar_dados_relatorio()

    def pesquisar_nos_registros(self, nome_documento):
        self.tabview_principal.set("📄 Registos Detalhados")
        self.entrada_busca_doc.delete(0, 'end')
        self.entrada_busca_doc.insert(0, nome_documento)
        self.carregar_dados_relatorio()

    def encerrar_sistema(self):
        plt.close('all'); self.quit(); self.destroy()

    def alternar_tema(self):
        bg, fg = ("#2b2b2b", "white") if self.switch_tema.get() == 1 else ("#ffffff", "black")
        ctk.set_appearance_mode("Dark" if self.switch_tema.get() == 1 else "Light")
        ttk.Style(self).configure("Treeview", background=bg, foreground=fg, fieldbackground=bg)
        self.visao_dashboard.gerar_graficos()

    def importar_arquivo_csv(self):
        sessao, _ = obter_sessao()
        cfg = sessao.query(ConfiguracaoSistema).first()
        pasta_cfg = cfg.caminho_csv if cfg and cfg.caminho_csv else r"D:\Relatorios"
        sessao.close()

        if not os.path.exists(pasta_cfg):
            return messagebox.showerror("Erro de Diretório", f"A pasta configurada não foi encontrada:\n{pasta_cfg}\n\nVerifique em '⚙️ Configurações'.")

        fich_csv = [os.path.join(pasta_cfg, f) for f in os.listdir(pasta_cfg) if f.lower().endswith('.csv')]
        
        if not fich_csv:
            return messagebox.showwarning("Aviso", f"Nenhum ficheiro .csv foi encontrado na pasta:\n{pasta_cfg}")

        caminho_mais_recente = max(fich_csv, key=os.path.getmtime)

        try:
            sessao, engine = obter_sessao()
            imp, ign = processar_csv_para_banco(caminho_mais_recente, engine)
            messagebox.showinfo("Importação Direta", f"📁 Ficheiro lido: {os.path.basename(caminho_mais_recente)}\n\n✅ Novos registos: {imp}\n⚠️ Ignorados (duplicados): {ign}")
            self.visao_dashboard.gerar_graficos()
            self.carregar_valores_comboboxes()
            self.carregar_dados_relatorio()
        except Exception as e: 
            messagebox.showerror("Erro de Importação", str(e))

    def abrir_calendario(self, entry_alvo):
        janela_cal = ctk.CTkToplevel(self); janela_cal.title("Data"); janela_cal.geometry("300x300"); janela_cal.attributes("-topmost", True); janela_cal.grab_set()
        bg, fg = ("#2b2b2b", "white") if self.switch_tema.get() == 1 else ("white", "black")
        cal = Calendar(janela_cal, selectmode='day', date_pattern='dd/mm/yyyy', background="#1f538d", headersbackground="#1f538d", normalbackground=bg, foreground=fg, normalforeground=fg, headersforeground="white")
        cal.pack(pady=10, padx=10, fill="both", expand=True)
        ctk.CTkButton(janela_cal, text="Confirmar 📅", command=lambda: [entry_alvo.delete(0, 'end'), entry_alvo.insert(0, cal.get_date()), janela_cal.destroy()]).pack(pady=10)

    def carregar_valores_comboboxes(self):
        sessao, engine = obter_sessao()
        try:
            df = pd.read_sql('''SELECT DISTINCT COALESCE(m.departamento, 'Sem Setor') as dept, COALESCE(m.nome_real, l.usuario) as usr, l.impressora as imp FROM logs_impressao l LEFT JOIN mapeamento_terminais m ON UPPER(l.terminal) = UPPER(m.terminal)''', engine)
            depts = ["Todos"] + sorted([str(x) for x in df['dept'].dropna().unique() if str(x).strip()])
            usrs = ["Todos"] + sorted([str(x) for x in df['usr'].dropna().unique() if str(x).strip()])
            imps = ["Todos"] + sorted([str(x) for x in df['imp'].dropna().unique() if str(x).strip()])
            if hasattr(self, 'cb_dept'):
                self.cb_dept.configure(values=depts); self.cb_dept.set("Todos")
                self.cb_usuario.configure(values=usrs); self.cb_usuario.set("Todos")
                self.cb_impressora.configure(values=imps); self.cb_impressora.set("Todos")
            if hasattr(self, 'cb_rel_dept'):
                self.cb_rel_dept.configure(values=depts); self.cb_rel_dept.set("Todos")
                self.cb_rel_usuario.configure(values=usrs); self.cb_rel_usuario.set("Todos")
                self.cb_rel_impressora.configure(values=imps); self.cb_rel_impressora.set("Todos")
            if hasattr(self, 'cb_dept_audit'):
                self.cb_dept_audit.configure(values=depts); self.cb_dept_audit.set("Todos")
        except Exception: pass
        finally: sessao.close()

    def ordenar_coluna_treeview(self, tree, col, reverse):
        for c in tree["columns"]:
            if c in self.titulos_originais_rel:
                tree.heading(c, text=self.titulos_originais_rel[c], command=lambda _c=c: self.ordenar_coluna_treeview(tree, _c, False))
        l = [(tree.set(k, col), k) for k in tree.get_children('')]
        def preparar_valor(val):
            val_str = str(val).strip()
            if not val_str or val_str == "-": return 0
            try: return datetime.strptime(val_str, "%d/%m/%Y %H:%M")
            except ValueError: pass
            if val_str.startswith("R$"):
                try: return float(val_str.replace("R$ ", "").replace(".", "").replace(",", "."))
                except: pass
            try: return int(val_str)
            except ValueError: pass
            return val_str.lower()
        try: l.sort(key=lambda t: preparar_valor(t[0]), reverse=reverse)
        except Exception: l.sort(reverse=reverse)
        for index, (val, k) in enumerate(l): tree.move(k, '', index)
        texto_atual = self.titulos_originais_rel.get(col, col)
        seta = " ▼" if reverse else " ▲"
        tree.heading(col, text=texto_atual + seta, command=lambda _c=col: self.ordenar_coluna_treeview(tree, _c, not reverse))


    # =========================================================
    # ABA 2: REGISTOS DETALHADOS 
    # =========================================================
    def montar_aba_relatorio(self):
        f_filt = ctk.CTkFrame(self.tab_relatorio, fg_color="transparent"); f_filt.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(f_filt, text="Data Inicial:").grid(row=0, column=0, padx=(0, 5), pady=5, sticky="w")
        self.entrada_data_ini = ctk.CTkEntry(f_filt, width=90, placeholder_text="DD/MM/AAAA"); self.entrada_data_ini.grid(row=0, column=1, padx=(0, 2), pady=5, sticky="w")
        ctk.CTkButton(f_filt, text="📅", width=30, command=lambda: self.abrir_calendario(self.entrada_data_ini)).grid(row=0, column=2, padx=(0, 10), pady=5, sticky="w")
        
        ctk.CTkLabel(f_filt, text="Data Final:").grid(row=0, column=3, padx=(0, 5), pady=5, sticky="w")
        self.entrada_data_fim = ctk.CTkEntry(f_filt, width=90, placeholder_text="DD/MM/AAAA"); self.entrada_data_fim.grid(row=0, column=4, padx=(0, 2), pady=5, sticky="w")
        ctk.CTkButton(f_filt, text="📅", width=30, command=lambda: self.abrir_calendario(self.entrada_data_fim)).grid(row=0, column=5, padx=(0, 10), pady=5, sticky="w")
        
        ctk.CTkLabel(f_filt, text="Departamento:").grid(row=0, column=6, padx=(0, 5), pady=5, sticky="w")
        self.cb_rel_dept = ctk.CTkComboBox(f_filt, width=150, values=["Todos"]); self.cb_rel_dept.grid(row=0, column=7, padx=(0, 10), pady=5, sticky="w")
        
        ctk.CTkLabel(f_filt, text="Buscar Documento:").grid(row=0, column=8, padx=(10, 5), pady=5, sticky="w")
        self.entrada_busca_doc = ctk.CTkEntry(f_filt, width=160, placeholder_text="Ex: rescisao, nfe")
        self.entrada_busca_doc.grid(row=0, column=9, padx=(0, 10), pady=5, sticky="w")

        ctk.CTkLabel(f_filt, text="Utilizador:").grid(row=1, column=0, padx=(0, 5), pady=5, sticky="w")
        self.cb_rel_usuario = ctk.CTkComboBox(f_filt, width=150, values=["Todos"]); self.cb_rel_usuario.grid(row=1, column=1, columnspan=2, padx=(0, 10), pady=5, sticky="w")
        
        ctk.CTkLabel(f_filt, text="Impressora:").grid(row=1, column=3, padx=(0, 5), pady=5, sticky="w")
        self.cb_rel_impressora = ctk.CTkComboBox(f_filt, width=150, values=["Todos"]); self.cb_rel_impressora.grid(row=1, column=4, columnspan=2, padx=(0, 10), pady=5, sticky="w")
        
        ctk.CTkButton(f_filt, text="Filtrar 🔍", command=self.carregar_dados_relatorio, width=100, fg_color="#2FA572", hover_color="#1D7850").grid(row=1, column=6, padx=5, pady=5, sticky="w")
        ctk.CTkButton(f_filt, text="Limpar", command=self.limpar_filtros_relatorio, width=70, fg_color="#555", hover_color="#333").grid(row=1, column=7, padx=5, pady=5, sticky="w")
        ctk.CTkButton(f_filt, text="Desfazer Ordenação ↺", command=self.carregar_dados_relatorio, width=150, fg_color="#E67E22", hover_color="#D35400").grid(row=1, column=8, columnspan=2, padx=5, pady=5, sticky="w")

        f_rod = ctk.CTkFrame(self.tab_relatorio, fg_color="transparent"); f_rod.pack(side="bottom", fill="x", pady=(10, 0))
        self.lbl_total_rel = ctk.CTkLabel(f_rod, text="Páginas: 0 | Custo: R$ 0,00", font=ctk.CTkFont(size=16, weight="bold"), text_color="#2FA572"); self.lbl_total_rel.pack(side="right", padx=10)

        bg, fg = ("#2b2b2b", "white") if self.switch_tema.get() == 1 else ("#ffffff", "black")
        ttk.Style(self).configure("Treeview", background=bg, foreground=fg, fieldbackground=bg, borderwidth=0); ttk.Style(self).map('Treeview', background=[('selected', '#1f538d')])
        f_tab = ctk.CTkFrame(self.tab_relatorio); f_tab.pack(fill="both", expand=True); scroll_y = ttk.Scrollbar(f_tab); scroll_y.pack(side="right", fill="y")
        self.tree_rel = ttk.Treeview(f_tab, columns=("Data", "Term", "Nome", "Setor", "Imp", "Pags", "Custo", "Doc"), show="headings", yscrollcommand=scroll_y.set); scroll_y.config(command=self.tree_rel.yview)
        
        for col, w in zip(("Data", "Term", "Nome", "Setor", "Imp", "Pags", "Custo", "Doc"), (120, 80, 130, 110, 90, 40, 70, 200)):
            self.tree_rel.heading(col, text=self.titulos_originais_rel[col], command=lambda c=col: self.ordenar_coluna_treeview(self.tree_rel, c, False))
            self.tree_rel.column(col, width=w, anchor="center" if col not in ["Nome", "Doc", "Setor"] else "w")
        self.tree_rel.pack(fill="both", expand=True)

    def carregar_dados_relatorio(self):
        for c in self.tree_rel["columns"]:
            if c in self.titulos_originais_rel:
                self.tree_rel.heading(c, text=self.titulos_originais_rel[c], command=lambda _c=c: self.ordenar_coluna_treeview(self.tree_rel, _c, False))

        d_ini, d_fim, usu, imp, dept = self.entrada_data_ini.get().strip(), self.entrada_data_fim.get().strip(), self.cb_rel_usuario.get(), self.cb_rel_impressora.get(), self.cb_rel_dept.get()
        busca_doc = self.entrada_busca_doc.get().strip().lower()

        query = '''SELECT l.data_hora, l.terminal, COALESCE(m.nome_real, l.usuario) as nome_final, COALESCE(m.departamento, 'Sem Setor') as departamento, l.impressora, l.paginas, COALESCE(i.custo_pagina, 0.0) as custo_pagina, l.documento 
                   FROM logs_impressao l LEFT JOIN mapeamento_terminais m ON UPPER(l.terminal) = UPPER(m.terminal) LEFT JOIN configuracao_impressoras i ON UPPER(l.impressora) = UPPER(i.nome_impressora) WHERE 1=1'''
        try:
            if d_ini: query += f" AND l.data_hora >= '{datetime.strptime(d_ini, '%d/%m/%Y').strftime('%Y-%m-%d 00:00:00')}'"
            if d_fim: query += f" AND l.data_hora <= '{datetime.strptime(d_fim, '%d/%m/%Y').strftime('%Y-%m-%d 23:59:59')}'"
            if usu and usu != "Todos": query += f" AND LOWER(COALESCE(m.nome_real, l.usuario)) = LOWER('{usu}')"
            if imp and imp != "Todos": query += f" AND LOWER(l.impressora) = LOWER('{imp}')"
            if dept and dept != "Todos": query += f" AND LOWER(COALESCE(m.departamento, 'Sem Setor')) = LOWER('{dept}')"
            if busca_doc: query += f" AND LOWER(l.documento) LIKE '%{busca_doc}%'"
        except ValueError: return messagebox.showerror("Erro", "Formato de data inválido.")

        query += " ORDER BY l.data_hora DESC"
        for i in self.tree_rel.get_children(): self.tree_rel.delete(i)

        sessao, engine = obter_sessao()
        try:
            df = pd.read_sql(query, engine); df['custo_total'] = df['paginas'] * df['custo_pagina']
            self.lbl_total_rel.configure(text=f"Total Páginas: {int(df['paginas'].sum()) if not df.empty else 0} | Custo: {f_moeda(df['custo_total'].sum())}")
            for _, r in df.iterrows(): self.tree_rel.insert("", "end", values=(pd.to_datetime(r['data_hora']).strftime("%d/%m/%Y %H:%M"), r['terminal'], r['nome_final'], r['departamento'], r['impressora'], r['paginas'], f_moeda(r['custo_total']), r['documento']))
        except Exception as e: messagebox.showerror("Erro", str(e))
        finally: sessao.close()

    def limpar_filtros_relatorio(self):
        self.entrada_data_ini.delete(0, 'end'); self.entrada_data_fim.delete(0, 'end'); self.cb_rel_usuario.set("Todos"); self.cb_rel_impressora.set("Todos"); self.cb_rel_dept.set("Todos"); 
        self.entrada_busca_doc.delete(0, 'end')
        self.carregar_dados_relatorio()


    # =========================================================
    # ABA 3 E CENTRAL DE RELATÓRIOS
    # =========================================================
    def montar_aba_exportacao(self):
        f_scr = ctk.CTkScrollableFrame(self.tab_exportacao, fg_color="transparent")
        f_scr.pack(fill="both", expand=True, padx=10, pady=5)

        f_per = ctk.CTkFrame(f_scr); f_per.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(f_per, text="1. Filtro Global (Período)", font=ctk.CTkFont(weight="bold", size=14)).pack(anchor="w", padx=15, pady=(10, 0))
        f_d = ctk.CTkFrame(f_per, fg_color="transparent"); f_d.pack(pady=10)
        ctk.CTkLabel(f_d, text="Inicial:").grid(row=0, column=0, padx=5); self.pdf_data_ini = ctk.CTkEntry(f_d, width=110, placeholder_text="DD/MM/AAAA"); self.pdf_data_ini.grid(row=0, column=1, padx=5)
        ctk.CTkButton(f_d, text="📅", width=30, command=lambda: self.abrir_calendario(self.pdf_data_ini)).grid(row=0, column=2, padx=(0, 20))
        ctk.CTkLabel(f_d, text="Final:").grid(row=0, column=3, padx=5); self.pdf_data_fim = ctk.CTkEntry(f_d, width=110, placeholder_text="DD/MM/AAAA"); self.pdf_data_fim.grid(row=0, column=4, padx=5)
        ctk.CTkButton(f_d, text="📅", width=30, command=lambda: self.abrir_calendario(self.pdf_data_fim)).grid(row=0, column=5, padx=5)

        f_sint = ctk.CTkFrame(f_scr); f_sint.pack(fill="x", pady=10)
        ctk.CTkLabel(f_sint, text="2. Relatórios de Resumo", font=ctk.CTkFont(weight="bold", size=14)).pack(anchor="w", padx=15, pady=(10, 0))
        f_bs = ctk.CTkFrame(f_sint, fg_color="transparent"); f_bs.pack(pady=10)
        ctk.CTkLabel(f_bs, text="Por Equipamento:").grid(row=0, column=0, padx=10, pady=5, sticky="e")
        ctk.CTkButton(f_bs, text="👁️ Visão", command=lambda: self.visualizar_central("impressoras"), fg_color="#3498DB", hover_color="#2980B9", width=120).grid(row=0, column=1, padx=5, pady=5)
        ctk.CTkButton(f_bs, text="📄 PDF", command=lambda: self.gerar_arquivo_central("impressoras", "pdf"), fg_color="#c23b22", hover_color="#8f2a18", width=120).grid(row=0, column=2, padx=5, pady=5)
        ctk.CTkButton(f_bs, text="📊 Excel", command=lambda: self.gerar_arquivo_central("impressoras", "excel"), fg_color="#1D6F42", hover_color="#144D2E", width=120).grid(row=0, column=3, padx=5, pady=5)
        
        ctk.CTkLabel(f_bs, text="Por Utilizador:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        ctk.CTkButton(f_bs, text="👁️ Visão", command=lambda: self.visualizar_central("usuarios"), fg_color="#3498DB", hover_color="#2980B9", width=120).grid(row=1, column=1, padx=5, pady=5)
        ctk.CTkButton(f_bs, text="📄 PDF", command=lambda: self.gerar_arquivo_central("usuarios", "pdf"), fg_color="#2FA572", hover_color="#1D7850", width=120).grid(row=1, column=2, padx=5, pady=5)
        ctk.CTkButton(f_bs, text="📊 Excel", command=lambda: self.gerar_arquivo_central("usuarios", "excel"), fg_color="#1D6F42", hover_color="#144D2E", width=120).grid(row=1, column=3, padx=5, pady=5)
        ctk.CTkLabel(f_bs, text="Ordem:").grid(row=1, column=4, padx=(15, 5), pady=5); self.pdf_ordenacao = ctk.CTkOptionMenu(f_bs, values=["Maior Volume", "Ordem Alfabética"], width=130); self.pdf_ordenacao.grid(row=1, column=5, padx=5, pady=5)

        f_audit = ctk.CTkFrame(f_scr); f_audit.pack(fill="x", pady=10)
        ctk.CTkLabel(f_audit, text="3. Auditoria e Desperdício", font=ctk.CTkFont(weight="bold", size=14)).pack(anchor="w", padx=15, pady=(10, 0))
        f_fa = ctk.CTkFrame(f_audit, fg_color="transparent"); f_fa.pack(pady=5)
        ctk.CTkLabel(f_fa, text="Departamento:").grid(row=0, column=0, padx=5, pady=5)
        self.cb_dept_audit = ctk.CTkComboBox(f_fa, width=150, values=["Todos"]); self.cb_dept_audit.grid(row=0, column=1, padx=5, pady=5)
        
        f_ba = ctk.CTkFrame(f_audit, fg_color="transparent"); f_ba.pack(pady=(5, 10))
        ctk.CTkLabel(f_ba, text="Doc. Extensos:").grid(row=0, column=0, padx=10, pady=5, sticky="e")
        ctk.CTkButton(f_ba, text="👁️ Visão", command=lambda: self.visualizar_central("audit_extensos"), fg_color="#3498DB", hover_color="#2980B9", width=100).grid(row=0, column=1, padx=5, pady=5)
        ctk.CTkButton(f_ba, text="📄 PDF", command=lambda: self.gerar_arquivo_central("audit_extensos", "pdf"), fg_color="#E67E22", hover_color="#D35400", width=100).grid(row=0, column=2, padx=5, pady=5)
        ctk.CTkButton(f_ba, text="📊 Excel", command=lambda: self.gerar_arquivo_central("audit_extensos", "excel"), fg_color="#1D6F42", hover_color="#144D2E", width=100).grid(row=0, column=3, padx=5, pady=5)
        
        ctk.CTkLabel(f_ba, text="Duplicadas:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        ctk.CTkButton(f_ba, text="👁️ Visão", command=lambda: self.visualizar_central("audit_duplicados"), fg_color="#3498DB", hover_color="#2980B9", width=100).grid(row=1, column=1, padx=5, pady=5)
        ctk.CTkButton(f_ba, text="📄 PDF", command=lambda: self.gerar_arquivo_central("audit_duplicados", "pdf"), fg_color="#E67E22", hover_color="#D35400", width=100).grid(row=1, column=2, padx=5, pady=5)
        ctk.CTkButton(f_ba, text="📊 Excel", command=lambda: self.gerar_arquivo_central("audit_duplicados", "excel"), fg_color="#1D6F42", hover_color="#144D2E", width=100).grid(row=1, column=3, padx=5, pady=5)

        f_det = ctk.CTkFrame(f_scr); f_det.pack(fill="x", pady=10)
        ctk.CTkLabel(f_det, text="4. Relatório Detalhado", font=ctk.CTkFont(weight="bold", size=14)).pack(anchor="w", padx=15, pady=(10, 0))
        f_fd = ctk.CTkFrame(f_det, fg_color="transparent"); f_fd.pack(pady=5)
        ctk.CTkLabel(f_fd, text="Dept:").grid(row=0, column=0, padx=5, pady=5); self.cb_dept = ctk.CTkComboBox(f_fd, width=150, values=["Todos"]); self.cb_dept.grid(row=0, column=1, padx=5, pady=5)
        ctk.CTkLabel(f_fd, text="Usr:").grid(row=0, column=2, padx=5, pady=5); self.cb_usuario = ctk.CTkComboBox(f_fd, width=150, values=["Todos"]); self.cb_usuario.grid(row=0, column=3, padx=5, pady=5)
        ctk.CTkLabel(f_fd, text="Imp:").grid(row=0, column=4, padx=5, pady=5); self.cb_impressora = ctk.CTkComboBox(f_fd, width=150, values=["Todos"]); self.cb_impressora.grid(row=0, column=5, padx=5, pady=5)
        f_bd = ctk.CTkFrame(f_det, fg_color="transparent"); f_bd.pack(pady=(5, 10))
        ctk.CTkButton(f_bd, text="👁️ Visão Completa", command=lambda: self.visualizar_central("detalhado"), fg_color="#3498DB", hover_color="#2980B9", width=150).pack(side="left", padx=10)
        ctk.CTkButton(f_bd, text="📄 PDF Paisagem", command=lambda: self.gerar_arquivo_central("detalhado", "pdf"), fg_color="#E67E22", hover_color="#D35400", width=150).pack(side="left", padx=10)
        ctk.CTkButton(f_bd, text="📊 Exportar Excel", command=lambda: self.gerar_arquivo_central("detalhado", "excel"), fg_color="#1D6F42", hover_color="#144D2E", width=150).pack(side="left", padx=10)

        f_mail = ctk.CTkFrame(f_scr); f_mail.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(f_mail, text="5. Envio de Relatório à Diretoria (Dia 01 até Hoje)", font=ctk.CTkFont(weight="bold", size=14)).pack(anchor="w", padx=15, pady=(10, 0))
        f_btn_mail = ctk.CTkFrame(f_mail, fg_color="transparent"); f_btn_mail.pack(pady=10)
        ctk.CTkLabel(f_btn_mail, text="Envia o acumulado do mês corrente em formato PDF e Excel.").pack(side="left", padx=10)
        ctk.CTkButton(f_btn_mail, text="🚀 Enviar Relatório do Mês Agora", command=self.disparar_fecho_manual_central, fg_color="#8E44AD", hover_color="#732D91", width=240).pack(side="left", padx=10)

    def obter_dados_central(self, tipo):
        d_ini, d_fim = self.pdf_data_ini.get().strip(), self.pdf_data_fim.get().strip()
        query = '''SELECT l.data_hora, l.terminal, COALESCE(m.nome_real, l.usuario) as nome_final, COALESCE(m.departamento, 'Sem Setor') as departamento, l.impressora, l.paginas, COALESCE(i.custo_pagina, 0.0) as custo_pagina, l.documento 
                   FROM logs_impressao l LEFT JOIN mapeamento_terminais m ON UPPER(l.terminal) = UPPER(m.terminal) LEFT JOIN configuracao_impressoras i ON UPPER(l.impressora) = UPPER(i.nome_impressora) WHERE 1=1'''
        if d_ini: query += f" AND l.data_hora >= '{datetime.strptime(d_ini, '%d/%m/%Y').strftime('%Y-%m-%d 00:00:00')}'"
        if d_fim: query += f" AND l.data_hora <= '{datetime.strptime(d_fim, '%d/%m/%Y').strftime('%Y-%m-%d 23:59:59')}'"
        
        if tipo == "detalhado":
            dept, usu, imp = self.cb_dept.get().strip(), self.cb_usuario.get().strip(), self.cb_impressora.get().strip()
            if dept and dept != "Todos": query += f" AND LOWER(COALESCE(m.departamento, 'Sem Setor')) = LOWER('{dept}')"
            if usu and usu != "Todos": query += f" AND LOWER(COALESCE(m.nome_real, l.usuario)) = LOWER('{usu}')"
            if imp and imp != "Todos": query += f" AND LOWER(l.impressora) = LOWER('{imp}')"
        elif tipo in ["audit_extensos", "audit_duplicados"]:
            dept_audit = self.cb_dept_audit.get().strip()
            if dept_audit and dept_audit != "Todos":
                query += f" AND LOWER(COALESCE(m.departamento, 'Sem Setor')) = LOWER('{dept_audit}')"

        query += " ORDER BY l.data_hora DESC"
        sessao, engine = obter_sessao(); df = pd.read_sql(query, engine); sessao.close()
        if not df.empty: df['custo_total'] = df['paginas'] * df['custo_pagina']
        return df

    def visualizar_central(self, tipo):
        try: df = self.obter_dados_central(tipo)
        except ValueError: return messagebox.showerror("Erro", "Data inválida.")
        if df.empty: return messagebox.showwarning("Aviso", "Sem dados para o período ou filtros selecionados.")

        janela_visao = ctk.CTkToplevel(self)
        janela_visao.title("Pré-visualização de Dados")
        janela_visao.geometry("1000x550")
        janela_visao.attributes("-topmost", True)

        titulos_modal = {
            "impressoras": "🔍 Visão Geral: Custos por Equipamento",
            "usuarios": "🔍 Visão Geral: Custos por Utilizador",
            "audit_extensos": "🔍 Auditoria: Top Documentos Mais Extensos",
            "audit_duplicados": "🔍 Auditoria: Top Impressões Duplicadas",
            "detalhado": "🔍 Visão Geral: Relatório Detalhado"
        }
        
        ctk.CTkLabel(janela_visao, text=titulos_modal.get(tipo, "Pré-visualização de Dados"), font=ctk.CTkFont(weight="bold", size=18)).pack(pady=15)
        
        frame_grid = ctk.CTkFrame(janela_visao)
        frame_grid.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        scroll_y = ttk.Scrollbar(frame_grid)
        scroll_y.pack(side="right", fill="y")
        
        self.tree_prev = ttk.Treeview(frame_grid, show="headings", yscrollcommand=scroll_y.set)
        scroll_y.config(command=self.tree_prev.yview)
        self.tree_prev.tag_configure('total', background="#2FA572", foreground="white")
        self.tree_prev.pack(fill="both", expand=True)

        if tipo == "impressoras":
            df['imp_agr'] = df['impressora'].apply(lambda x: 'Contábil/Fiscal & Contratos' if str(x).upper() in ['CONTABIL_FISCAL', 'CONTRATOS'] else x)
            resumo = df.groupby('imp_agr').agg({'paginas': 'sum', 'custo_total': 'sum'}).reset_index().sort_values(by='paginas', ascending=False)
            self.tree_prev["columns"] = ("Equipamento", "Páginas", "Custo")
            for c, w in zip(("Equipamento", "Páginas", "Custo"), (300, 100, 150)): self.tree_prev.heading(c, text=c); self.tree_prev.column(c, width=w, anchor="center" if c!="Equipamento" else "w")
            for _, r in resumo.iterrows(): self.tree_prev.insert("", "end", values=(r['imp_agr'], int(r['paginas']), f_moeda(r['custo_total'])))
            self.tree_prev.insert("", "end", values=("TOTAL GERAL", int(resumo['paginas'].sum()), f_moeda(resumo['custo_total'].sum())), tags=('total',))
        
        elif tipo == "usuarios":
            resumo = df.groupby(['nome_final', 'departamento']).agg({'paginas': 'sum', 'custo_total': 'sum'}).reset_index().sort_values(by='nome_final' if self.pdf_ordenacao.get() == "Ordem Alfabética" else 'paginas', ascending=(self.pdf_ordenacao.get() == "Ordem Alfabética"))
            self.tree_prev["columns"] = ("Utilizador", "Setor", "Páginas", "Custo")
            for c, w in zip(("Utilizador", "Setor", "Páginas", "Custo"), (250, 180, 120, 150)): self.tree_prev.heading(c, text=c); self.tree_prev.column(c, width=w, anchor="center" if c in ["Páginas", "Custo"] else "w")
            for _, r in resumo.iterrows(): self.tree_prev.insert("", "end", values=(r['nome_final'], r['departamento'], int(r['paginas']), f_moeda(r['custo_total'])))
            self.tree_prev.insert("", "end", values=("TOTAL GERAL", "-", int(resumo['paginas'].sum()), f_moeda(resumo['custo_total'].sum())), tags=('total',))
        
        elif tipo == "audit_extensos":
            df['paginas'] = pd.to_numeric(df['paginas'], errors='coerce').fillna(0)
            df_filtrado = df[df['paginas'] > 1]
            df_ex = df_filtrado.nlargest(50, 'paginas')
            self.tree_prev["columns"] = ("Data", "Utilizador", "Páginas", "Documento")
            for c, w in zip(("Data", "Utilizador", "Páginas", "Documento"), (120, 150, 80, 400)):
                self.tree_prev.heading(c, text=c); self.tree_prev.column(c, width=w, anchor="center" if c!="Documento" else "w")
            for _, r in df_ex.iterrows():
                d_str = pd.to_datetime(r['data_hora']).strftime("%d/%m/%Y %H:%M")
                self.tree_prev.insert("", "end", values=(d_str, r['nome_final'], int(r['paginas']), r['documento']))
        
        elif tipo == "audit_duplicados":
            df_dup = df.groupby(['documento', 'nome_final']).agg(vezes=('documento', 'count'), paginas_totais=('paginas', 'sum')).reset_index()
            df_ex = df_dup[df_dup['vezes'] > 1].sort_values(by=['vezes', 'paginas_totais'], ascending=[False, False]).head(50)
            self.tree_prev["columns"] = ("Qtd", "Utilizador", "Total Pags", "Documento")
            for c, w in zip(("Qtd", "Utilizador", "Total Pags", "Documento"), (80, 150, 100, 400)):
                self.tree_prev.heading(c, text=c); self.tree_prev.column(c, width=w, anchor="center" if c!="Documento" else "w")
            for _, r in df_ex.iterrows():
                self.tree_prev.insert("", "end", values=(f"{int(r['vezes'])}x", r['nome_final'], int(r['paginas_totais']), r['documento']))
        
        elif tipo == "detalhado":
            self.tree_prev["columns"] = ("Data", "Terminal", "Nome", "Setor", "Imp", "Pags", "Custo", "Doc")
            for col, w in zip(("Data", "Terminal", "Nome", "Setor", "Imp", "Pags", "Custo", "Doc"), (120, 90, 130, 110, 100, 50, 80, 250)):
                self.tree_prev.heading(col, text=col.replace("Custo", "Custo (R$)")); self.tree_prev.column(col, width=w, anchor="center" if col not in ["Nome", "Doc", "Setor"] else "w")
            for _, r in df.iterrows(): self.tree_prev.insert("", "end", values=(pd.to_datetime(r['data_hora']).strftime("%d/%m/%Y %H:%M"), r['terminal'], r['nome_final'], r['departamento'], r['impressora'], r['paginas'], f_moeda(r['custo_total']), r['documento']))
            self.tree_prev.insert("", "end", values=("TOTAL GERAL", "", "", "", "", int(df['paginas'].sum()), f_moeda(df['custo_total'].sum()), ""), tags=('total',))

    def gerar_arquivo_central(self, tipo, formato):
        try: df = self.obter_dados_central(tipo)
        except ValueError: return messagebox.showerror("Erro", "Data inválida.")
        if df.empty: return messagebox.showwarning("Aviso", "Sem dados.")
        
        d_ini, d_fim = self.pdf_data_ini.get().strip(), self.pdf_data_fim.get().strip()
        str_ini, str_fim = d_ini.replace('/', '-') if d_ini else "Inicio", d_fim.replace('/', '-') if d_fim else "Hoje"
        ext = ".xlsx" if formato == "excel" else ".pdf"
        tipo_f = ("Excel", "*.xlsx") if formato == "excel" else ("PDF", "*.pdf")
        
        if tipo == "impressoras": nome = f"Equipamentos_{str_ini}_a_{str_fim}{ext}"
        elif tipo == "usuarios": nome = f"Utilizadores_{str_ini}_a_{str_fim}{ext}"
        elif tipo == "audit_extensos": nome = f"Auditoria_Extensos_{str_ini}_a_{str_fim}{ext}"
        elif tipo == "audit_duplicados": nome = f"Auditoria_Duplicados_{str_ini}_a_{str_fim}{ext}"
        else: nome = f"Relatorio_Detalhado_{str_ini}_a_{str_fim}{ext}"
        
        caminho = filedialog.asksaveasfilename(defaultextension=ext, initialfile=nome, filetypes=[tipo_f], title=f"Guardar Relatório")
        if not caminho: return

        if tipo == "audit_extensos":
            df['paginas'] = pd.to_numeric(df['paginas'], errors='coerce').fillna(0)
            df_filtrado = df[df['paginas'] > 1]
            df_ex = df_filtrado.nlargest(100, 'paginas')[['data_hora', 'nome_final', 'departamento', 'paginas', 'documento']]
            df_ex['data_hora'] = pd.to_datetime(df_ex['data_hora']).dt.strftime("%d/%m/%Y %H:%M")
            df_ex = df_ex.rename(columns={'data_hora': 'Data', 'nome_final': 'Utilizador', 'departamento': 'Setor', 'paginas': 'Páginas', 'documento': 'Ficheiro'})
        elif tipo == "audit_duplicados":
            df_dup = df.groupby(['documento', 'nome_final', 'departamento']).agg(vezes=('documento', 'count'), paginas_totais=('paginas', 'sum')).reset_index()
            df_ex = df_dup[df_dup['vezes'] > 1].sort_values(by=['vezes', 'paginas_totais'], ascending=[False, False])
            df_ex = df_ex.rename(columns={'vezes': 'Qtd Impressões', 'nome_final': 'Utilizador', 'departamento': 'Setor', 'paginas_totais': 'Total Páginas', 'documento': 'Ficheiro'})

        if formato == "excel":
            try:
                if tipo == "impressoras":
                    df['imp_agr'] = df['impressora'].apply(lambda x: 'Contábil/Fiscal & Contratos' if str(x).upper() in ['CONTABIL_FISCAL', 'CONTRATOS'] else x)
                    df_ex = df.groupby('imp_agr').agg({'paginas': 'sum', 'custo_total': 'sum'}).reset_index().sort_values(by='paginas', ascending=False)
                    df_ex = df_ex.rename(columns={'imp_agr': 'Impressora', 'paginas': 'Total Páginas', 'custo_total': 'Custo Estimado (R$)'})
                elif tipo == "usuarios":
                    df_ex = df.groupby(['nome_final', 'departamento']).agg({'paginas': 'sum', 'custo_total': 'sum'}).reset_index()
                    df_ex = df_ex.rename(columns={'nome_final': 'Utilizador', 'departamento': 'Setor', 'paginas': 'Total Páginas', 'custo_total': 'Custo Estimado (R$)'})
                elif tipo == "detalhado":
                    df_ex = df.rename(columns={'data_hora': 'Data', 'terminal': 'Terminal', 'nome_final': 'Utilizador', 'departamento': 'Setor', 'impressora': 'Impressora', 'paginas': 'Páginas', 'custo_pagina': 'Custo Fixo', 'custo_total': 'Custo Acumulado', 'documento': 'Ficheiro'})
                
                df_ex.to_excel(caminho, index=False)
                messagebox.showinfo("Sucesso", f"Excel guardado em:\n{caminho}")
            except Exception as e: messagebox.showerror("Erro Excel", str(e))
            
        elif formato == "pdf":
            periodo = f"{d_ini or 'Início'} a {d_fim or 'Hoje'}"
            
            try:
                from relatorios import exportar_resumo_impressoras_pdf, exportar_resumo_usuarios_pdf, exportar_relatorio_detalhado_pdf
                from relatorios import exportar_auditoria_extensos_pdf, exportar_auditoria_duplicados_pdf
                
                if tipo == "impressoras": 
                    exportar_resumo_impressoras_pdf(df, caminho, periodo)
                elif tipo == "usuarios": 
                    exportar_resumo_usuarios_pdf(df, caminho, periodo, self.pdf_ordenacao.get())
                elif tipo == "audit_extensos":
                    exportar_auditoria_extensos_pdf(df_ex.head(40), caminho, periodo)
                elif tipo == "audit_duplicados":
                    exportar_auditoria_duplicados_pdf(df_ex.head(40), caminho, periodo)
                else: 
                    info_f = "Apenas Período"
                    f_usados = []
                    d, u, i = self.cb_dept.get(), self.cb_usuario.get(), self.cb_impressora.get()
                    if d != "Todos": f_usados.append(f"Set: {d}")
                    if u != "Todos": f_usados.append(f"Usr: {u}")
                    if i != "Todos": f_usados.append(f"Imp: {i}")
                    if f_usados: info_f = " | ".join(f_usados)
                    exportar_relatorio_detalhado_pdf(df, caminho, periodo, info_f)
                    
                messagebox.showinfo("Sucesso", f"PDF guardado em:\n{caminho}")
            except Exception as e: 
                messagebox.showerror("Erro PDF", str(e))

    def disparar_fecho_manual_central(self):
        hoje = datetime.now()
        d_ini_str = hoje.replace(day=1).strftime("%d/%m/%Y")
        d_fim_str = hoje.strftime("%d/%m/%Y")
        mes_ref = hoje.strftime("%m/%Y")

        sessao, _ = obter_sessao()
        cfg = sessao.query(ConfiguracaoSistema).first()
        sessao.close()

        if not cfg or not cfg.remetente or not cfg.senha or not cfg.destinatario:
            return messagebox.showwarning("Aviso", "Configure as credenciais de SMTP primeiro no botão '⚙️ Configurações' no topo!")

        if messagebox.askyesno("Envio de Relatório Acumulado", f"Deseja enviar o relatório de {d_ini_str} até hoje ({d_fim_str}) para {cfg.destinatario}?"):
            try:
                self.motor_envio_email(cfg.remetente, cfg.senha, cfg.destinatario, cfg.servidor_smtp, cfg.porta_smtp, d_ini_str, d_fim_str, mes_ref, silencioso=False)
            except Exception as e:
                messagebox.showerror("Erro", str(e))

    def motor_envio_email(self, rem, sen, dest, serv_manual, porta_int, d_ini, d_fim, mes_ref, silencioso):
        query = f'''SELECT l.data_hora, l.terminal, COALESCE(m.nome_real, l.usuario) as nome_final, COALESCE(m.departamento, 'Sem Setor') as departamento, l.impressora, l.paginas, COALESCE(i.custo_pagina, 0.0) as custo_pagina, l.documento 
                   FROM logs_impressao l LEFT JOIN mapeamento_terminais m ON UPPER(l.terminal) = UPPER(m.terminal) LEFT JOIN configuracao_impressoras i ON UPPER(l.impressora) = UPPER(i.nome_impressora) WHERE 1=1'''
        if d_ini: query += f" AND l.data_hora >= '{datetime.strptime(d_ini, '%d/%m/%Y').strftime('%Y-%m-%d 00:00:00')}'"
        if d_fim: query += f" AND l.data_hora <= '{datetime.strptime(d_fim, '%d/%m/%Y').strftime('%Y-%m-%d 23:59:59')}'"
        query += " ORDER BY l.data_hora DESC"

        sessao, engine = obter_sessao(); df = pd.read_sql(query, engine); sessao.close()
        
        if df.empty:
            if not silencioso: messagebox.showwarning("Aviso", "Não há impressões no período selecionado.")
            return

        df['custo_total'] = df['paginas'] * df['custo_pagina']
        df['paginas_num'] = pd.to_numeric(df['paginas'], errors='coerce').fillna(0)

        temp_dir = tempfile.gettempdir()
        pdf_resumo_path = os.path.join(temp_dir, "Resumo_Financeiro_Mes.pdf")
        pdf_extensos_path = os.path.join(temp_dir, "Auditoria_Extensos_Mes.pdf")
        pdf_duplicados_path = os.path.join(temp_dir, "Auditoria_Duplicados_Mes.pdf")
        excel_path = os.path.join(temp_dir, "Base_Dados_Completa.xlsx")
        
        periodo = f"{d_ini} a {d_fim}"

        from relatorios import exportar_resumo_impressoras_pdf, exportar_auditoria_extensos_pdf, exportar_auditoria_duplicados_pdf
        
        df_imp = df.copy()
        def unificar_imp(nome):
            if str(nome).strip().upper() in ['CONTABIL_FISCAL', 'CONTRATOS']: return 'Contábil/Fiscal & Contratos'
            return nome
        df_imp['impressora'] = df_imp['impressora'].apply(unificar_imp)
        exportar_resumo_impressoras_pdf(df_imp, pdf_resumo_path, periodo)

        df_filtrado_ext = df[df['paginas_num'] > 1]
        df_ex_ext = df_filtrado_ext.nlargest(40, 'paginas_num')[['data_hora', 'nome_final', 'departamento', 'paginas_num', 'documento']]
        df_ex_ext['data_hora'] = pd.to_datetime(df_ex_ext['data_hora']).dt.strftime("%d/%m/%Y %H:%M")
        df_ex_ext = df_ex_ext.rename(columns={'data_hora': 'Data', 'nome_final': 'Utilizador', 'departamento': 'Setor', 'paginas_num': 'Páginas', 'documento': 'Ficheiro'})
        exportar_auditoria_extensos_pdf(df_ex_ext, pdf_extensos_path, periodo)

        df_dup = df.groupby(['documento', 'nome_final', 'departamento']).agg(vezes=('documento', 'count'), paginas_totais=('paginas_num', 'sum')).reset_index()
        df_ex_dup = df_dup[df_dup['vezes'] > 1].sort_values(by=['vezes', 'paginas_totais'], ascending=[False, False]).head(40)
        df_ex_dup = df_ex_dup.rename(columns={'vezes': 'Qtd Impressões', 'nome_final': 'Utilizador', 'departamento': 'Setor', 'paginas_totais': 'Total Páginas', 'documento': 'Ficheiro'})
        exportar_auditoria_duplicados_pdf(df_ex_dup, pdf_duplicados_path, periodo)

        df_ex = df.rename(columns={'data_hora': 'Data', 'terminal': 'Terminal', 'nome_final': 'Utilizador', 'departamento': 'Setor', 'impressora': 'Impressora', 'paginas': 'Páginas', 'custo_pagina': 'Custo Fixo', 'custo_total': 'Custo Estimado', 'documento': 'Ficheiro'})
        if 'paginas_num' in df_ex.columns:
            df_ex = df_ex.drop(columns=['paginas_num'])
        df_ex.to_excel(excel_path, index=False)

        # -------------------------------------------------------------
        # SISTEMA DE TEMPLATE EXTERNO (GERIDO VIA INTERFACE)
        # -------------------------------------------------------------
        caminho_template = "template_email.txt"
        texto_padrao = """Olá,

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

        if not os.path.exists(caminho_template):
            try:
                with open(caminho_template, "w", encoding="utf-8") as f:
                    f.write(texto_padrao)
            except Exception: pass

        try:
            with open(caminho_template, "r", encoding="utf-8") as f:
                corpo_template = f.read()
        except Exception:
            corpo_template = texto_padrao 

        total_pags_str = str(int(df['paginas_num'].sum()))
        custo_total_str = f_moeda(df['custo_total'].sum())
        
        corpo = corpo_template.replace("{periodo}", periodo)\
                              .replace("{total_pags}", total_pags_str)\
                              .replace("{custo_total}", custo_total_str)
        # -------------------------------------------------------------

        msg = MIMEMultipart()
        msg['From'], msg['To'], msg['Subject'] = rem, dest, f"Relatório de Impressões e Auditoria - {periodo}"
        msg.attach(MIMEText(corpo, 'plain'))

        lista_anexos = [pdf_resumo_path, pdf_extensos_path, pdf_duplicados_path, excel_path]
        for f_path in lista_anexos:
            with open(f_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename= {os.path.basename(f_path)}")
            msg.attach(part)

        if serv_manual:
            servidor = serv_manual
        else:
            servidor = "smtp-mail.outlook.com" if "outlook" in rem.lower() or "hotmail" in rem.lower() else "smtp.gmail.com"
            porta_int = 587 if "outlook" in rem.lower() or "hotmail" in rem.lower() else 465

        if porta_int == 465: server = smtplib.SMTP_SSL(servidor, porta_int)
        else:
            server = smtplib.SMTP(servidor, porta_int)
            server.starttls()
        
        server.login(rem, sen)
        server.send_message(msg)
        server.quit()

        if not silencioso:
            messagebox.showinfo("Sucesso", "O pacote completo de relatórios e auditoria foi enviado à diretoria com sucesso!")

    # =========================================================
    # JANELA DE CONFIGURAÇÕES GLOBAIS (CAMINHO CSV E SMTP)
    # =========================================================
    def abrir_janela_configuracoes(self):
        jan = ctk.CTkToplevel(self)
        jan.title("Configurações do Sistema")
        jan.geometry("560x680")
        jan.attributes("-topmost", True)
        jan.grab_set()

        f_scr = ctk.CTkScrollableFrame(jan, fg_color="transparent")
        f_scr.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(f_scr, text="Configurações Globais do Sistema", font=ctk.CTkFont(weight="bold", size=16)).pack(pady=15)

        sessao, _ = obter_sessao()
        cfg = sessao.query(ConfiguracaoSistema).first()
        if not cfg:
            cfg = ConfiguracaoSistema(caminho_csv=r"D:\Relatorios", porta_smtp=465)
            sessao.add(cfg); sessao.commit()
        sessao.close()

        f_box1 = ctk.CTkFrame(f_scr)
        f_box1.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(f_box1, text="Pasta Padrão dos Relatórios CSV:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=15, pady=(10, 0))
        
        f_csv = ctk.CTkFrame(f_box1, fg_color="transparent")
        f_csv.pack(fill="x", padx=15, pady=10)
        
        e_csv = ctk.CTkEntry(f_csv, width=380)
        e_csv.pack(side="left", padx=(0, 5))
        e_csv.insert(0, cfg.caminho_csv or r"D:\Relatorios")

        def procurar_pasta():
            pasta = filedialog.askdirectory(title="Selecione a pasta dos CSVs")
            if pasta:
                e_csv.delete(0, 'end'); e_csv.insert(0, pasta)

        ctk.CTkButton(f_csv, text="📁 Procurar", command=procurar_pasta, width=90, fg_color="#3498DB", hover_color="#2980B9").pack(side="left")

        f_box2 = ctk.CTkFrame(f_scr)
        f_box2.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(f_box2, text="Parâmetros de Envio de E-mail (SMTP):", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=15, pady=(10, 0))
        
        f_mail = ctk.CTkFrame(f_box2, fg_color="transparent")
        f_mail.pack(fill="x", padx=15, pady=10)

        ctk.CTkLabel(f_mail, text="E-mail Remetente:").pack(anchor="w", pady=(5, 0))
        e_rem = ctk.CTkEntry(f_mail, width=460); e_rem.pack(pady=(0, 8))
        e_rem.insert(0, cfg.remetente or "")

        ctk.CTkLabel(f_mail, text="Senha de Aplicação:").pack(anchor="w", pady=(5, 0))
        e_sen = ctk.CTkEntry(f_mail, width=460, show="*"); e_sen.pack(pady=(0, 8))
        e_sen.insert(0, cfg.senha or "")

        ctk.CTkLabel(f_mail, text="E-mail da Diretoria (Destinatário):").pack(anchor="w", pady=(5, 0))
        e_dest = ctk.CTkEntry(f_mail, width=460); e_dest.pack(pady=(0, 8))
        e_dest.insert(0, cfg.destinatario or "")

        f_srv = ctk.CTkFrame(f_mail, fg_color="transparent")
        f_srv.pack(fill="x", pady=5)

        f_serv_porta = ctk.CTkFrame(f_srv, fg_color="transparent")
        f_serv_porta.pack(fill="x", pady=5)

        ctk.CTkLabel(f_serv_porta, text="Servidor SMTP:").pack(side="left", padx=(0, 10))
        ctk.CTkLabel(f_serv_porta, text="Porta:").pack(side="left", padx=(120, 0))

        f_inputs = ctk.CTkFrame(f_srv, fg_color="transparent")
        f_inputs.pack(fill="x", pady=2)

        e_serv = ctk.CTkEntry(f_inputs, width=330, placeholder_text="Ex: mail.viman.com.br")
        e_serv.pack(side="left", padx=(0, 15))
        e_serv.insert(0, cfg.servidor_smtp or "")

        e_porta = ctk.CTkEntry(f_inputs, width=115, placeholder_text="465 ou 587")
        e_porta.pack(side="left")
        e_porta.insert(0, str(cfg.porta_smtp) if cfg.porta_smtp else "465")

        def salvar_configuracoes():
            c_path = e_csv.get().strip()
            rem = e_rem.get().strip()
            sen = e_sen.get().strip()
            dest = e_dest.get().strip()
            serv = e_serv.get().strip()
            p_str = e_porta.get().strip()
            p_int = int(p_str) if p_str.isdigit() else 465

            s, _ = obter_sessao()
            c = s.query(ConfiguracaoSistema).first()
            if not c: c = ConfiguracaoSistema()
            c.caminho_csv = c_path
            c.remetente = rem
            c.senha = sen
            c.destinatario = dest
            c.servidor_smtp = serv
            c.porta_smtp = p_int
            s.add(c); s.commit(); s.close()

            messagebox.showinfo("Sucesso", "Configurações globais guardadas com sucesso!")
            jan.destroy()

        ctk.CTkButton(f_scr, text="💾 Salvar Configurações", command=salvar_configuracoes, fg_color="#2FA572", hover_color="#1D7850", width=280, height=45).pack(pady=15)
        
        # --- NOVO BOTÃO PARA ABRIR O EDITOR DE TEXTO DA MENSAGEM DO E-MAIL ---
        ctk.CTkButton(f_scr, text="📝 Editar Mensagem do E-mail", command=self.abrir_janela_template_email, fg_color="#F39C12", hover_color="#D68910", width=280, height=40).pack(pady=(0, 20))

    # =========================================================
    # NOVO: EDITOR DE TEXTO PARA A MENSAGEM DO E-MAIL
    # =========================================================
    def abrir_janela_template_email(self):
        jan_temp = ctk.CTkToplevel(self)
        jan_temp.title("Editar Mensagem Automática")
        jan_temp.geometry("600x550")
        jan_temp.attributes("-topmost", True)
        jan_temp.grab_set()

        ctk.CTkLabel(jan_temp, text="Template do Corpo do E-mail", font=ctk.CTkFont(weight="bold", size=16)).pack(pady=(20, 5))
        ctk.CTkLabel(jan_temp, text="Pode usar as variáveis {periodo}, {total_pags} e {custo_total} no seu texto.", font=ctk.CTkFont(slant="italic", size=12)).pack(pady=(0, 10))

        txt_template = ctk.CTkTextbox(jan_temp, width=550, height=350, font=ctk.CTkFont(size=14))
        txt_template.pack(padx=20, pady=10)

        caminho_template = "template_email.txt"
        texto_padrao = "Olá,\n\nSegue em anexo o pacote de relatórios de impressões da Viman Contabilidade referente ao período de {periodo}.\n\n► Total de Páginas Impressas: {total_pags}\n► Custo Estimado Total: {custo_total}\n\nFicheiros em anexo:\n- Resumo_Financeiro_Mes.pdf (Consumo por Equipamento)\n- Auditoria_Extensos_Mes.pdf (Documentos com mais páginas)\n- Auditoria_Duplicados_Mes.pdf (Detecção de Desperdício)\n- Base_Dados_Completa.xlsx (Registos Detalhados)\n\nAtenciosamente,\nSistema de Auditoria Interna - Viman Contabilidade"

        if os.path.exists(caminho_template):
            try:
                with open(caminho_template, "r", encoding="utf-8") as f:
                    conteudo = f.read()
            except Exception:
                conteudo = texto_padrao
        else:
            conteudo = texto_padrao

        txt_template.insert("1.0", conteudo)

        def salvar_template():
            novo_texto = txt_template.get("1.0", "end-1c")
            try:
                with open(caminho_template, "w", encoding="utf-8") as f:
                    f.write(novo_texto)
                messagebox.showinfo("Sucesso", "Mensagem de e-mail atualizada e gravada com sucesso!")
                jan_temp.destroy()
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível salvar o template:\n{e}")

        ctk.CTkButton(jan_temp, text="💾 Salvar Mensagem", command=salvar_template, fg_color="#2FA572", hover_color="#1D7850", width=220, height=45).pack(pady=10)

    # =========================================================
    # JANELA DE CADASTROS (CUSTOS E DEPARTAMENTOS)
    # =========================================================
    def abrir_janela_custos(self):
        jan = ctk.CTkToplevel(self); jan.title("Custos de Impressão"); jan.geometry("500x500"); jan.attributes("-topmost", True); jan.grab_set() 
        ctk.CTkLabel(jan, text="Definir Valor (R$) por Página", font=ctk.CTkFont(weight="bold", size=16)).pack(pady=15)
        
        f = ctk.CTkFrame(jan, fg_color="transparent"); f.pack(fill="x", padx=20)
        ctk.CTkLabel(f, text="Impressora (Exata):").grid(row=0, column=0, sticky="w", pady=2)
        
        sessao, engine = obter_sessao()
        imps_unicas = sorted([str(x) for x in pd.read_sql("SELECT DISTINCT impressora FROM logs_impressao", engine)['impressora'].dropna().unique()])
        sessao.close()
        
        ei = ctk.CTkComboBox(f, width=200, values=imps_unicas); ei.grid(row=1, column=0, sticky="w", pady=5, padx=(0, 15))
        ctk.CTkLabel(f, text="Custo por Página (R$):").grid(row=0, column=1, sticky="w", pady=2)
        ec = ctk.CTkEntry(f, width=120, placeholder_text="0,05"); ec.grid(row=1, column=1, sticky="w", pady=5)

        def load():
            for i in tree.get_children(): tree.delete(i)
            s, _ = obter_sessao()
            for r in s.query(ConfiguracaoImpressora).all(): tree.insert("", "end", values=(r.nome_impressora, f_moeda(r.custo_pagina)))
            s.close()

        def save():
            n, v_str = ei.get().strip().upper(), ec.get().strip().replace(',', '.')
            try: v = float(v_str)
            except: return messagebox.showwarning("Aviso", "Valor inválido! Use formato 0,05")
            if not n: return
            s, _ = obter_sessao(); reg = s.query(ConfiguracaoImpressora).filter_by(nome_impressora=n).first()
            if reg: reg.custo_pagina = v
            else: s.add(ConfiguracaoImpressora(nome_impressora=n, custo_pagina=v))
            s.commit(); s.close(); ec.delete(0, 'end'); load(); self.visao_dashboard.gerar_graficos(); self.carregar_dados_relatorio()

        def delete():
            n = ei.get().strip().upper()
            s, _ = obter_sessao(); reg = s.query(ConfiguracaoImpressora).filter_by(nome_impressora=n).first()
            if reg: s.delete(reg); s.commit()
            s.close(); ec.delete(0, 'end'); load(); self.visao_dashboard.gerar_graficos(); self.carregar_dados_relatorio()

        fb = ctk.CTkFrame(jan, fg_color="transparent"); fb.pack(fill="x", padx=20, pady=10)
        ctk.CTkButton(fb, text="Salvar Custo", command=save, width=140, fg_color="#2FA572", hover_color="#1D7850").pack(side="left", padx=5)
        ctk.CTkButton(fb, text="Remover", command=delete, width=120, fg_color="#c23b22", hover_color="#8f2a18").pack(side="left", padx=5)
        
        ttk.Style(jan).configure("Treeview", borderwidth=0)
        tree = ttk.Treeview(jan, columns=("I", "C"), show="headings", height=10)
        tree.heading("I", text="Impressora"); tree.heading("C", text="Custo (R$)")
        tree.column("I", width=250); tree.column("C", width=150); tree.pack(fill="both", expand=True, padx=20, pady=10)
        tree.bind("<<TreeviewSelect>>", lambda e: (ei.set(tree.item(tree.selection()[0])['values'][0]), ec.delete(0, 'end'), ec.insert(0, str(tree.item(tree.selection()[0])['values'][1]).replace('R$ ', ''))) if tree.selection() else None)
        load()

    def abrir_janela_mapeamento(self):
        jan = ctk.CTkToplevel(self); jan.title("Departamentos e Vínculos"); jan.geometry("600x550"); jan.attributes("-topmost", True); jan.grab_set() 
        ctk.CTkLabel(jan, text="Cadastro de Utilizadores e Departamentos", font=ctk.CTkFont(weight="bold", size=16)).pack(pady=15)
        f = ctk.CTkFrame(jan, fg_color="transparent"); f.pack(fill="x", padx=20)
        ctk.CTkLabel(f, text="Terminal:").grid(row=0, column=0, sticky="w", pady=2); et = ctk.CTkEntry(f, width=130); et.grid(row=1, column=0, sticky="w", pady=5, padx=(0, 10))
        ctk.CTkLabel(f, text="Nome Real:").grid(row=0, column=1, sticky="w", pady=2); en = ctk.CTkEntry(f, width=200); en.grid(row=1, column=1, sticky="w", pady=5, padx=(0, 10))
        ctk.CTkLabel(f, text="Departamento:").grid(row=0, column=2, sticky="w", pady=2); ed = ctk.CTkEntry(f, width=170, placeholder_text="Ex: Recursos Humanos"); ed.grid(row=1, column=2, sticky="w", pady=5)

        def load():
            for i in tree.get_children(): tree.delete(i)
            s, _ = obter_sessao()
            for r in s.query(MapeamentoTerminal).all(): tree.insert("", "end", values=(r.terminal, r.nome_real, r.departamento or "Sem Setor"))
            s.close()
        def save():
            t, n, d = et.get().strip().upper(), en.get().strip(), ed.get().strip()
            if not t or not n: return messagebox.showwarning("Aviso", "Preencha o Terminal e Nome!")
            s, _ = obter_sessao(); v = s.query(MapeamentoTerminal).filter_by(terminal=t).first()
            if v: v.nome_real, v.departamento = n, d
            else: s.add(MapeamentoTerminal(terminal=t, nome_real=n, departamento=d))
            s.commit(); s.close(); et.delete(0, 'end'); en.delete(0, 'end'); ed.delete(0, 'end'); load(); self.visao_dashboard.gerar_graficos(); self.carregar_dados_relatorio(); self.carregar_valores_comboboxes()
        def delete():
            t = et.get().strip().upper()
            s, _ = obter_sessao(); v = s.query(MapeamentoTerminal).filter_by(terminal=t).first()
            if v: s.delete(v); s.commit()
            s.close(); et.delete(0, 'end'); en.delete(0, 'end'); ed.delete(0, 'end'); load(); self.visao_dashboard.gerar_graficos(); self.carregar_dados_relatorio(); self.carregar_valores_comboboxes()

        fb = ctk.CTkFrame(jan, fg_color="transparent"); fb.pack(fill="x", padx=20, pady=10)
        ctk.CTkButton(fb, text="Salvar Vínculo", command=save, width=140, fg_color="#2FA572", hover_color="#1D7850").pack(side="left", padx=5)
        ctk.CTkButton(fb, text="Excluir", command=delete, width=120, fg_color="#c23b22", hover_color="#8f2a18").pack(side="left", padx=5)
        
        ttk.Style(jan).configure("Treeview", borderwidth=0); tree = ttk.Treeview(jan, columns=("T", "N", "D"), show="headings", height=12)
        for c, w in zip(("T", "N", "D"), (100, 200, 200)): tree.heading(c, text={"T":"Terminal", "N":"Funcionário", "D":"Departamento"}[c]); tree.column(c, width=w)
        tree.pack(fill="both", expand=True, padx=20, pady=10)
        tree.bind("<<TreeviewSelect>>", lambda e: (et.delete(0, 'end'), et.insert(0, tree.item(tree.selection()[0])['values'][0]), en.delete(0, 'end'), en.insert(0, tree.item(tree.selection()[0])['values'][1]), ed.delete(0, 'end'), ed.insert(0, "" if tree.item(tree.selection()[0])['values'][2] == "Sem Setor" else tree.item(tree.selection()[0])['values'][2])) if tree.selection() else None)
        load()

if __name__ == "__main__":
    app = AppImpressoes()
    app.mainloop()