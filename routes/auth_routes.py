# routes/auth_routes.py
from flask import Blueprint, request, jsonify, session
from bson.objectid import ObjectId
from datetime import datetime
from models.usuario import Usuario
from database.mongo import db as mongo_db

auth_bp = Blueprint('auth', __name__)
usuario_model = Usuario()


@auth_bp.route('/api/login', methods=['POST'])
def login():
    """Endpoint para login de usuários"""
    try:
        dados = request.get_json()
        email = dados.get('usuario')  # Pode ser email ou usuário
        senha = dados.get('senha')
        
        if not email or not senha:
            return jsonify({
                'sucesso': False, 
                'mensagem': 'Usuário e senha são obrigatórios'
            }), 400
        
        # Buscar usuário por email
        user = mongo_db.get_collection('usuarios').find_one({
            '$or': [
                {'email': email},
                {'usuario': email}
            ]
        })
        
        if not user:
            return jsonify({
                'sucesso': False, 
                'mensagem': 'Usuário não encontrado'
            }), 401
        
        # Verificar senha usando bcrypt
        import bcrypt
        try:
            if not bcrypt.checkpw(senha.encode('utf-8'), user.get('senha', b'')):
                return jsonify({
                    'sucesso': False, 
                    'mensagem': 'Senha incorreta'
                }), 401
        except Exception as e:
            # Se a senha estiver em texto puro (para testes)
            if user.get('senha') != senha:
                return jsonify({
                    'sucesso': False, 
                    'mensagem': 'Senha incorreta'
                }), 401
        
        # Verificar se usuário está ativo
        if user.get('status') == 'inativo':
            return jsonify({
                'sucesso': False, 
                'mensagem': 'Usuário desativado. Contate o administrador.'
            }), 401
        
        # Criar sessão com dados do usuário
        session['user_id'] = str(user['_id'])
        session['user_email'] = user.get('email')
        session['user_name'] = user.get('nome', user.get('email'))
        session['user_profile'] = user.get('perfil', 'pedagogico')
        session['user_unidade'] = user.get('unidade', '')  # Adiciona a unidade na sessão
        session.permanent = True
        
        return jsonify({
            'sucesso': True,
            'mensagem': 'Login realizado com sucesso',
            'usuario': {
                'id': str(user['_id']),
                'nome': user.get('nome', user.get('email')),
                'email': user.get('email'),
                'perfil': user.get('perfil', 'pedagogico'),
                'unidade': user.get('unidade', '')  # Retorna a unidade
            }
        })
    except Exception as e:
        print(f'Erro no login: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'sucesso': False, 
            'mensagem': f'Erro ao realizar login: {str(e)}'
        }), 500


