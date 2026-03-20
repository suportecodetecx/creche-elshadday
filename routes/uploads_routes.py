from flask import Blueprint, send_from_directory, abort
import os

uploads_bp = Blueprint('uploads', __name__)

@uploads_bp.route('/uploads/<path:pasta>/<path:filename>')
def get_upload(pasta, filename):
    """Serve arquivos da pasta uploads"""
    try:
        # Verifica se a pasta é permitida
        pastas_permitidas = ['alunos', 'pais', 'terceiros', 'documentos']
        if pasta not in pastas_permitidas:
            abort(404)
        
        # Caminho completo
        upload_folder = os.path.join('uploads', pasta)
        
        # Retorna o arquivo
        return send_from_directory(upload_folder, filename)
    except Exception as e:
        abort(404)