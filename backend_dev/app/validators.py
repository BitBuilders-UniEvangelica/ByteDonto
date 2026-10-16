"""Helpers de validação de entrada do servidor.

Todas as funções levantam ValueError com mensagens em português quando a
validação falha, permitindo que as rotas façam try/except e retornem HTTP 400.
"""

import re
from datetime import date, datetime


def _so_digitos(valor):
    """Remove qualquer caractere que não seja dígito."""
    return re.sub(r"\D", "", str(valor or ""))


def campo_obrigatorio(valor, campo):
    """Garante que um campo de texto foi preenchido."""
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        raise ValueError(f"O campo '{campo}' é obrigatório.")
    return valor


def validar_cpf(cpf):
    """Valida um CPF (11 dígitos + dígitos verificadores).

    Aceita CPF mascarado ou apenas dígitos. Retorna a string limpa.
    """
    digitos = _so_digitos(cpf)

    if len(digitos) != 11:
        raise ValueError("CPF inválido.")

    # Rejeita sequências repetidas (ex: 00000000000)
    if digitos == digitos[0] * 11:
        raise ValueError("CPF inválido.")

    # Primeiro dígito verificador
    soma = sum(int(digitos[i]) * (10 - i) for i in range(9))
    resto = (soma * 10) % 11
    dv1 = 0 if resto == 10 else resto

    # Segundo dígito verificador
    soma = sum(int(digitos[i]) * (11 - i) for i in range(10))
    resto = (soma * 10) % 11
    dv2 = 0 if resto == 10 else resto

    if dv1 != int(digitos[9]) or dv2 != int(digitos[10]):
        raise ValueError("CPF inválido.")

    return digitos


def validar_cnpj(cnpj):
    """Valida um CNPJ (14 dígitos + dígitos verificadores).

    Aceita CNPJ mascarado ou apenas dígitos. Retorna a string limpa.
    """
    digitos = _so_digitos(cnpj)

    if len(digitos) != 14:
        raise ValueError("CNPJ inválido.")

    if digitos == digitos[0] * 14:
        raise ValueError("CNPJ inválido.")

    def _calcular_dv(base, pesos):
        soma = sum(int(base[i]) * pesos[i] for i in range(len(pesos)))
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    dv1 = _calcular_dv(digitos[:12], pesos1)
    dv2 = _calcular_dv(digitos[:12] + str(dv1), pesos2)

    if dv1 != int(digitos[12]) or dv2 != int(digitos[13]):
        raise ValueError("CNPJ inválido.")

    return digitos


_EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validar_email(email):
    """Valida o formato de um e-mail. Retorna o e-mail (sem espaços)."""
    valor = (email or "").strip()
    if not _EMAIL_REGEX.match(valor):
        raise ValueError("E-mail inválido.")
    return valor


def validar_telefone(tel):
    """Valida um telefone (10 ou 11 dígitos). Retorna apenas os dígitos."""
    digitos = _so_digitos(tel)
    if len(digitos) not in (10, 11):
        raise ValueError("Telefone inválido.")
    return digitos


def validar_data_nascimento(data):
    """Valida uma data de nascimento no formato YYYY-MM-DD.

    A data deve ser válida, não estar no futuro e não ter mais de 120 anos.
    Retorna a string no formato YYYY-MM-DD.
    """
    valor = (str(data or "")).strip()
    try:
        nascimento = datetime.strptime(valor, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Data de nascimento inválida.")

    hoje = date.today()
    if nascimento > hoje:
        raise ValueError("A data de nascimento não pode estar no futuro.")

    if nascimento.year < hoje.year - 120:
        raise ValueError("Data de nascimento inválida.")

    return nascimento.isoformat()


def validar_valor(valor):
    """Valida um valor numérico maior que zero. Retorna float."""
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ValueError("Valor deve ser maior que zero.")

    if numero <= 0:
        raise ValueError("Valor deve ser maior que zero.")

    return numero


def validar_enum(valor, opcoes, campo):
    """Garante que o valor está dentro das opções permitidas."""
    if valor not in opcoes:
        opcoes_texto = ", ".join(str(o) for o in opcoes)
        raise ValueError(f"O campo '{campo}' deve ser um de: {opcoes_texto}.")
    return valor
