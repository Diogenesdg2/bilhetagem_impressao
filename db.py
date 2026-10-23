# db.py
import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

Base = declarative_base()

class RegistroImpressao(Base):
    __tablename__ = 'logs_impressao'
    id = Column(Integer, primary_key=True, autoincrement=True)
    data_hora = Column(DateTime, nullable=False)
    terminal = Column(String(50), nullable=False)
    usuario = Column(String(50), nullable=False)
    impressora = Column(String(100), nullable=False)
    paginas = Column(Integer, nullable=False)
    documento = Column(String(255), nullable=True)

class MapeamentoTerminal(Base):
    __tablename__ = 'mapeamento_terminais'
    id = Column(Integer, primary_key=True, autoincrement=True)
    terminal = Column(String(50), unique=True, nullable=False)
    nome_real = Column(String(100), nullable=False)
    departamento = Column(String(100), nullable=True)

class ConfiguracaoImpressora(Base):
    __tablename__ = 'configuracao_impressoras'
    id = Column(Integer, primary_key=True, autoincrement=True)
    nome_impressora = Column(String(100), unique=True, nullable=False)
    custo_pagina = Column(Float, default=0.0)

class HistoricoEnvio(Base):
    __tablename__ = 'historico_envios'
    id = Column(Integer, primary_key=True, autoincrement=True)
    mes_referencia = Column(String(10), unique=True) # Ex: "09/2026"
    data_envio = Column(DateTime, default=datetime.now)

# --- TABELA CENTRAL DE CONFIGURAÇÕES DO SISTEMA ---
class ConfiguracaoSistema(Base):
    __tablename__ = 'configuracoes_sistema'
    id = Column(Integer, primary_key=True, autoincrement=True)
    caminho_csv = Column(String(255), default=r"D:\Relatorios")
    remetente = Column(String(100), default="")
    senha = Column(String(100), default="")
    destinatario = Column(String(100), default="")
    servidor_smtp = Column(String(100), default="")
    porta_smtp = Column(Integer, default=465)

def obter_sessao(string_conexao: str = "sqlite:///impressoes.db"):
    try:
        engine = create_engine(string_conexao, connect_args={'check_same_thread': False})
        Base.metadata.create_all(engine)
        
        with engine.begin() as conn:
            try: conn.execute(text("ALTER TABLE mapeamento_terminais ADD COLUMN departamento VARCHAR(100)"))
            except Exception: pass
                
        Sessao = sessionmaker(bind=engine)
        return Sessao(), engine
    except SQLAlchemyError as erro:
        print(f"Erro no SQLite: {erro}")
        raise