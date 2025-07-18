from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, cast, Date
from src.database import get_db
from src.models import acesso as models_acesso
from src.models import estacionamento as models_estacionamento
from src.models import faturamento as models_faturamento
from src.models.dashboard import OcupacaoHoraData, VisaoGeralMetrics, VisaoGeralResponse
from src.models.usuario import Usuario
from src.auth.dependencies import get_current_user

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)

brazil_timezone = ZoneInfo('America/Sao_Paulo')

@router.get("/{estacionamento_id}", response_model=VisaoGeralResponse)
def get_visao_geral_data(
    estacionamento_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    db_estacionamento = db.query(models_estacionamento.EstacionamentoDB).filter(
        models_estacionamento.EstacionamentoDB.id == estacionamento_id
    ).first()

    if not db_estacionamento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Estacionamento não encontrado.")

    authorized_admin_id = current_user.id if current_user.role == 'admin' else current_user.admin_id
    if db_estacionamento.admin_id != authorized_admin_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não tem permissão para acessar os dados deste estacionamento.")

    today_local_date = datetime.now(brazil_timezone).date()
    yesterday_local_date = today_local_date - timedelta(days=1)

    vagas_ocupadas = db.query(models_acesso.AcessoDB).filter(
        models_acesso.AcessoDB.id_estacionamento == estacionamento_id,
        models_acesso.AcessoDB.hora_saida.is_(None)
    ).count()

    total_vagas = db_estacionamento.total_vagas

    entradas_hoje = db.query(models_acesso.AcessoDB).filter(
        models_acesso.AcessoDB.id_estacionamento == estacionamento_id,
        cast(models_acesso.AcessoDB.hora_entrada, Date) == today_local_date
    ).count()

    saidas_hoje = db.query(models_acesso.AcessoDB).filter(
        models_acesso.AcessoDB.id_estacionamento == estacionamento_id,
        cast(models_acesso.AcessoDB.hora_saida, Date) == today_local_date
    ).count()

    faturamento_hoje_result = db.query(func.sum(models_faturamento.FaturamentoDB.valor)).filter(
        and_(
            cast(models_faturamento.FaturamentoDB.data_faturamento, Date) == today_local_date,
            models_faturamento.FaturamentoDB.id_acesso == models_acesso.AcessoDB.id,
            models_acesso.AcessoDB.id_estacionamento == estacionamento_id
        )
    ).scalar()
    faturamento_hoje = float(faturamento_hoje_result) if faturamento_hoje_result else 0.0

    entradas_ontem = db.query(models_acesso.AcessoDB).filter(
        models_acesso.AcessoDB.id_estacionamento == estacionamento_id,
        cast(models_acesso.AcessoDB.hora_entrada, Date) == yesterday_local_date
    ).count()
    saidas_ontem = db.query(models_acesso.AcessoDB).filter(
        models_acesso.AcessoDB.id_estacionamento == estacionamento_id,
        cast(models_acesso.AcessoDB.hora_saida, Date) == yesterday_local_date
    ).count()

    ocupacao_hoje_delta = entradas_hoje - saidas_hoje
    ocupacao_ontem_delta = entradas_ontem - saidas_ontem

    porcentagem_ocupacao = 0.0
    if ocupacao_ontem_delta != 0:
        porcentagem_ocupacao = ((ocupacao_hoje_delta - ocupacao_ontem_delta) / abs(ocupacao_ontem_delta)) * 100

    acessos_por_hora_dict = {i: 0 for i in range(24)}

    acessos_hoje_local_range = db.query(models_acesso.AcessoDB).filter(
        models_acesso.AcessoDB.id_estacionamento == estacionamento_id,
        cast(models_acesso.AcessoDB.hora_entrada, Date) == today_local_date
    ).all()

    for acesso in acessos_hoje_local_range:
        hora_entrada_local_aware = acesso.hora_entrada.replace(tzinfo=brazil_timezone) if acesso.hora_entrada.tzinfo is None else acesso.hora_entrada
        hora = hora_entrada_local_aware.hour
        acessos_por_hora_dict[hora] = acessos_por_hora_dict.get(hora, 0) + 1

    grafico_ocupacao_hora_data = [
        OcupacaoHoraData(hora=h, acessos=acessos_por_hora_dict[h]) for h in range(24)
    ]

    metrics = VisaoGeralMetrics(
        vagas_ocupadas=vagas_ocupadas,
        total_vagas=total_vagas,
        porcentagem_ocupacao=round(porcentagem_ocupacao, 2),
        entradas_hoje=entradas_hoje,
        saidas_hoje=saidas_hoje,
        faturamento_hoje=faturamento_hoje
    )

    return VisaoGeralResponse(
        metrics=metrics,
        grafico_ocupacao_hora=grafico_ocupacao_hora_data
    )
