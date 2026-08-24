# ============================================================
# ⚠️ FUNCIONALIDADE DE DOCUMENTOS REMOVIDA
# ============================================================
# Este arquivo foi mantido apenas para evitar erros de importação.
# Todas as rotas de documentos foram desativadas.
# ============================================================

from flask import Blueprint, jsonify

# Cria o blueprint vazio (apenas para não quebrar o app.py)
documentos_bp = Blueprint('documentos', __name__, url_prefix='/documentos')


# ============================================================
# ROTA INFORMATIVA (OPCIONAL)
# ============================================================
@documentos_bp.route('/')
def documentos_index():
    """Retorna mensagem informando que a funcionalidade foi removida"""
    return jsonify({
        'sucesso': False,
        'mensagem': 'Funcionalidade de documentos removida',
        'detalhe': 'O sistema agora trabalha apenas com fotos e dados cadastrais'
    }), 410  # 410 Gone


@documentos_bp.route('/gestao')
def gestao_documentos():
    """Redireciona ou retorna erro informativo"""
    return jsonify({
        'sucesso': False,
        'mensagem': 'Página de gestão de documentos removida',
        'redirecionar': '/'
    }), 410


# ============================================================
# ROTAS API DESATIVADAS
# ============================================================
@documentos_bp.route('/api/listar', methods=['GET'])
def listar_documentos():
    return jsonify({
        'sucesso': False,
        'mensagem': 'API de documentos desativada'
    }), 410


@documentos_bp.route('/api/upload', methods=['POST'])
def upload_documento():
    return jsonify({
        'sucesso': False,
        'mensagem': 'Upload de documentos desativado'
    }), 410


@documentos_bp.route('/api/atualizar', methods=['POST'])
def atualizar_documento():
    return jsonify({
        'sucesso': False,
        'mensagem': 'Atualização de documentos desativada'
    }), 410


@documentos_bp.route('/api/download/<documento_id>', methods=['GET'])
def download_documento(documento_id):
    return jsonify({
        'sucesso': False,
        'mensagem': 'Download de documentos desativado'
    }), 410


@documentos_bp.route('/api/visualizar/<documento_id>', methods=['GET'])
def visualizar_documento(documento_id):
    return jsonify({
        'sucesso': False,
        'mensagem': 'Visualização de documentos desativada'
    }), 410


@documentos_bp.route('/api/excluir/<documento_id>', methods=['DELETE'])
def excluir_documento(documento_id):
    return jsonify({
        'sucesso': False,
        'mensagem': 'Exclusão de documentos desativada'
    }), 410


@documentos_bp.route('/api/estatisticas', methods=['GET'])
def estatisticas():
    return jsonify({
        'sucesso': False,
        'mensagem': 'Estatísticas de documentos desativadas'
    }), 410


# ============================================================
# HANDLER PARA QUALQUER OUTRA ROTA DE DOCUMENTOS
# ============================================================
@documentos_bp.route('/<path:path>')
def catch_all(path):
    """Captura qualquer outra rota de documentos e retorna erro"""
    return jsonify({
        'sucesso': False,
        'mensagem': f'Rota /documentos/{path} não existe ou foi desativada',
        'dica': 'O sistema agora trabalha apenas com fotos e dados cadastrais'
    }), 404