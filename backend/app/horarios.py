"""Convenção única de data/hora da agenda.

Comportamento encontrado antes desta correção (documentado):
  * O frontend envia `data_agendada` SEM fuso ("2026-11-10T09:00:00" = 09:00 no
    relógio da clínica).
  * A coluna é TIMESTAMPTZ e as sessões do banco usam UTC (Supabase/PostgREST e
    o provider local), então o valor ficava gravado como 09:00 UTC e voltava
    como "2026-11-10T09:00:00+00:00".
  * A agenda da recepção exibe `data_agendada.slice(11, 16)` -> "09:00" (certo);
    o painel do especialista, o registro clínico e a ficha do paciente usam
    `new Date(...)` -> 06:00 no Brasil (3 h a menos).

Convenção adotada (sem migrar dados): `data_agendada` guarda o HORÁRIO DE
PAREDE da clínica. É exatamente o que já está gravado em produção, então nada
precisa ser convertido. Para o frontend:
  * entrada sem fuso      -> mantida como está (horário de parede);
  * entrada COM fuso      -> convertida para o fuso da clínica (APP_TIMEZONE)
                             e gravada como horário de parede;
  * saída                 -> sempre sem fuso ("2026-11-10T09:00:00"), que o
                             `new Date()` do navegador lê como horário local e o
                             `slice(11, 16)` continua lendo como "09:00".
Assim todas as telas mostram o mesmo horário, sem mudar o frontend.
"""

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from config import Config


def fuso():
    return ZoneInfo(Config.APP_TIMEZONE or "America/Sao_Paulo")


def hoje():
    """Data de hoje no fuso da clínica (o servidor do Railway roda em UTC)."""
    return datetime.now(fuso()).date()


def _parse(valor):
    texto = str(valor).strip()
    if texto.endswith(("Z", "z")):
        texto = texto[:-1] + "+00:00"
    return datetime.fromisoformat(texto)


def normalizar_entrada(valor):
    """Valida e converte `data_agendada` recebida para horário de parede (sem fuso).

    Levanta ValueError (-> HTTP 400) se não for uma data/hora ISO válida."""
    if valor is None or not str(valor).strip():
        raise ValueError("O campo 'data_agendada' é obrigatório.")
    try:
        dt = _parse(valor)
    except (TypeError, ValueError):
        raise ValueError("data_agendada inválida. Use o formato AAAA-MM-DDTHH:MM (ex.: 2026-11-10T09:00).")
    if isinstance(dt, datetime) and dt.tzinfo is not None:
        dt = dt.astimezone(fuso()).replace(tzinfo=None)
    return dt.replace(microsecond=0).isoformat(timespec="seconds")


def para_banco(horario_de_parede):
    """Valor para gravar/filtrar no banco: o horário de parede marcado como UTC.

    Explícito ("+00:00") para não depender do fuso da sessão do banco (o
    Supabase usa UTC hoje, mas um ajuste de fuso no projeto deslocaria tudo)."""
    return f"{horario_de_parede}+00:00"


def para_saida(valor):
    """Valor lido do banco -> horário de parede sem fuso (string ISO)."""
    if not valor:
        return valor
    try:
        dt = _parse(valor) if not isinstance(valor, datetime) else valor
    except (TypeError, ValueError):
        return valor
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.isoformat(timespec="seconds")


def inicio_do_dia(d: date):
    return para_banco(f"{d.isoformat()}T00:00:00")


def fim_do_dia(d: date):
    return para_banco(f"{d.isoformat()}T23:59:59")
