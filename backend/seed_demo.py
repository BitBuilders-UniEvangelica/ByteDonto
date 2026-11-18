"""
ByteDonto — Seed de dados de demonstração (SOMENTE ambiente local).

Popula o banco com um cenário completo para testes:
  - Configura o proprietário (conta do dono) + clínica
  - Cria 1 atendente (Recepção) e 1 profissional (Especialista)
  - Cria pacientes, consultas, lançamentos financeiros e um plano de tratamento

Segurança:
  - Recusa rodar em produção: exige APP_ENV=development (ou local) explícito e
    aborta se detectar o Railway ou APP_ENV=production.
  - Nenhum e-mail ou senha fica no código: tudo vem de variáveis de ambiente
    (veja backend/.env.example, seção "Seed de demonstração").
  - NUNCA redefine a senha nem sobrescreve o perfil de uma conta já existente.
  - Não imprime senhas.

Como rodar:
    cd backend
    APP_ENV=development venv/bin/python seed_demo.py

Pode rodar mais de uma vez: a clínica e a equipe não são duplicadas.
Pacientes/consultas/financeiro só são criados se a clínica ainda não tiver pacientes.
"""
import os
import random
import sys
from datetime import datetime, timedelta, timezone

AMBIENTES_PERMITIDOS = {"development", "local"}
SENHA_MIN_SEED = 12


class SeedBloqueado(RuntimeError):
    """O seed não pode rodar neste ambiente/configuração."""


def verificar_ambiente(env=None):
    """Bloqueia a execução fora de ambiente local. Default-deny."""
    env = os.environ if env is None else env
    if env.get("RAILWAY_ENVIRONMENT") or env.get("RAILWAY_ENVIRONMENT_NAME") or env.get("RAILWAY_PROJECT_ID"):
        raise SeedBloqueado("Ambiente Railway detectado — o seed de demonstração nunca roda em deploy.")
    app_env = (env.get("APP_ENV") or "").strip().lower()
    if app_env not in AMBIENTES_PERMITIDOS:
        raise SeedBloqueado(
            "O seed só roda com APP_ENV=development (ou local) definido explicitamente. "
            f"APP_ENV atual: {app_env or '(não definido)'}."
        )


def ler_configuracao(env=None):
    """Lê e valida as contas do seed a partir do ambiente."""
    env = os.environ if env is None else env
    contas = {}
    faltando = []
    for chave, papel in (("OWNER", "Dono"), ("RECEPCAO", "Recepção"), ("ESPECIALISTA", "Especialista")):
        email = (env.get(f"SEED_{chave}_EMAIL") or "").strip()
        senha = env.get(f"SEED_{chave}_PASSWORD") or ""
        if not email:
            faltando.append(f"SEED_{chave}_EMAIL")
        if not senha:
            faltando.append(f"SEED_{chave}_PASSWORD")
        elif len(senha) < SENHA_MIN_SEED:
            raise SeedBloqueado(f"SEED_{chave}_PASSWORD deve ter no mínimo {SENHA_MIN_SEED} caracteres.")
        contas[chave] = {"email": email, "senha": senha, "papel": papel}
    if faltando:
        raise SeedBloqueado("Variáveis ausentes: " + ", ".join(faltando) + ". Veja backend/.env.example.")
    emails = [c["email"].lower() for c in contas.values()]
    if len(set(emails)) != len(emails):
        raise SeedBloqueado("Os e-mails SEED_*_EMAIL precisam ser diferentes entre si.")
    contas["OWNER"]["nome"] = (env.get("SEED_OWNER_NOME") or "Proprietário Demo").strip()
    return contas


admin = None  # cliente Supabase (service role) criado em main(), após as verificações


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
    """Procura o usuário no Auth percorrendo todas as páginas da listagem."""
    pagina = 1
    while True:
        usuarios = admin.auth.admin.list_users(page=pagina, per_page=1000)
        for u in usuarios:
            if (getattr(u, "email", "") or "").lower() == email.lower():
                return u
        if len(usuarios) < 1000:
            return None
        pagina += 1


def garantir_auth_user(email, senha):
    """Retorna (user_id, foi_criado).

    Se a conta já existir, ela é reutilizada SEM alterar a senha.
    """
    user = achar_auth_user(email)
    if user:
        return user.id, False
    novo = admin.auth.admin.create_user(
        {"email": email, "password": senha, "email_confirm": True}
    )
    return novo.user.id, True


