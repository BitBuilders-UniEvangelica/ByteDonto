"""
ByteDonto — Seed de dados de demonstração.

Popula o banco com um cenário completo para testes:
  - Configura o proprietário (conta do dono) + clínica
  - Cria 1 atendente (Recepção) e 1 profissional (Especialista)
  - Cria pacientes, consultas, lançamentos financeiros e um plano de tratamento

Como rodar:
    cd backend_dev
    venv/bin/python seed_demo.py

Contas: os e-mails e senhas vêm do .env (DEMO_DONO_EMAIL, DEMO_DONO_SENHA,
DEMO_RECEPCAO_EMAIL, DEMO_RECEPCAO_SENHA, DEMO_ESPECIALISTA_EMAIL,
DEMO_ESPECIALISTA_SENHA). Senha não informada é gerada na hora e mostrada no
fim; quem já existe mantém a senha que tem. Nada de credencial fica no código.

Pode rodar mais de uma vez: a clínica e a equipe não são duplicadas.
Pacientes/consultas/financeiro só são criados se a clínica ainda não tiver pacientes.
"""
import os
import random
import secrets
from datetime import datetime, timedelta, timezone

from config import Config
from app.database import create_client
from app.auth_utils import PERMISSOES_PADRAO

admin = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

# ---- Configuração das contas -------------------------------------------------
OWNER_EMAIL = os.getenv("DEMO_DONO_EMAIL", "dono.demo@bytedonto.com")
RECEP_EMAIL = os.getenv("DEMO_RECEPCAO_EMAIL", "recepcao.demo@bytedonto.com")
ESPEC_EMAIL = os.getenv("DEMO_ESPECIALISTA_EMAIL", "profissional.demo@bytedonto.com")

PERMISSOES_RECEPCAO = PERMISSOES_PADRAO["Recepção"]
PERMISSOES_ESPECIALISTA = PERMISSOES_PADRAO["Especialista"]


def gerar_cpf():
    """Gera um CPF válido (com dígitos verificadores corretos)."""
    base = [random.randint(0, 9) for _ in range(9)]

    def dv(nums):
        peso = len(nums) + 1
        soma = sum(p * (peso - i) for i, p in enumerate(nums))
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    d1 = dv(base)
    d2 = dv(base + [d1])
    return "".join(map(str, base + [d1, d2]))


def achar_auth_user(email):
    for u in admin.auth.admin.list_users():
        if (getattr(u, "email", "") or "").lower() == email.lower():
            return u
    return None


def garantir_auth_user(email, variavel_senha):
    """Retorna (user_id, senha_exibida).

    Se a senha estiver no .env, ela é aplicada (conta nova ou existente).
    Sem senha no .env: conta nova recebe uma senha aleatória; conta existente
    mantém a dela (senha_exibida fica None).
    """
    senha_env = os.getenv(variavel_senha)
    user = achar_auth_user(email)
    if user:
        if senha_env:
            admin.auth.admin.update_user_by_id(user.id, {"password": senha_env})
        return user.id, senha_env
    senha = senha_env or secrets.token_urlsafe(12)
    novo = admin.auth.admin.create_user(
        {"email": email, "password": senha, "email_confirm": True}
    )
    return novo.user.id, senha


def upsert_perfil(uid, nome, papel, clinica_id=None, permissoes=None):
    dados = {"nome": nome, "papel": papel}
    if clinica_id:
        dados["clinica_id"] = clinica_id
    if permissoes is not None:
        dados["permissoes"] = permissoes
    existe = admin.table("usuarios").select("id").eq("id", uid).execute().data
    if existe:
        admin.table("usuarios").update(dados).eq("id", uid).execute()
    else:
        admin.table("usuarios").insert({**dados, "id": uid}).execute()


def iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


print("=" * 60)
print("ByteDonto — Seed de demonstração")
print("=" * 60)

# ---- 1. Proprietário ---------------------------------------------------------
owner_id, owner_senha = garantir_auth_user(OWNER_EMAIL, "DEMO_DONO_SENHA")
print(f"\n[1] Proprietário: {OWNER_EMAIL}")

