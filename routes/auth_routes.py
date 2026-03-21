# routes/auth_routes.py
from flask import Blueprint, request, jsonify, session
from models.usuario import Usuario
from bson.objectid import ObjectId

auth_bp = Blueprint('auth', __name__)
usuario_model = Usuario()

@auth_bp.route('/api/usuarios', methods=['GET'])
def listar_usuarios():
    try:
        if session.get('user_profile') != 'admin':
            return jsonify({'erro': 'Acesso negado'}), 403
        
        usuarios = usuario_model.listar_usuarios()
        return jsonify({'sucesso': True, 'usuarios': usuarios})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@auth_bp.route('/api/usuarios', methods=['POST'])
def criar_usuario():
    try:
        if session.get('user_profile') != 'admin':
            return jsonify({'erro': 'Acesso negado'}), 403
        
        dados = request.get_json()
        email = dados.get('email')
        senha = dados.get('senha')
        perfil = dados.get('perfil')
        nome = dados.get('nome')
        
        if not all([email, senha, perfil, nome]):
            return jsonify({'erro': 'Todos os campos são obrigatórios'}), 400
        
        usuario_model.criar_usuario(email, senha, perfil, nome)
        return jsonify({'sucesso': True, 'mensagem': 'Usuário criado com sucesso'})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@auth_bp.route('/api/usuarios/<user_id>', methods=['PUT'])
def atualizar_usuario(user_id):
    try:
        if session.get('user_profile') != 'admin':
            return jsonify({'erro': 'Acesso negado'}), 403
        
        dados = request.get_json()
        usuario_model.atualizar_usuario(user_id, dados)
        return jsonify({'sucesso': True, 'mensagem': 'Usuário atualizado'})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@auth_bp.route('/api/usuarios/<user_id>', methods=['DELETE'])
def deletar_usuario(user_id):
    try:
        if session.get('user_profile') != 'admin':
            return jsonify({'erro': 'Acesso negado'}), 403
        
        usuario_model.desativar_usuario(user_id)
        return jsonify({'sucesso': True, 'mensagem': 'Usuário desativado'})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500