@auth_bp.route('/api/trocar-senha', methods=['POST'])
def trocar_senha():
    """Endpoint para trocar a senha do usuário logado"""
    try:
        # Verificar se usuário está logado
        if not session.get('user_id'):
            return jsonify({'sucesso': False, 'mensagem': 'Usuário não autenticado'}), 401
        
        dados = request.get_json()
        senha_atual = dados.get('senha_atual')
        nova_senha = dados.get('nova_senha')
        
        if not senha_atual or not nova_senha:
            return jsonify({'sucesso': False, 'mensagem': 'Senha atual e nova senha são obrigatórias'}), 400
        
        if len(nova_senha) < 6:
            return jsonify({'sucesso': False, 'mensagem': 'A nova senha deve ter pelo menos 6 caracteres'}), 400
        
        # Buscar usuário no banco
        import bcrypt
        user = mongo_db.get_collection('usuarios').find_one({'_id': ObjectId(session['user_id'])})
        
        if not user:
            session.clear()
            return jsonify({'sucesso': False, 'mensagem': 'Usuário não encontrado'}), 404
        
        # Verificar senha atual
        try:
            if not bcrypt.checkpw(senha_atual.encode('utf-8'), user.get('senha', b'')):
                return jsonify({'sucesso': False, 'mensagem': 'Senha atual incorreta'}), 401
        except Exception as e:
            # Se a senha estiver em texto puro (para testes)
            if user.get('senha') != senha_atual:
                return jsonify({'sucesso': False, 'mensagem': 'Senha atual incorreta'}), 401
        
        # Gerar hash da nova senha
        nova_senha_hash = bcrypt.hashpw(nova_senha.encode('utf-8'), bcrypt.gensalt())
        
        # Atualizar senha
        mongo_db.get_collection('usuarios').update_one(
            {'_id': ObjectId(session['user_id'])},
            {'$set': {
                'senha': nova_senha_hash,
                'data_atualizacao': datetime.now(),
                'senha_alterada_em': datetime.now()
            }}
        )
        
        return jsonify({
            'sucesso': True, 
            'mensagem': 'Senha alterada com sucesso!'
        })
    except Exception as e:
        print(f'Erro ao trocar senha: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'mensagem': f'Erro ao alterar senha: {str(e)}'}), 500


@auth_bp.route('/api/logout', methods=['POST'])
def logout():
    """Endpoint para logout"""
    try:
        session.clear()
        return jsonify({
            'sucesso': True, 
            'mensagem': 'Logout realizado com sucesso'
        })
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@auth_bp.route('/api/session', methods=['GET'])
def verificar_sessao():
    """Verifica se o usuário está logado"""
    try:
        if session.get('user_id'):
            return jsonify({
                'sucesso': True,
                'logado': True,
                'usuario': {
                    'id': session.get('user_id'),
                    'nome': session.get('user_name'),
                    'email': session.get('user_email'),
                    'perfil': session.get('user_profile'),
                    'unidade': session.get('user_unidade', '')
                }
            })
        else:
            return jsonify({'sucesso': True, 'logado': False})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@auth_bp.route('/api/criar-usuario-teste', methods=['POST'])
def criar_usuario_teste():
    """Endpoint para criar usuário de teste usando o modelo Usuario"""
    try:
        usuarios_criados = []
        
        # Criar usuário admin
        try:
            usuario_model.criar_usuario(
                email='admin@creche.com',
                senha='admin123',
                perfil='admin',
                nome='Administrador do Sistema'
            )
            usuarios_criados.append({
                'usuario': 'admin@creche.com',
                'senha': 'admin123',
                'perfil': 'admin'
            })
            print("✅ Usuário admin criado")
        except Exception as e:
            if 'E-mail já cadastrado' in str(e):
                print("ℹ️ Usuário admin já existe")
            else:
                print(f"⚠️ Erro ao criar admin: {e}")
        
        # Criar usuário pedagógico
        try:
            usuario_model.criar_usuario(
                email='pedagogico@creche.com',
                senha='pedagogico123',
                perfil='pedagogico',
                nome='Usuário Pedagógico'
            )
            usuarios_criados.append({
                'usuario': 'pedagogico@creche.com',
                'senha': 'pedagogico123',
                'perfil': 'pedagogico'
            })
            print("✅ Usuário pedagógico criado")
        except Exception as e:
            if 'E-mail já cadastrado' in str(e):
                print("ℹ️ Usuário pedagógico já existe")
            else:
                print(f"⚠️ Erro ao criar pedagógico: {e}")
        
        if usuarios_criados:
            return jsonify({
                'sucesso': True,
                'mensagem': f'{len(usuarios_criados)} usuário(s) criado(s) com sucesso!',
                'usuarios': usuarios_criados
            })
        else:
            # Listar usuários existentes
            usuarios = usuario_model.listar_usuarios()
            return jsonify({
                'sucesso': True,
                'mensagem': 'Usuários já existem no sistema',
                'usuarios': [
                    {'email': u.get('email'), 'perfil': u.get('perfil')} 
                    for u in usuarios if u.get('status') == 'ativo'
                ]
            })
    except Exception as e:
        print(f'Erro ao criar usuário teste: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'sucesso': False, 
            'erro': str(e)
        }), 500


@auth_bp.route('/api/usuarios', methods=['GET'])
def listar_usuarios():
    """Lista todos os usuários (apenas admin)"""
    try:
        if session.get('user_profile') != 'admin':
            return jsonify({'erro': 'Acesso negado'}), 403
        
        usuarios = usuario_model.listar_usuarios()
        return jsonify({'sucesso': True, 'usuarios': usuarios})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@auth_bp.route('/api/usuarios', methods=['POST'])
