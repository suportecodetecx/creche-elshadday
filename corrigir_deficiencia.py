# corrigir_deficiencia.py
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

print("🔌 Conectando ao MongoDB...")

# Conectar ao MongoDB
mongo_uri = os.getenv('MONGO_URI', 'mongodb+srv://cadastro_db_user:0Vvl27ZcrYqaD8Kj@cluster0.6mtltjd.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
db_name = os.getenv('DB_NAME', 'creche_el_shadday')

client = MongoClient(mongo_uri, tls=True, tlsAllowInvalidCertificates=True)
db = client[db_name]
alunos = db['alunos']

# Corrigir o aluno 010-2026
print("\n📝 Corrigindo aluno 010-2026...")

resultado = alunos.update_one(
    { "num_inscricao": "010-2026" },
    { 
        "$set": {
            "saude.deficiencia": True,
            "saude.deficiencia_desc": "TDH"
        }
    }
)

if resultado.modified_count > 0:
    print("✅ Deficiência corrigida com sucesso!")
    print("   - deficiencia: True")
    print("   - deficiencia_desc: TDH")
elif resultado.matched_count > 0:
    print("ℹ️ Aluno encontrado mas já estava correto")
else:
    print("❌ Aluno não encontrado")

# Verificar se funcionou
aluno = alunos.find_one({"num_inscricao": "010-2026"})
if aluno:
    print("\n📋 Dados atualizados:")
    print(f"   Deficiência: {aluno.get('saude', {}).get('deficiencia')}")
    print(f"   Descrição: {aluno.get('saude', {}).get('deficiencia_desc')}")

print("\n✅ Script finalizado!")