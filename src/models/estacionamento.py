from typing import Optional
from sqlalchemy import Column, Integer, String, Numeric, ForeignKey
from pydantic import BaseModel, ConfigDict
from .base import Base

class EstacionamentoDB(Base):
    __tablename__ = "estacionamento"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), nullable=False)
    endereco = Column(String)
    total_vagas = Column(Integer, nullable=False)
    valor_primeira_hora = Column(Numeric(10, 2))
    valor_demais_horas = Column(Numeric(10, 2))
    valor_diaria = Column(Numeric(10, 2))
    admin_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)


class EstacionamentoCreate(BaseModel):
    nome: str
    total_vagas: int
    endereco: Optional[str] = None
    valor_primeira_hora: Optional[float] = None
    valor_demais_horas: Optional[float] = None
    valor_diaria: Optional[float] = None

class Estacionamento(EstacionamentoCreate):
    id: int
    admin_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
