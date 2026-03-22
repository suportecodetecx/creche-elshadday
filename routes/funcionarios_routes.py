from flask import Blueprint, request, jsonify
from database.mongo import get_db
from datetime import datetime

funcionarios_bp = Blueprint('funcionarios', __name__)

# API - Listar funcionários
@funcionarios_bp.route('/api/funcionarios/listar', methods=['GET'])
def listar_funcionarios():
    """Listar todos os funcionários cadastrados"""
    try:
        db = get_db()
        funcionarios = list(db.funcionarios.find({}, {'_id': 0}))
        return jsonify({'sucesso': True, 'funcionarios': funcionarios})
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

# API - Cadastrar funcionário
@funcionarios_bp.route('/api/funcionarios/cadastrar', methods=['POST'])
def cadastrar_funcionario():
    """Cadastrar um novo funcionário"""
    try:
        dados = request.get_json()
        
        nome = dados.get('nome', '').strip()
        rgm = dados.get('rgm', '').strip()
        telefone = dados.get('telefone', '').strip()
        unidade = dados.get('unidade', '')
        funcao = dados.get('funcao', '')
        
        # Validações
        if not nome or not rgm or not unidade or not funcao:
            return jsonify({'sucesso': False, 'erro': 'Todos os campos são obrigatórios'}), 400
        
        if not telefone:
            return jsonify({'sucesso': False, 'erro': 'Telefone é obrigatório'}), 400
        
        db = get_db()
        
        # Verificar se RGM já existe
        if db.funcionarios.find_one({'rgm': rgm}):
            return jsonify({'sucesso': False, 'erro': 'RGM já cadastrado'}), 400
        
        # Inserir funcionário com telefone
        funcionario = {
            'nome': nome,
            'rgm': rgm,
            'telefone': telefone,
            'unidade': unidade,
            'funcao': funcao,
            'data_cadastro': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        db.funcionarios.insert_one(funcionario)
        
        return jsonify({'sucesso': True, 'mensagem': 'Funcionário cadastrado com sucesso'})
        
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

# API - Atualizar funcionário
@funcionarios_bp.route('/api/funcionarios/atualizar', methods=['POST'])
def atualizar_funcionario():
    """Atualizar um funcionário existente"""
    try:
        dados = request.get_json()
        
        rgm = dados.get('rgm', '').strip()
        nome = dados.get('nome', '').strip()
        telefone = dados.get('telefone', '').strip()
        unidade = dados.get('unidade', '')
        funcao = dados.get('funcao', '')
        
        # Validações
        if not rgm:
            return jsonify({'sucesso': False, 'erro': 'RGM não informado'}), 400
        
        if not nome or not unidade or not funcao:
            return jsonify({'sucesso': False, 'erro': 'Todos os campos são obrigatórios'}), 400
        
        if not telefone:
            return jsonify({'sucesso': False, 'erro': 'Telefone é obrigatório'}), 400
        
        db = get_db()
        
        # Verificar se funcionário existe
        funcionario = db.funcionarios.find_one({'rgm': rgm})
        if not funcionario:
            return jsonify({'sucesso': False, 'erro': 'Funcionário não encontrado'}), 404
        
        # Atualizar funcionário
        db.funcionarios.update_one(
            {'rgm': rgm},
            {'$set': {
                'nome': nome,
                'telefone': telefone,
                'unidade': unidade,
                'funcao': funcao,
                'data_atualizacao': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }}
        )
        
        return jsonify({'sucesso': True, 'mensagem': 'Funcionário atualizado com sucesso'})
        
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

# API - Excluir funcionário
@funcionarios_bp.route('/api/funcionarios/excluir', methods=['POST'])
def excluir_funcionario():
    """Excluir um funcionário"""
    try:
        dados = request.get_json()
        rgm = dados.get('rgm', '')
        
        if not rgm:
            return jsonify({'sucesso': False, 'erro': 'RGM não informado'}), 400
        
        db = get_db()
        
        # Verificar se funcionário existe
        if not db.funcionarios.find_one({'rgm': rgm}):
            return jsonify({'sucesso': False, 'erro': 'Funcionário não encontrado'}), 404
        
        # Excluir funcionário
        db.funcionarios.delete_one({'rgm': rgm})
        
        return jsonify({'sucesso': True, 'mensagem': 'Funcionário excluído com sucesso'})
        
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500