def garantir_perfil(uid, nome, papel, clinica_id=None, permissoes=None):
    """Cria o perfil se não existir. Perfil existente NUNCA é sobrescrito.

    Retorna o perfil (dict) que ficou valendo.
    """
    existe = admin.table("usuarios").select("id, papel, clinica_id").eq("id", uid).execute().data
    if existe:
        return existe[0]
    dados = {"id": uid, "nome": nome, "papel": papel}
    if clinica_id:
        dados["clinica_id"] = clinica_id
    if permissoes is not None:
        dados["permissoes"] = permissoes
    admin.table("usuarios").insert(dados).execute()
    return dados


def iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def main():
    global admin
    try:
        verificar_ambiente()
        contas = ler_configuracao()
    except SeedBloqueado as e:
        print(f"[seed bloqueado] {e}", file=sys.stderr)
        return 2

    # Imports tardios: só depois das travas de ambiente tocamos no Supabase.
    from config import Config, validar_config
    from supabase import create_client
    from app.auth_utils import PERMISSOES_PADRAO

    validar_config(Config)
    admin = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
    try:
        _executar(contas, PERMISSOES_PADRAO)
    except SeedBloqueado as e:
        print(f"[seed interrompido] {e}", file=sys.stderr)
        return 2
    return 0


def _executar(contas, PERMISSOES_PADRAO):
    print("=" * 60)
    print("ByteDonto — Seed de demonstração")
    print("=" * 60)

    # ---- 1. Proprietário ---------------------------------------------------------
    owner = contas["OWNER"]
    owner_id, owner_novo = garantir_auth_user(owner["email"], owner["senha"])
    print(f"\n[1] Proprietário: {owner['email']} ({'conta criada agora' if owner_novo else 'conta já existia — senha mantida'})")
    perfil_owner = garantir_perfil(owner_id, owner["nome"], "Dono", None, {})
    if perfil_owner.get("papel") != "Dono":
        raise SeedBloqueado(
            "SEED_OWNER_EMAIL pertence a uma conta que não é de proprietário. "
            "Use outro e-mail — o seed não altera perfis existentes."
        )

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
        # Vincula a clínica criada ao proprietário (só quando ele não tinha nenhuma).
        admin.table("usuarios").update({"clinica_id": clinica_id}).eq("id", owner_id).execute()
        print(f"[2] Clínica criada: OdontoByte — Clínica Modelo")
    else:
        print(f"[2] Clínica já existente reutilizada")

    # ---- 3. Equipe ---------------------------------------------------------------
    membros = {}
    for chave, nome, permissoes in (
        ("RECEPCAO", "Ana Recepção (Demo)", dict(PERMISSOES_PADRAO["Recepção"])),
        ("ESPECIALISTA", "Dr. Bruno Especialista (Demo)", dict(PERMISSOES_PADRAO["Especialista"])),
    ):
        conta = contas[chave]
        uid, novo = garantir_auth_user(conta["email"], conta["senha"])
        perfil_membro = garantir_perfil(uid, nome, conta["papel"], clinica_id, permissoes)
        if perfil_membro.get("clinica_id") != clinica_id or perfil_membro.get("papel") != conta["papel"]:
            raise SeedBloqueado(
                f"SEED_{chave}_EMAIL já pertence a uma conta de outra clínica/papel. "
                "Use outro e-mail — o seed não altera perfis existentes."
            )
        membros[chave] = uid
        print(f"    {conta['papel']}: {conta['email']} ({'criada agora' if novo else 'já existia — senha mantida'})")
    recep_id, espec_id = membros["RECEPCAO"], membros["ESPECIALISTA"]
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
                "email": "maria.souza@example.com",
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
                "email": "joao.lima@example.com",
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
                "email": "beatriz.castro@example.com",
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
    print("SEED CONCLUÍDO")
    print("=" * 60)
    for chave, rotulo in (("OWNER", "PROPRIETÁRIO (Dono)"), ("RECEPCAO", "ATENDENTE (Recepção)"),
                          ("ESPECIALISTA", "PROFISSIONAL (Especialista)")):
        print(f"\n  {rotulo}")
        print(f"    e-mail: {contas[chave]['email']}")
        print(f"    senha : definida em SEED_{chave}_PASSWORD (contas já existentes mantêm a senha atual)")
    print()


if __name__ == "__main__":
    sys.exit(main())
