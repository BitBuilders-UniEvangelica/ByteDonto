"""
ByteDonto — Seed de dados de demonstração.

Popula o banco com um cenário completo para testes:
  - Configura o proprietário (conta do dono) + clínica
  - Cria 1 atendente (Recepção) e 1 profissional (Especialista)
  - Cria pacientes, consultas, lançamentos financeiros e um plano de tratamento

Como rodar:
    cd backend
    venv/bin/python seed_demo.py

Pode rodar mais de uma vez: a clínica e a equipe não são duplicadas.
Pacientes/consultas/financeiro só são criados se a clínica ainda não tiver pacientes.
"""
import random
from datetime import datetime, timedelta, timezone

from config import Config
from app.database import create_client

admin = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

# ---- Configuração das contas -------------------------------------------------
OWNER_EMAIL = "vitorhugosteam3@gmail.com"
OWNER_SENHA_SE_NOVO = "Bytedonto@2026"   # usada só se a conta ainda não existir

RECEP_EMAIL, RECEP_SENHA = "recepcao.demo@bytedonto.com", "Recepcao@2026"
ESPEC_EMAIL, ESPEC_SENHA = "profissional.demo@bytedonto.com", "Profissional@2026"

PERMISSOES_RECEPCAO = {
    "ver_pacientes": True, "editar_pacientes": True, "ver_prontuario": False,
    "editar_prontuario": False, "ver_agenda": True, "agendar_consultas": True,
    "cancelar_consultas": True, "ver_financeiro": True,
}
PERMISSOES_ESPECIALISTA = {
    "ver_pacientes": True, "editar_pacientes": False, "ver_prontuario": True,
    "editar_prontuario": True, "ver_agenda": True, "agendar_consultas": False,
    "cancelar_consultas": False, "ver_financeiro": False,
}


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


def garantir_auth_user(email, senha):
    """Retorna (user_id, foi_criado). Se já existir, garante a senha conhecida."""
    user = achar_auth_user(email)
    if user:
        try:
            admin.auth.admin.update_user_by_id(user.id, {"password": senha})
        except Exception:
            pass
        return user.id, False
    novo = admin.auth.admin.create_user(
        {"email": email, "password": senha, "email_confirm": True}
    )
    return novo.user.id, True


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
owner_id, owner_novo = garantir_auth_user(OWNER_EMAIL, OWNER_SENHA_SE_NOVO)
print(f"\n[1] Proprietário: {OWNER_EMAIL} ({'conta criada agora' if owner_novo else 'conta já existia'})")

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

upsert_perfil(owner_id, "Victor Hugo (Proprietário)", "Dono", clinica_id, {})

# ---- 3. Equipe ---------------------------------------------------------------
recep_id, recep_novo = garantir_auth_user(RECEP_EMAIL, RECEP_SENHA)
upsert_perfil(recep_id, "Ana Recepção", "Recepção", clinica_id, PERMISSOES_RECEPCAO)

espec_id, espec_novo = garantir_auth_user(ESPEC_EMAIL, ESPEC_SENHA)
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
print("SEED CONCLUÍDO — credenciais de acesso")
print("=" * 60)
print(f"\n  PROPRIETÁRIO (Dono)")
print(f"    e-mail: {OWNER_EMAIL}")
print(f"    senha : {'(use a senha que você já definiu)' if not owner_novo else OWNER_SENHA_SE_NOVO}")
print(f"\n  ATENDENTE (Recepção)")
print(f"    e-mail: {RECEP_EMAIL}")
print(f"    senha : {RECEP_SENHA}")
print(f"\n  PROFISSIONAL (Especialista)")
print(f"    e-mail: {ESPEC_EMAIL}")
print(f"    senha : {ESPEC_SENHA}")
print()