# ---- 2. Clínica --------------------------------------------------------------
perfil = admin.table("usuarios").select("clinica_id").eq("id", owner_id).execute().data
clinica_id = perfil[0]["clinica_id"] if (perfil and perfil[0].get("clinica_id")) else None

if not clinica_id:
    base_clinica = {
        "nome_fantasia": "OdontoByte — Clínica Modelo",
        "razao_social": "OdontoByte Serviços Odontológicos LTDA",
        "cnpj": "11222333000181",
        "dono_id": owner_id,
    }
    extras = {
        "telefone": "1133224455",
        "endereco": {"logradouro": "Av. Paulista, 1000", "cidade": "São Paulo",
                     "estado": "SP", "pais": "Brasil"},
    }
    try:
        clinica = admin.table("clinicas").insert({**base_clinica, **extras}).execute().data[0]
    except Exception:
        # Migração de colunas (telefone/endereco) ainda não aplicada
        clinica = admin.table("clinicas").insert(base_clinica).execute().data[0]
    clinica_id = clinica["id"]
    print(f"[2] Clínica criada: OdontoByte — Clínica Modelo")
else:
    print(f"[2] Clínica já existente reutilizada")

upsert_perfil(owner_id, "Proprietário Demo", "Dono", clinica_id, {})

# ---- 3. Equipe ---------------------------------------------------------------
recep_id, recep_senha = garantir_auth_user(RECEP_EMAIL, "DEMO_RECEPCAO_SENHA")
upsert_perfil(recep_id, "Ana Recepção", "Recepção", clinica_id, PERMISSOES_RECEPCAO)

espec_id, espec_senha = garantir_auth_user(ESPEC_EMAIL, "DEMO_ESPECIALISTA_SENHA")
upsert_perfil(espec_id, "Dr. Bruno Especialista", "Especialista", clinica_id, PERMISSOES_ESPECIALISTA)
print(f"[3] Equipe pronta: 1 atendente (Recepção) + 1 profissional (Especialista)")

# ---- 4. Pacientes + consultas + financeiro + plano ---------------------------
ja_tem = admin.table("pacientes").select("id").eq("clinica_id", clinica_id).execute().data
if ja_tem:
    print(f"[4] A clínica já possui {len(ja_tem)} paciente(s) — seed de pacientes/consultas/financeiro PULADO (evita duplicar).")
