# atualizar_master_perfil.py
from database.mongo import db
from datetime import datetime

def atualizar_master():
    """Atualiza o usuário master para ter perfil 'master'"""
    
    collection = db.get_collection('usuarios')
    
    # Verificar usuário atual
    user = collection.find_one({'usuario': 'master'})
    if user:
        print(f"📋 Usuário master antes: perfil = {user.get('perfil')}")
        
        # Atualizar para perfil 'master'
        result = collection.update_one(
            {'usuario': 'master'},
            {'$set': {
                'perfil': 'master',
                'data_atualizacao': datetime.now()
            }}
        )
        
        if result.modified_count > 0:
            print("✅ Usuário master atualizado para perfil 'master'")
        else:
            print("⚠️ Nenhuma alteração necessária")
        
        # Verificar após atualização
        user_after = collection.find_one({'usuario': 'master'})
        print(f"📋 Usuário master depois: perfil = {user_after.get('perfil')}")
    else:
        print("❌ Usuário master não encontrado")

if __name__ == '__main__':
    atualizar_master()