import pymongo
import re
from datetime import datetime
import os
from dotenv import load_dotenv

# Carregar variáveis do arquivo .env
load_dotenv()

# ==================== CONFIGURAÇÃO ====================
# Usar a mesma URI do seu arquivo .env
MONGO_URI = os.getenv('MONGO_URI', 'mongodb+srv://cadastro_db_user:0Vvl27ZcrYqaD8Kj@cluster0.6mtltjd.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
DB_NAME = os.getenv('DB_NAME', 'creche_el_shadday')

print(f"🔌 Conectando ao MongoDB...")
print(f"📦 Banco de dados: {DB_NAME}")

# Conectar ao MongoDB com as mesmas configurações do seu sistema
try:
    client = pymongo.MongoClient(
        MONGO_URI,
        tls=True,
        tlsAllowInvalidCertificates=True,
        connectTimeoutMS=30000,
        socketTimeoutMS=30000,
        serverSelectionTimeoutMS=30000
    )
    
    # Testar conexão
    client.admin.command('ping')
    print("✅ Conectado ao MongoDB Atlas com sucesso!")
    
    db = client[DB_NAME]
    alunos_collection = db['alunos']
    
    # Listar coleções para confirmar
    collections = db.list_collection_names()
    print(f"📚 Coleções disponíveis: {collections}")
    
except Exception as e:
    print(f"❌ Erro ao conectar: {e}")
    exit(1)

print("\n" + "=" * 70)
print("📝 INICIANDO PADRONIZAÇÃO DOS DADOS")
print("=" * 70)

# ==================== FUNÇÕES DE CAPITALIZAÇÃO ====================

def capitalizar_texto(texto):
    """Capitaliza texto geral (endereços, turmas, etc.)"""
    if not texto or not isinstance(texto, str):
        return texto
    
    texto = str(texto).strip()
    if not texto:
        return texto
    
    palavras_especiais = ['RG', 'CPF', 'CIN', 'CNPJ', 'TEA', 'TDAH', 'HIV', 'AIDS', 'SP', 'RJ', 'MG', 'CEIC', 'CEIM']
    
    palavras = texto.lower().split(' ')
    palavras_cap = []
    
    for p in palavras:
        if not p:
            continue
        if p.upper() in palavras_especiais:
            palavras_cap.append(p.upper())
        elif '-' in p:
            partes = []
            for part in p.split('-'):
                if part:
                    partes.append(part[0].upper() + part[1:])
                else:
                    partes.append('')
            palavras_cap.append('-'.join(partes))
        else:
            palavras_cap.append(p[0].upper() + p[1:] if p else p)
    
    return ' '.join(palavras_cap)


def capitalizar_nome(nome):
    """Capitaliza nome próprio (respeita preposições)"""
    if not nome or not isinstance(nome, str):
        return nome
    
    nome = str(nome).strip()
    if not nome:
        return nome
    
    palavras_minusculas = {'da', 'de', 'do', 'das', 'dos', 'e', 'a', 'o', 'as', 'os'}
    
    # Tratar nomes com múltiplos espaços
    palavras = nome.lower().split()
    palavras_cap = []
    
    for i, p in enumerate(palavras):
        if not p:
            continue
        if i == 0:
            # Primeira palavra sempre com primeira letra maiúscula
            palavras_cap.append(p[0].upper() + p[1:])
        elif p in palavras_minusculas:
            # Preposições ficam minúsculas
            palavras_cap.append(p)
        elif p == 'e':
            # Conjunção 'e' fica minúscula
            palavras_cap.append(p)
        else:
            # Demais palavras capitalizadas
            palavras_cap.append(p[0].upper() + p[1:])
    
    return ' '.join(palavras_cap)


# ==================== CORREÇÃO DOS ALUNOS ====================

# Contadores
total_alunos = 0
alunos_modificados = 0

# Buscar todos os alunos
alunos = alunos_collection.find({})

for aluno in alunos:
    total_alunos += 1
    modificacoes = {}
    aluno_id = aluno.get('_id')
    nome_aluno = aluno.get('dados_pessoais', {}).get('nome', 'Sem nome')
    
    print(f"\n📌 Processando: {nome_aluno[:50]}...")
    
    # 1. CORRIGIR DADOS PESSOAIS
    if 'dados_pessoais' in aluno:
        dados_pessoais = aluno['dados_pessoais']
        
        # Nome do aluno
        if dados_pessoais.get('nome'):
            novo_nome = capitalizar_nome(dados_pessoais['nome'])
            if novo_nome != dados_pessoais['nome']:
                modificacoes['dados_pessoais.nome'] = novo_nome
                print(f"   📝 Nome: '{dados_pessoais['nome'][:40]}...' -> '{novo_nome[:40]}...'")
        
        # Naturalidade
        if dados_pessoais.get('naturalidade'):
            nova_naturalidade = capitalizar_texto(dados_pessoais['naturalidade'])
            if nova_naturalidade != dados_pessoais['naturalidade']:
                modificacoes['dados_pessoais.naturalidade'] = nova_naturalidade
                print(f"   📝 Naturalidade: '{dados_pessoais['naturalidade']}' -> '{nova_naturalidade}'")
        
        # Nacionalidade
        if dados_pessoais.get('nacionalidade'):
            nova_nacionalidade = capitalizar_texto(dados_pessoais['nacionalidade'])
            if nova_nacionalidade != dados_pessoais['nacionalidade']:
                modificacoes['dados_pessoais.nacionalidade'] = nova_nacionalidade
                print(f"   📝 Nacionalidade: '{dados_pessoais['nacionalidade']}' -> '{nova_nacionalidade}'")
        
        # Raça
        if dados_pessoais.get('raca'):
            nova_raca = capitalizar_texto(dados_pessoais['raca'])
            if nova_raca != dados_pessoais['raca']:
                modificacoes['dados_pessoais.raca'] = nova_raca
                print(f"   📝 Raça: '{dados_pessoais['raca']}' -> '{nova_raca}'")
    
    # 2. CORRIGIR ENDEREÇO
    if 'endereco' in aluno:
        endereco = aluno['endereco']
        
        if endereco.get('logradouro'):
            novo_logradouro = capitalizar_texto(endereco['logradouro'])
            if novo_logradouro != endereco['logradouro']:
                modificacoes['endereco.logradouro'] = novo_logradouro
                print(f"   📝 Logradouro: '{endereco['logradouro']}' -> '{novo_logradouro}'")
        
        if endereco.get('bairro'):
            novo_bairro = capitalizar_texto(endereco['bairro'])
            if novo_bairro != endereco['bairro']:
                modificacoes['endereco.bairro'] = novo_bairro
                print(f"   📝 Bairro: '{endereco['bairro']}' -> '{novo_bairro}'")
        
        if endereco.get('cidade'):
            nova_cidade = capitalizar_texto(endereco['cidade'])
            if nova_cidade != endereco['cidade']:
                modificacoes['endereco.cidade'] = nova_cidade
                print(f"   📝 Cidade: '{endereco['cidade']}' -> '{nova_cidade}'")
        
        if endereco.get('complemento'):
            novo_complemento = capitalizar_texto(endereco['complemento'])
            if novo_complemento != endereco['complemento']:
                modificacoes['endereco.complemento'] = novo_complemento
                print(f"   📝 Complemento: '{endereco['complemento']}' -> '{novo_complemento}'")
    
    # 3. CORRIGIR TURMA
    if 'turma' in aluno:
        turma = aluno['turma']
        
        if turma.get('turma'):
            nova_turma = capitalizar_texto(turma['turma'])
            # Corrigir "Infantil Ii" para "Infantil II"
            nova_turma = re.sub(r'Ii\b', 'II', nova_turma, flags=re.IGNORECASE)
            nova_turma = re.sub(r'Iii\b', 'III', nova_turma, flags=re.IGNORECASE)
            nova_turma = re.sub(r'Iv\b', 'IV', nova_turma, flags=re.IGNORECASE)
            if nova_turma != turma['turma']:
                modificacoes['turma.turma'] = nova_turma
                print(f"   📝 Turma: '{turma['turma']}' -> '{nova_turma}'")
        
        if turma.get('unidade'):
            nova_unidade = capitalizar_texto(turma['unidade'])
            if nova_unidade != turma['unidade']:
                modificacoes['turma.unidade'] = nova_unidade
                print(f"   📝 Unidade: '{turma['unidade']}' -> '{nova_unidade}'")
        
        if turma.get('periodo'):
            novo_periodo = capitalizar_texto(turma['periodo'])
            if novo_periodo != turma['periodo']:
                modificacoes['turma.periodo'] = novo_periodo
                print(f"   📝 Período: '{turma['periodo']}' -> '{novo_periodo}'")
    
    # 4. CORRIGIR SAÚDE
    if 'saude' in aluno:
        saude = aluno['saude']
        
        if saude.get('alergias'):
            nova_alergia = capitalizar_texto(saude['alergias'])
            if nova_alergia != saude['alergias']:
                modificacoes['saude.alergias'] = nova_alergia
                print(f"   📝 Alergias: '{saude['alergias'][:30]}...' -> '{nova_alergia[:30]}...'")
        
        if saude.get('medicamentos'):
            novo_medicamento = capitalizar_texto(saude['medicamentos'])
            if novo_medicamento != saude['medicamentos']:
                modificacoes['saude.medicamentos'] = novo_medicamento
                print(f"   📝 Medicamentos: '{saude['medicamentos'][:30]}...' -> '{novo_medicamento[:30]}...'")
        
        if saude.get('restricoes'):
            nova_restricao = capitalizar_texto(saude['restricoes'])
            if nova_restricao != saude['restricoes']:
                modificacoes['saude.restricoes'] = nova_restricao
                print(f"   📝 Restrições: '{saude['restricoes'][:30]}...' -> '{nova_restricao[:30]}...'")
        
        if saude.get('deficiencia_desc'):
            nova_desc = capitalizar_texto(saude['deficiencia_desc'])
            if nova_desc != saude['deficiencia_desc']:
                modificacoes['saude.deficiencia_desc'] = nova_desc
                print(f"   📝 Deficiência: '{saude['deficiencia_desc']}' -> '{nova_desc}'")
        
        if saude.get('plano_saude'):
            novo_plano = capitalizar_texto(saude['plano_saude'])
            if novo_plano != saude['plano_saude']:
                modificacoes['saude.plano_saude'] = novo_plano
                print(f"   📝 Plano Saúde: '{saude['plano_saude']}' -> '{novo_plano}'")
    
    # 5. CORRIGIR RESPONSÁVEIS
    if 'responsaveis' in aluno and aluno['responsaveis']:
        for idx, resp in enumerate(aluno['responsaveis']):
            if resp.get('nome'):
                novo_nome = capitalizar_nome(resp['nome'])
                if novo_nome != resp['nome']:
                    modificacoes[f'responsaveis.{idx}.nome'] = novo_nome
                    print(f"   📝 Responsável {idx+1}: '{resp['nome'][:30]}...' -> '{novo_nome[:30]}...'")
            
            if resp.get('parentesco'):
                novo_parentesco = capitalizar_texto(resp['parentesco'])
                if novo_parentesco != resp['parentesco']:
                    modificacoes[f'responsaveis.{idx}.parentesco'] = novo_parentesco
                    print(f"   📝 Parentesco: '{resp['parentesco']}' -> '{novo_parentesco}'")
    
    # 6. CORRIGIR TERCEIROS
    if 'terceiros' in aluno and aluno['terceiros']:
        for idx, terc in enumerate(aluno['terceiros']):
            if terc.get('nome'):
                novo_nome = capitalizar_nome(terc['nome'])
                if novo_nome != terc['nome']:
                    modificacoes[f'terceiros.{idx}.nome'] = novo_nome
                    print(f"   📝 Terceiro {idx+1}: '{terc['nome'][:30]}...' -> '{novo_nome[:30]}...'")
    
    # 7. CORRIGIR TRANSPORTE
    if 'transporte' in aluno and aluno['transporte']:
        transporte = aluno['transporte']
        if transporte.get('nome'):
            novo_nome = capitalizar_nome(transporte['nome'])
            if novo_nome != transporte['nome']:
                modificacoes['transporte.nome'] = novo_nome
                print(f"   📝 Transporte: '{transporte['nome']}' -> '{novo_nome}'")
    
    # Aplicar modificações se houver
    if modificacoes:
        modificacoes['data_padronizacao'] = datetime.now()
        result = alunos_collection.update_one(
            {'_id': aluno_id},
            {'$set': modificacoes}
        )
        alunos_modificados += 1
        print(f"   ✅ {len(modificacoes)} campo(s) corrigido(s)")
    else:
        print(f"   ✅ Nenhuma correção necessária")

# ==================== RESUMO FINAL ====================
print("\n" + "=" * 70)
print("📊 RESUMO DA PADRONIZAÇÃO")
print("=" * 70)
print(f"📌 Total de alunos analisados: {total_alunos}")
print(f"✅ Alunos corrigidos: {alunos_modificados}")

# Verificar alguns alunos corrigidos
print("\n📋 AMOSTRA DE ALUNOS:")
amostra = alunos_collection.find({}, {'dados_pessoais.nome': 1, '_id': 0}).limit(10)
for aluno in amostra:
    nome = aluno.get('dados_pessoais', {}).get('nome', 'Sem nome')
    print(f"   - {nome}")

print("\n" + "=" * 70)
print("✅ PADRONIZAÇÃO CONCLUÍDA!")
print("=" * 70)

client.close()