def criar_usuario():
    """Cria um novo usuário (apenas admin)"""
    try:
        if session.get('user_profile') != 'admin':
            return jsonify({'erro': 'Acesso negado'}), 403
        
        dados = request.get_json()
        email = dados.get('email')
        senha = dados.get('senha')
        perfil = dados.get('perfil')
        nome = dados.get('nome')
        unidade = dados.get('unidade', '')  # Adiciona campo unidade
        
        if not all([email, senha, perfil, nome]):
            return jsonify({'erro': 'Todos os campos são obrigatórios'}), 400
        
        # Criar usuário com unidade
        from database.mongo import db
        import bcrypt
        
        # Verificar se já existe
        if db.get_collection('usuarios').find_one({'email': email}):
            return jsonify({'erro': 'E-mail já cadastrado'}), 400
        
        # Criptografar senha
        senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt())
        
        novo_usuario = {
            'email': email,
            'usuario': email.split('@')[0],
            'senha': senha_hash,
            'nome': nome,
            'perfil': perfil,
            'unidade': unidade,
            'status': 'ativo',
            'ativo': True,
            'data_criacao': datetime.now(),
            'data_atualizacao': datetime.now()
        }
        
        result = db.get_collection('usuarios').insert_one(novo_usuario)
        
        return jsonify({
            'sucesso': True, 
            'mensagem': 'Usuário criado com sucesso',
            'id': str(result.inserted_id)
        })
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@auth_bp.route('/api/usuarios/<user_id>', methods=['PUT'])
def atualizar_usuario(user_id):
    """Atualiza um usuário existente (apenas admin)"""
    try:
        if session.get('user_profile') != 'admin':
            return jsonify({'erro': 'Acesso negado'}), 403
        
        dados = request.get_json()
        
        # Se tiver senha, faz o hash
        if 'senha' in dados and dados['senha']:
            import bcrypt
            dados['senha'] = bcrypt.hashpw(dados['senha'].encode('utf-8'), bcrypt.gensalt())
        
        dados['data_atualizacao'] = datetime.now()
        
        result = mongo_db.get_collection('usuarios').update_one(
            {'_id': ObjectId(user_id)},
            {'$set': dados}
        )
        
        if result.modified_count == 0:
            return jsonify({'erro': 'Usuário não encontrado ou nenhuma alteração'}), 404
        
        return jsonify({
            'sucesso': True, 
            'mensagem': 'Usuário atualizado'
        })
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@auth_bp.route('/api/usuarios/<user_id>', methods=['DELETE'])
def deletar_usuario(user_id):
    """Desativa um usuário (apenas admin)"""
    try:
        if session.get('user_profile') != 'admin':
            return jsonify({'erro': 'Acesso negado'}), 403
        
        result = mongo_db.get_collection('usuarios').update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'status': 'inativo', 'ativo': False, 'data_atualizacao': datetime.now()}}
        )
        
        if result.modified_count == 0:
            return jsonify({'erro': 'Usuário não encontrado'}), 404
        
        return jsonify({
            'sucesso': True, 
            'mensagem': 'Usuário desativado'
        })
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@auth_bp.route('/api/me', methods=['GET'])
def usuario_atual():
    """Retorna os dados do usuário logado atualmente"""
    try:
        if not session.get('user_id'):
            return jsonify({'sucesso': False, 'mensagem': 'Não autenticado'}), 401
        
        user = mongo_db.get_collection('usuarios').find_one({'_id': ObjectId(session['user_id'])})
        
        if not user:
            session.clear()
            return jsonify({'sucesso': False, 'mensagem': 'Usuário não encontrado'}), 404
        
        return jsonify({
            'sucesso': True,
            'usuario': {
                'id': str(user['_id']),
                'nome': user.get('nome'),
                'email': user.get('email'),
                'usuario': user.get('usuario'),
                'perfil': user.get('perfil'),
                'unidade': user.get('unidade', '')
            }
        })
    except Exception as e:
        return jsonify({'erro': str(e)}), 500