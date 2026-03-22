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
        # Usuário Master (Administrador)
        {
            'usuario': 'master',
            'email': 'master@creche.com',
            'senha_plana': 'code@@',
            'nome': 'Administrador Master',
            'perfil': 'admin',
            'unidade': 'Todas as Unidades',
            'status': 'ativo',
            'ativo': True
        },
        # Usuário Admin (alternativo)
        {
            'usuario': 'admin',
            'email': 'admin@creche.com',
            'senha_plana': 'admin123',
            'nome': 'Administrador',
            'perfil': 'admin',
            'unidade': 'Todas as Unidades',
            'status': 'ativo',
            'ativo': True
        },
        # Usuário Pedagógico Geral
        {
            'usuario': 'pedagogico',
            'email': 'pedagogico@creche.com',
            'senha_plana': 'pedagogo123',
            'nome': 'Usuário Pedagógico',
            'perfil': 'pedagogico',
            'unidade': '',
            'status': 'ativo',
            'ativo': True
        },
        # Usuário Pedagógico CEIC
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
        # Usuário Pedagógico CEIM
        {
            'usuario': 'pedagogaceim',
            'email': 'pedagogaceim@creche.com',
            'senha_plana': '1234@@',
            'nome': 'Usuário Pedagógico CEIM',
            'perfil': 'pedagogico',
            'unidade': 'CEIM Prof. Egberto Malta Moreira',
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
            collection.update_one(
                {'usuario': user_data['usuario']},
                {'$set': dados_usuario}
            )
            print(f"✅ Usuário {user_data['usuario']} ATUALIZADO | Senha: {user_data['senha_plana']}")
        else:
            # Criar novo usuário
            dados_usuario['usuario'] = user_data['usuario']
            dados_usuario['data_criacao'] = datetime.now()
            collection.insert_one(dados_usuario)
            print(f"✅ Usuário {user_data['usuario']} CRIADO | Senha: {user_data['senha_plana']}")
    
    print("\n" + "="*60)
    print("🔑 CREDENCIAIS DOS USUÁRIOS:")
    print("-"*60)
    print("👨‍💼 ADMINISTRADORES:")
    print("   Usuário: master | Senha: code@@ | Perfil: admin")
    print("   Usuário: admin  | Senha: admin123 | Perfil: admin")
    print("\n👩‍🏫 PEDAGÓGICOS:")
    print("   Usuário: pedagogico    | Senha: pedagogo123 | Unidade: Todas")
    print("   Usuário: pedagogaceic  | Senha: 1234@@      | Unidade: CEIC El Shadday")
    print("   Usuário: pedagogaceim  | Senha: 1234@@      | Unidade: CEIM Prof. Egberto Malta Moreira")
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
    
    # Contar total de usuários
    total = collection.count_documents({})
    print(f"\n📊 Total de usuários no sistema: {total}")

if __name__ == '__main__':
    criar_usuarios()