else:
    pacientes_def = [
        {
            "nome": "Maria Fernanda Souza", "genero": "Feminino",
            "data_nascimento": "1990-04-15", "telefone_whatsapp": "11991234567",
            "email": "maria.souza@email.com",
            "endereco": {"cep": "01310100", "rua": "Av. Paulista", "numero": "900",
                         "bairro": "Bela Vista", "cidade": "São Paulo", "estado": "SP"},
            "anamnese": {"alergias": "Penicilina", "condicoes": "Hipertensão controlada",
                         "medicacoes": "Losartana 50mg", "drogas": "Nega",
                         "cirurgias": "Apendicectomia (2015)",
                         "emergencia_nome": "Carlos Souza", "emergencia_telefone": "11997654321"},
        },
        {
            "nome": "João Carlos Lima", "genero": "Masculino",
            "data_nascimento": "1985-11-02", "telefone_whatsapp": "11988887777",
            "email": "joao.lima@email.com",
            "endereco": {"cep": "04538132", "rua": "Rua Funchal", "numero": "200",
                         "bairro": "Vila Olímpia", "cidade": "São Paulo", "estado": "SP"},
            "anamnese": {"alergias": "", "condicoes": "Diabetes tipo 2",
                         "medicacoes": "Metformina", "drogas": "Tabagista",
                         "cirurgias": "", "emergencia_nome": "Sandra Lima",
                         "emergencia_telefone": "11990001122"},
        },
        {
            "nome": "Beatriz Almeida Castro", "genero": "Feminino",
            "data_nascimento": "2001-07-28", "telefone_whatsapp": "11993336688",
            "email": "beatriz.castro@email.com",
            "endereco": {"cep": "05407002", "rua": "Rua Cardeal Arcoverde", "numero": "150",
                         "bairro": "Pinheiros", "cidade": "São Paulo", "estado": "SP"},
            "anamnese": {"alergias": "", "condicoes": "", "medicacoes": "",
                         "drogas": "Nega", "cirurgias": "", "emergencia_nome": "",
                         "emergencia_telefone": ""},
        },
    ]
    pacientes = []
    for p in pacientes_def:
        row = admin.table("pacientes").insert({
            "clinica_id": clinica_id, "cpf": gerar_cpf(), "status": "Ativo", **p
        }).execute().data[0]
        pacientes.append(row)

    agora = datetime.now(timezone.utc)
    # Consultas: 1 finalizada, 1 hoje, 1 futura
    admin.table("atendimentos").insert([
        {"clinica_id": clinica_id, "paciente_id": pacientes[0]["id"], "dentista_id": espec_id,
         "data_agendada": iso(agora - timedelta(days=7)), "tipo_atendimento": "Primeira Avaliação",
         "procedimentos_descritos": "Profilaxia + avaliação inicial",
         "evolucao_clinica": "Paciente apresentou boa higiene. Realizada limpeza completa.",
         "status": "Finalizado"},
        {"clinica_id": clinica_id, "paciente_id": pacientes[1]["id"], "dentista_id": espec_id,
         "data_agendada": iso(agora.replace(hour=14, minute=0)), "tipo_atendimento": "Retorno",
         "procedimentos_descritos": "Restauração dente 26", "status": "Agendado"},
        {"clinica_id": clinica_id, "paciente_id": pacientes[2]["id"], "dentista_id": espec_id,
         "data_agendada": iso(agora + timedelta(days=3)), "tipo_atendimento": "Procedimento",
         "procedimentos_descritos": "Extração siso", "status": "Agendado"},
    ]).execute()

    # Financeiro: 1 pago, 1 pendente
    admin.table("faturamento").insert([
        {"clinica_id": clinica_id, "paciente_id": pacientes[0]["id"], "dentista_responsavel": espec_id,
         "valor": 250.00, "forma_pagamento": "Pix", "status_pagamento": "Pago"},
        {"clinica_id": clinica_id, "paciente_id": pacientes[1]["id"], "dentista_responsavel": espec_id,
         "valor": 1200.00, "forma_pagamento": "Cartão Crédito", "status_pagamento": "Pendente"},
    ]).execute()

    # Plano de tratamento com 2 itens
    plano = admin.table("planos_tratamento").insert({
        "clinica_id": clinica_id, "paciente_id": pacientes[0]["id"], "dentista_id": espec_id,
        "titulo": "Plano de Reabilitação Oral", "status": "Orcamento",
        "valor_total": 800.00, "observacoes": "Tratamento em duas etapas.",
    }).execute().data[0]
    admin.table("plano_itens").insert([
        {"plano_id": plano["id"], "procedimento": "Restauração em resina", "dente": "26",
         "quantidade": 1, "valor_unitario": 300.00, "status": "Pendente", "ordem": 1},
        {"plano_id": plano["id"], "procedimento": "Clareamento dental", "dente": "—",
         "quantidade": 1, "valor_unitario": 500.00, "status": "Pendente", "ordem": 2},
    ]).execute()

    print(f"[4] Criados: 3 pacientes, 3 consultas, 2 lançamentos financeiros, 1 plano de tratamento")

# ---- Resumo ------------------------------------------------------------------
print("\n" + "=" * 60)
print("SEED CONCLUÍDO — contas de acesso")
print("=" * 60)
for titulo, email, senha in (
    ("PROPRIETÁRIO (Dono)", OWNER_EMAIL, owner_senha),
    ("ATENDENTE (Recepção)", RECEP_EMAIL, recep_senha),
    ("PROFISSIONAL (Especialista)", ESPEC_EMAIL, espec_senha),
):
    print(f"\n  {titulo}")
    print(f"    e-mail: {email}")
    print(f"    senha : {senha or '(mantida: a conta já existia)'}")
print()
