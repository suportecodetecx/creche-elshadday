# criar_usuarios.py
from database.mongo import db
import bcrypt
from datetime import datetime

def criar_usuarios():
    """Cria/atualiza os usuários no sistema"""
    
    print("🚀 CRIANDO/ATUALIZANDO USUÁRIOS...")
    print("="*60)
    
    # Acessar coleção
    collection = db.get_collection('usuarios')
    
    # Lista de usuários com as senhas desejadas
    usuarios = [
        {
            'usuario': 'pedagogaceic',
            'email': 'pedagogaceic@creche.com',
            'senha_plana': '1234@@',
            'nome': 'Usuário Pedagógico CEIC',
            'perfil': 'pedagogico',
            'unidade': 'CEIC El Shadday',
            'status': 'ativo',
            'ativo': True
        },
        {
            'usuario': 'pedagogaceim',
            'email': 'pedagogaceim@creche.com',
            'senha_plana': '1234@@',
            'nome': 'Usuário Pedagógico CEIM',
            'perfil': 'pedagogico',
            'unidade': 'CEIM Prof. Egberto Malta Moreira',
            'status': 'ativo',
            'ativo': True
        },
        {
            'usuario': 'master',
            'email': 'master@creche.com',
            'senha_plana': 'code@@',
            'nome': 'Administrador Master',
            'perfil': 'admin',
            'unidade': 'Todas as Unidades',
            'status': 'ativo',
            'ativo': True
        }
    ]
    
    for user_data in usuarios:
        # Gerar hash da senha
        senha_hash = bcrypt.hashpw(user_data['senha_plana'].encode('utf-8'), bcrypt.gensalt())
        
        # Dados para atualizar/criar
        dados_usuario = {
            'email': user_data['email'],
            'senha': senha_hash,
            'nome': user_data['nome'],
            'perfil': user_data['perfil'],
            'unidade': user_data['unidade'],
            'status': user_data['status'],
            'ativo': user_data['ativo'],
            'data_atualizacao': datetime.now()
        }
        
        # Verificar se usuário já existe
        existing = collection.find_one({'usuario': user_data['usuario']})
        
        if existing:
            # Atualizar usuário existente
            result = collection.update_one(
                {'usuario': user_data['usuario']},
                {'$set': dados_usuario}
            )
            print(f"✅ Usuário {user_data['usuario']} ATUALIZADO | Senha: {user_data['senha_plana']} | Unidade: {user_data['unidade']}")
        else:
            # Criar novo usuário
            dados_usuario['usuario'] = user_data['usuario']
            dados_usuario['data_criacao'] = datetime.now()
            collection.insert_one(dados_usuario)
            print(f"✅ Usuário {user_data['usuario']} CRIADO | Senha: {user_data['senha_plana']} | Unidade: {user_data['unidade']}")
    
    print("\n" + "="*60)
    print("🔑 CREDENCIAIS DOS USUÁRIOS:")
    print("-"*60)
    print("Usuário: pedagogaceic | Senha: 1234@@ | Unidade: CEIC El Shadday")
    print("Usuário: pedagogaceim | Senha: 1234@@ | Unidade: CEIM Prof. Egberto Malta Moreira")
    print("Usuário: master | Senha: code@@| Perfil: Administrador Master")
    print("="*60)
    
    # Testar as senhas após criação
    print("\n🔍 TESTANDO SENHAS:")
    print("-"*60)
    for user_data in usuarios:
        user = collection.find_one({'usuario': user_data['usuario']})
        if user:
            senha_hash = user.get('senha')
            senha_teste = user_data['senha_plana'].encode('utf-8')
            
            if bcrypt.checkpw(senha_teste, senha_hash):
                print(f"✅ {user_data['usuario']}: senha '{user_data['senha_plana']}' OK")
            else:
                print(f"❌ {user_data['usuario']}: senha '{user_data['senha_plana']}' FALHOU!")
        else:
            print(f"❌ {user_data['usuario']}: usuário não encontrado!")

if __name__ == '__main__':
    criar_usuarios()