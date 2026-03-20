from database.mongo import db

def iniciar_contador():
    try:
        # Verifica se o contador existe
        contador = db.get_collection('contadores').find_one({'nome': 'num_inscricao'})
        
        if not contador:
            # Cria o contador com valor inicial
            db.get_collection('contadores').insert_one({
                'nome': 'num_inscricao',
                'valor': 17  # Começa do 17 porque você já tem 16 alunos
            })
            print("✅ Contador criado com valor 17")
        else:
            print(f"✅ Contador já existe: {contador['valor']}")
        
        # Lista todos os contadores
        contadores = list(db.get_collection('contadores').find())
        print(f"📊 Contadores: {contadores}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == '__main__':
    iniciar_contador()