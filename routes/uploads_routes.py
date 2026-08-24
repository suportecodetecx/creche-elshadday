from flask import Blueprint, send_from_directory, abort, jsonify, request
from database.mongo import db
from gridfs import GridFS
from bson import ObjectId
from datetime import datetime
import os
import logging

uploads_bp = Blueprint('uploads', __name__)
logger = logging.getLogger(__name__)

# ============================================================
# ROTA PARA ARQUIVOS ESTÁTICOS (LEGADO)
# ============================================================

@uploads_bp.route('/uploads/<path:pasta>/<path:filename>')
def get_upload(pasta, filename):
    """Serve arquivos da pasta uploads (apenas imagens)"""
    try:
        # 🔥 REMOVIDA pasta 'documentos' - apenas fotos
        pastas_permitidas = ['alunos', 'pais', 'terceiros']
        if pasta not in pastas_permitidas:
            logger.warning(f"Pasta não permitida: {pasta}")
            abort(404)
        
        # Caminho completo
        upload_folder = os.path.join('uploads', pasta)
        
        # Verifica se é imagem (extensões permitidas)
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if ext not in ['jpg', 'jpeg', 'png', 'gif']:
            logger.warning(f"Arquivo não é imagem: {filename}")
            abort(404)
        
        # Retorna o arquivo
        return send_from_directory(upload_folder, filename)
    except Exception as e:
        logger.error(f"Erro ao servir arquivo: {e}")
        abort(404)


# ============================================================
# API PARA UPLOAD DE FOTOS (GRIDFS)
# ============================================================

@uploads_bp.route('/api/upload-foto', methods=['POST'])
def upload_foto():
    """Upload de foto para GridFS (apenas imagens)"""
    try:
        print("\n📤 UPLOAD DE FOTO")
        
        if 'arquivo' not in request.files:
            return jsonify({'sucesso': False, 'erro': 'Nenhum arquivo enviado'}), 400
        
        arquivo = request.files['arquivo']
        campo = request.form.get('campo', 'desconhecido')
        
        if not arquivo or not arquivo.filename:
            return jsonify({'sucesso': False, 'erro': 'Arquivo inválido'}), 400
        
        # 🔥 VALIDAÇÃO: SÓ ACEITA IMAGENS
        if not arquivo.content_type.startswith('image/'):
            return jsonify({
                'sucesso': False, 
                'erro': 'Apenas imagens são permitidas (JPG, PNG, GIF, etc)'
            }), 400
        
        # Verifica tamanho (máx 5MB para fotos)
        arquivo.seek(0, os.SEEK_END)
        tamanho = arquivo.tell()
        arquivo.seek(0)
        
        if tamanho > 5 * 1024 * 1024:
            return jsonify({
                'sucesso': False, 
                'erro': 'Imagem muito grande (máx 5MB)'
            }), 400
        
        # Upload para GridFS
        fs = GridFS(db.db)
        file_id = fs.put(
            arquivo.read(),
            filename=arquivo.filename,
            content_type=arquivo.content_type,
            metadata={
                'campo': campo,
                'tipo': 'foto',
                'original_name': arquivo.filename,
                'upload_date': datetime.now()
            }
        )
        
        print(f"   ✅ Foto salva: {campo} - ID: {file_id}")
        
        return jsonify({
            'sucesso': True,
            'file_id': str(file_id),
            'campo': campo,
            'mensagem': 'Foto salva com sucesso!'
        })
        
    except Exception as e:
        print(f"❌ Erro no upload: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# ============================================================
# API PARA VISUALIZAR FOTOS (GRIDFS)
# ============================================================

@uploads_bp.route('/api/foto/<file_id>', methods=['GET'])
def get_foto(file_id):
    """Busca foto do GridFS pelo ID"""
    try:
        from flask import send_file
        from io import BytesIO
        
        fs = GridFS(db.db)
        file_obj = fs.get(ObjectId(file_id))
        
        # Verifica se é imagem
        if not file_obj.content_type.startswith('image/'):
            return jsonify({'erro': 'Arquivo não é uma imagem'}), 400
        
        response = file_obj.read()
        return send_file(
            BytesIO(response),
            mimetype=file_obj.content_type,
            as_attachment=False,
            download_name=file_obj.filename
        )
        
    except Exception as e:
        print(f"❌ Erro ao buscar foto: {e}")
        return jsonify({'erro': 'Foto não encontrada'}), 404


# ============================================================
# ROTA LEGADA PARA COMPATIBILIDADE (REDIRECIONA)
# ============================================================

@uploads_bp.route('/api/alunos/arquivo/<file_id>', methods=['GET'])
def get_arquivo_aluno(file_id):
    """Rota legada - redireciona para /api/foto/"""
    return get_foto(file_id)


@uploads_bp.route('/api/upload-arquivo', methods=['POST'])
def upload_arquivo_legado():
    """Rota legada - redireciona para /api/upload-foto"""
    return upload_foto()