from database.mongo import db
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

print("🔧 RESETANDO CONTADOR DE INSCRIÇÃO")
print("=" * 40)

# Conecta ao banco
uri = os.getenv('MONGO_URI')
client = MongoClient(uri)
db = client['creche_el_shadday']

# Mostra valor atual
contador_atual = db.contadores.find_one({'nome': 'num_inscricao'})
print(f"📊 Valor atual: {contador_atual['valor'] if contador_atual else 'Não encontrado'}")

# Reseta para 1
resultado = db.contadores.update_one(
    {'nome': 'num_inscricao'},
    {'$set': {'valor': 0}},
    upsert=True
)

# Verifica se deu certo
contador_novo = db.contadores.find_one({'nome': 'num_inscricao'})
print(f"✅ Novo valor: {contador_novo['valor']}")

print("=" * 40)
print("🎉 Contador resetado com sucesso!")
print("🚀 Reinicie o servidor e teste o cadastro")