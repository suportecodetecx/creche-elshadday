from flask import Blueprint, request, jsonify
from database.mongo import get_db
from datetime import datetime

funcionarios_bp = Blueprint('funcionarios', __name__)

# ==================== FUNCIONÁRIOS BÁSICO ====================

# API - Listar funcionários
@funcionarios_bp.route('/api/funcionarios/listar', methods=['GET'])
def listar_funcionarios():
    """Listar todos os funcionários cadastrados"""
    try:
        db = get_db()
        funcionarios = list(db.funcionarios.find({}, {'_id': 0}))
        
        # Garantir que todos os campos existam
        for func in funcionarios:
            if 'cpf' not in func:
                func['cpf'] = ''
            if 'telefone' not in func:
                func['telefone'] = ''
        
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
        cpf = dados.get('cpf', '').strip()
        rgm = dados.get('rgm', '').strip()
        telefone = dados.get('telefone', '').strip()
        unidade = dados.get('unidade', '')
        funcao = dados.get('funcao', '')
        
        if not nome:
            return jsonify({'sucesso': False, 'erro': 'Nome é obrigatório'}), 400
        if not cpf:
            return jsonify({'sucesso': False, 'erro': 'CPF é obrigatório'}), 400
        if not rgm:
            return jsonify({'sucesso': False, 'erro': 'RGM é obrigatório'}), 400
        if not unidade:
            return jsonify({'sucesso': False, 'erro': 'Unidade é obrigatória'}), 400
        if not funcao:
            return jsonify({'sucesso': False, 'erro': 'Função é obrigatória'}), 400
        
        db = get_db()
        
        # Verificar se RGM já existe
        if db.funcionarios.find_one({'rgm': rgm}):
            return jsonify({'sucesso': False, 'erro': 'RGM já cadastrado'}), 400
        
        # Verificar se CPF já existe
        if db.funcionarios.find_one({'cpf': cpf}):
            return jsonify({'sucesso': False, 'erro': 'CPF já cadastrado'}), 400
        
        funcionario = {
            'nome': nome,
            'cpf': cpf,
            'rgm': rgm,
            'telefone': telefone if telefone else '',
            'unidade': unidade,
            'funcao': funcao,
            'beneficio_odonto': False,
            'beneficio_plano_saude': False,
            'beneficio_vale_transporte': False,
            'valor_plano_saude': 0,
            'valor_vale_transporte': 0,
            'dependentes': [],
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
        cpf = dados.get('cpf', '').strip()
        telefone = dados.get('telefone', '').strip()
        unidade = dados.get('unidade', '')
        funcao = dados.get('funcao', '')
        
        if not rgm:
            return jsonify({'sucesso': False, 'erro': 'RGM não informado'}), 400
        if not nome:
            return jsonify({'sucesso': False, 'erro': 'Nome é obrigatório'}), 400
        if not cpf:
            return jsonify({'sucesso': False, 'erro': 'CPF é obrigatório'}), 400
        if not unidade:
            return jsonify({'sucesso': False, 'erro': 'Unidade é obrigatória'}), 400
        if not funcao:
            return jsonify({'sucesso': False, 'erro': 'Função é obrigatória'}), 400
        
        db = get_db()
        
        # Verificar se funcionário existe
        funcionario = db.funcionarios.find_one({'rgm': rgm})
        if not funcionario:
            return jsonify({'sucesso': False, 'erro': 'Funcionário não encontrado'}), 404
        
        # Verificar se CPF já existe para outro funcionário
        cpf_existente = db.funcionarios.find_one({'cpf': cpf, 'rgm': {'$ne': rgm}})
        if cpf_existente:
            return jsonify({'sucesso': False, 'erro': 'CPF já cadastrado para outro funcionário'}), 400
        
        # Atualizar funcionário
        db.funcionarios.update_one(
            {'rgm': rgm},
            {'$set': {
                'nome': nome,
                'cpf': cpf,
                'telefone': telefone if telefone else '',
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
        
        if not db.funcionarios.find_one({'rgm': rgm}):
            return jsonify({'sucesso': False, 'erro': 'Funcionário não encontrado'}), 404
        
        db.funcionarios.delete_one({'rgm': rgm})
        return jsonify({'sucesso': True, 'mensagem': 'Funcionário excluído com sucesso'})
        
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# ==================== BENEFÍCIOS E DEPENDENTES ====================

# API - Listar funcionários com benefícios
@funcionarios_bp.route('/api/funcionarios/beneficios/listar', methods=['GET'])
def listar_beneficios():
    """Listar todos os funcionários com seus benefícios e dependentes"""
    try:
        db = get_db()
        funcionarios = list(db.funcionarios.find({}, {'_id': 0}))
        
        # Garantir que todos os funcionários tenham os campos de benefício
        for func in funcionarios:
            if 'beneficio_odonto' not in func:
                func['beneficio_odonto'] = False
            if 'beneficio_plano_saude' not in func:
                func['beneficio_plano_saude'] = False
            if 'beneficio_vale_transporte' not in func:
                func['beneficio_vale_transporte'] = False
            if 'valor_plano_saude' not in func:
                func['valor_plano_saude'] = 0
            if 'valor_vale_transporte' not in func:
                func['valor_vale_transporte'] = 0
            if 'dependentes' not in func:
                func['dependentes'] = []
            if 'cpf' not in func:
                func['cpf'] = ''
            if 'telefone' not in func:
                func['telefone'] = ''
        
        return jsonify({'sucesso': True, 'funcionarios': funcionarios})
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# API - Atualizar benefício (Odonto, Plano Saúde ou Vale Transporte)
@funcionarios_bp.route('/api/funcionarios/beneficios/atualizar', methods=['POST'])
def atualizar_beneficio():
    """Atualizar benefício de um funcionário (Odonto, Plano de Saúde ou Vale Transporte)"""
    try:
        dados = request.get_json()
        rgm = dados.get('rgm')
        campo = dados.get('campo')  # 'beneficio_odonto', 'beneficio_plano_saude' ou 'beneficio_vale_transporte'
        valor = dados.get('valor')  # True ou False
        
        if not rgm:
            return jsonify({'sucesso': False, 'erro': 'RGM não informado'}), 400
        
        if campo not in ['beneficio_odonto', 'beneficio_plano_saude', 'beneficio_vale_transporte']:
            return jsonify({'sucesso': False, 'erro': 'Campo inválido'}), 400
        
        db = get_db()
        
        result = db.funcionarios.update_one(
            {'rgm': rgm},
            {'$set': {campo: valor}}
        )
        
        if result.matched_count == 0:
            return jsonify({'sucesso': False, 'erro': 'Funcionário não encontrado'}), 404
        
        return jsonify({'sucesso': True})
        
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# API - Atualizar valor do benefício (Plano de Saúde ou Vale Transporte)
@funcionarios_bp.route('/api/funcionarios/beneficios/atualizar-valor', methods=['POST'])
def atualizar_valor_beneficio():
    """Atualizar o valor mensal de um benefício (Plano de Saúde ou Vale Transporte)"""
    try:
        dados = request.get_json()
        rgm = dados.get('rgm')
        campo = dados.get('campo')  # 'valor_plano_saude' ou 'valor_vale_transporte'
        valor = dados.get('valor', 0)
        
        if not rgm:
            return jsonify({'sucesso': False, 'erro': 'RGM não informado'}), 400
        
        if campo not in ['valor_plano_saude', 'valor_vale_transporte']:
            return jsonify({'sucesso': False, 'erro': 'Campo inválido'}), 400
        
        db = get_db()
        
        # Verificar se funcionário existe
        funcionario = db.funcionarios.find_one({'rgm': rgm})
        if not funcionario:
            return jsonify({'sucesso': False, 'erro': 'Funcionário não encontrado'}), 404
        
        # Atualizar o valor
        db.funcionarios.update_one(
            {'rgm': rgm},
            {'$set': {campo: float(valor)}}
        )
        
        return jsonify({'sucesso': True, 'mensagem': 'Valor atualizado com sucesso'})
        
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# API - Atualizar dependentes do Plano de Saúde
@funcionarios_bp.route('/api/funcionarios/dependentes/atualizar', methods=['POST'])
def atualizar_dependentes():
    """Atualizar a lista de dependentes de um funcionário (Plano de Saúde)"""
    try:
        dados = request.get_json()
        rgm = dados.get('rgm')
        dependentes = dados.get('dependentes', [])
        
        if not rgm:
            return jsonify({'sucesso': False, 'erro': 'RGM não informado'}), 400
        
        db = get_db()
        
        # Verificar se o funcionário existe
        funcionario = db.funcionarios.find_one({'rgm': rgm})
        if not funcionario:
            return jsonify({'sucesso': False, 'erro': 'Funcionário não encontrado'}), 404
        
        # Validar estrutura dos dependentes (garantir campos obrigatórios)
        dependentes_validados = []
        for dep in dependentes:
            if dep and isinstance(dep, dict):
                dependentes_validados.append({
                    'nome': dep.get('nome', ''),
                    'parentesco': dep.get('parentesco', '')
                })
        
        # Atualizar dependentes
        result = db.funcionarios.update_one(
            {'rgm': rgm},
            {'$set': {'dependentes': dependentes_validados}}
        )
        
        return jsonify({'sucesso': True, 'mensagem': 'Dependentes salvos com sucesso'})
        
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# API - Buscar funcionário específico com benefícios
@funcionarios_bp.route('/api/funcionarios/beneficios/<rgm>', methods=['GET'])
def buscar_funcionario_beneficios(rgm):
    """Buscar um funcionário específico com seus benefícios e dependentes"""
    try:
        db = get_db()
        funcionario = db.funcionarios.find_one({'rgm': rgm}, {'_id': 0})
        
        if not funcionario:
            return jsonify({'sucesso': False, 'erro': 'Funcionário não encontrado'}), 404
        
        # Garantir campos padrão
        if 'beneficio_odonto' not in funcionario:
            funcionario['beneficio_odonto'] = False
        if 'beneficio_plano_saude' not in funcionario:
            funcionario['beneficio_plano_saude'] = False
        if 'beneficio_vale_transporte' not in funcionario:
            funcionario['beneficio_vale_transporte'] = False
        if 'valor_plano_saude' not in funcionario:
            funcionario['valor_plano_saude'] = 0
        if 'valor_vale_transporte' not in funcionario:
            funcionario['valor_vale_transporte'] = 0
        if 'dependentes' not in funcionario:
            funcionario['dependentes'] = []
        if 'cpf' not in funcionario:
            funcionario['cpf'] = ''
        if 'telefone' not in funcionario:
            funcionario['telefone'] = ''
        
        return jsonify({'sucesso': True, 'funcionario': funcionario})
        
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# API - Estatísticas de benefícios
@funcionarios_bp.route('/api/funcionarios/beneficios/estatisticas', methods=['GET'])
def estatisticas_beneficios():
    """Retorna estatísticas dos benefícios"""
    try:
        db = get_db()
        
        total = db.funcionarios.count_documents({})
        odonto = db.funcionarios.count_documents({'beneficio_odonto': True})
        planoSaude = db.funcionarios.count_documents({'beneficio_plano_saude': True})
        valeTransporte = db.funcionarios.count_documents({'beneficio_vale_transporte': True})
        
        # Total de dependentes
        pipeline = [
            {'$unwind': {'path': '$dependentes', 'preserveNullAndEmptyArrays': True}},
            {'$count': 'total'}
        ]
        result = list(db.funcionarios.aggregate(pipeline))
        totalDependentes = result[0]['total'] if result else 0
        
        return jsonify({
            'sucesso': True,
            'estatisticas': {
                'total_funcionarios': total,
                'beneficio_odonto': odonto,
                'beneficio_plano_saude': planoSaude,
                'beneficio_vale_transporte': valeTransporte,
                'total_dependentes': totalDependentes
            }
        })
        
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# API - Atualizar CPF
@funcionarios_bp.route('/api/funcionarios/atualizar-cpf', methods=['POST'])
def atualizar_cpf():
    """Atualizar CPF de um funcionário"""
    try:
        dados = request.get_json()
        rgm = dados.get('rgm')
        cpf = dados.get('cpf', '').strip()
        
        if not rgm:
            return jsonify({'sucesso': False, 'erro': 'RGM não informado'}), 400
        if not cpf:
            return jsonify({'sucesso': False, 'erro': 'CPF é obrigatório'}), 400
        
        db = get_db()
        
        # Verificar se CPF já existe para outro funcionário
        cpf_existente = db.funcionarios.find_one({'cpf': cpf, 'rgm': {'$ne': rgm}})
        if cpf_existente:
            return jsonify({'sucesso': False, 'erro': 'CPF já cadastrado para outro funcionário'}), 400
        
        result = db.funcionarios.update_one(
            {'rgm': rgm},
            {'$set': {'cpf': cpf}}
        )
        
        if result.matched_count == 0:
            return jsonify({'sucesso': False, 'erro': 'Funcionário não encontrado'}), 404
        
        return jsonify({'sucesso': True, 'mensagem': 'CPF atualizado com sucesso'})
        
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500