from flask import Blueprint, request, jsonify, render_template, send_file
from database.mongo import db
from gridfs import GridFS
from bson import ObjectId
from datetime import datetime
import io

# Cria o blueprint
documentos_bp = Blueprint('documentos', __name__, url_prefix='/documentos')

# Inicializar GridFS - CORRIGIDO
# db.db acessa a instância do banco de dados dentro do objeto MongoDB
fs = GridFS(db.db)

# Mapeamento de meses
MESES = {
    '1': 'Janeiro', '2': 'Fevereiro', '3': 'Março', '4': 'Abril',
    '5': 'Maio', '6': 'Junho', '7': 'Julho', '8': 'Agosto',
    '9': 'Setembro', '10': 'Outubro', '11': 'Novembro', '12': 'Dezembro'
}

MESES_LISTA = [
    {'valor': '1', 'nome': 'Janeiro'},
    {'valor': '2', 'nome': 'Fevereiro'},
    {'valor': '3', 'nome': 'Março'},
    {'valor': '4', 'nome': 'Abril'},
    {'valor': '5', 'nome': 'Maio'},
    {'valor': '6', 'nome': 'Junho'},
    {'valor': '7', 'nome': 'Julho'},
    {'valor': '8', 'nome': 'Agosto'},
    {'valor': '9', 'nome': 'Setembro'},
    {'valor': '10', 'nome': 'Outubro'},
    {'valor': '11', 'nome': 'Novembro'},
    {'valor': '12', 'nome': 'Dezembro'}
]

# Lista de categorias para Prestação de Contas
CATEGORIAS_PRESTACAO = [
    'Merenda Escolar',
    'Material de Limpeza',
    'Material de Expediente e Consumo',
    'Guia',
    'INSS',
    'DAFE',
    'FGTS',
    'Folha de Pagamento e Despesas de RH',
    'Serviços de Terceiros'
]

# Lista de unidades
UNIDADES = [
    'CEIC El Shadday',
    'CEIM Prof. Egberto Malta Moreira'
]


# ==================== PÁGINA PRINCIPAL ====================
@documentos_bp.route('/gestao')
def gestao_documentos():
    """Página principal de gestão de documentos"""
    return render_template('documentos/gestao_documentos.html', meses=MESES_LISTA)


# ==================== LISTAR DOCUMENTOS ====================
@documentos_bp.route('/api/listar', methods=['GET'])
def listar_documentos():
    """Lista todos os documentos com filtros"""
    try:
        tipo = request.args.get('tipo', '')
        mes = request.args.get('mes', '')
        nome = request.args.get('nome', '').lower()
        ano = request.args.get('ano', '')
        unidade = request.args.get('unidade', '')
        categoria = request.args.get('categoria', '')
        
        # Buscar documentos na coleção
        colecao = db.db.documentos
        query = {}
        
        if tipo:
            query['tipo'] = tipo
        if mes and mes in MESES:
            query['mes'] = MESES[mes]
        if ano:
            query['ano'] = ano
        if unidade:
            query['unidade'] = unidade
        if categoria:
            query['categoria'] = categoria
        if nome:
            query['nome_lower'] = {'$regex': nome, '$options': 'i'}
        
        documentos = list(colecao.find(query).sort('data_upload', -1))
        
        # Converter ObjectId para string
        for doc in documentos:
            doc['_id'] = str(doc['_id'])
            if doc.get('file_id'):
                doc['file_id'] = str(doc['file_id'])
            # Garantir que nota_fiscal existe
            if 'nota_fiscal' not in doc:
                doc['nota_fiscal'] = None
        
        return jsonify({
            'sucesso': True,
            'documentos': documentos,
            'total': len(documentos)
        })
        
    except Exception as e:
        print(f"❌ Erro ao listar documentos: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# ==================== UPLOAD DE DOCUMENTO ====================
@documentos_bp.route('/api/upload', methods=['POST'])
def upload_documento():
    """Upload de documento (prestação de contas ou atestado)"""
    try:
        # Receber dados do formulário
        tipo = request.form.get('tipo')
        unidade = request.form.get('unidade')
        nome_pessoa = request.form.get('nome_pessoa', '').strip()
        mes = request.form.get('mes')
        ano = request.form.get('ano')
        nota_fiscal = request.form.get('nota_fiscal', '').strip()
        
        if 'arquivo' not in request.files:
            return jsonify({'sucesso': False, 'erro': 'Nenhum arquivo enviado'}), 400
        
        file = request.files['arquivo']
        if not file or not file.filename:
            return jsonify({'sucesso': False, 'erro': 'Arquivo inválido'}), 400
        
        # Validar campos obrigatórios
        if not tipo:
            return jsonify({'sucesso': False, 'erro': 'Tipo de documento é obrigatório'}), 400
        if not unidade:
            return jsonify({'sucesso': False, 'erro': 'Unidade é obrigatória'}), 400
        if not nome_pessoa:
            return jsonify({'sucesso': False, 'erro': 'Nome é obrigatório'}), 400
        if not mes:
            return jsonify({'sucesso': False, 'erro': 'Mês é obrigatório'}), 400
        if not ano:
            return jsonify({'sucesso': False, 'erro': 'Ano é obrigatório'}), 400
        
        mes_nome = MESES.get(mes, mes)
        
        # Gerar nome do arquivo
        extensao = file.filename.rsplit('.', 1)[-1].lower()
        nome_arquivo = f"{nome_pessoa}_{mes_nome}_{ano}"
        if tipo == 'atestado':
            nome_arquivo += "_atestado"
        elif tipo == 'prestacao':
            nome_arquivo += "_prestacao"
        nome_arquivo += f".{extensao}"
        
        # Ler arquivo
        file_data = file.read()
        
        # Preparar metadados
        metadata = {
            'tipo': tipo,
            'unidade': unidade,
            'nome_pessoa': nome_pessoa,
            'mes': mes_nome,
            'ano': ano,
            'data_upload': datetime.now()
        }
        
        # Se for prestação de contas, adiciona categoria
        categoria = None
        if tipo == 'prestacao':
            categoria = request.form.get('categoria')
            if categoria:
                metadata['categoria'] = categoria
        
        # Se tem nota fiscal, adiciona
        if nota_fiscal:
            metadata['nota_fiscal'] = nota_fiscal
        
        # Salvar no GridFS
        file_id = fs.put(
            file_data,
            filename=nome_arquivo,
            content_type=file.content_type,
            metadata=metadata
        )
        
        # Salvar referência na coleção documentos
        colecao = db.db.documentos
        doc_ref = {
            'file_id': file_id,
            'nome_arquivo': nome_arquivo,
            'nome_pessoa': nome_pessoa,
            'nome_lower': nome_pessoa.lower(),
            'tipo': tipo,
            'unidade': unidade,
            'mes': mes_nome,
            'ano': ano,
            'extensao': extensao,
            'tamanho': len(file_data),
            'data_upload': datetime.now(),
            'data_formatada': datetime.now().strftime('%d/%m/%Y %H:%M')
        }
        
        # Adiciona categoria se for prestação
        if tipo == 'prestacao' and categoria:
            doc_ref['categoria'] = categoria
        
        # Adiciona nota fiscal se tiver
        if nota_fiscal:
            doc_ref['nota_fiscal'] = nota_fiscal
        
        colecao.insert_one(doc_ref)
        
        print(f"✅ Documento salvo: {nome_arquivo} (ID: {file_id})")
        print(f"   📌 Tipo: {tipo}")
        print(f"   🏫 Unidade: {unidade}")
        if nota_fiscal:
            print(f"   📄 Nota Fiscal: {nota_fiscal}")
        if categoria:
            print(f"   📂 Categoria: {categoria}")
        
        return jsonify({
            'sucesso': True,
            'mensagem': 'Documento enviado com sucesso!',
            'documento': {
                'id': str(doc_ref['_id']),
                'nome_arquivo': nome_arquivo,
                'nome_pessoa': nome_pessoa,
                'tipo': tipo,
                'unidade': unidade,
                'mes': mes_nome,
                'ano': ano,
                'nota_fiscal': nota_fiscal if nota_fiscal else None,
                'categoria': categoria if categoria else None,
                'data_formatada': doc_ref['data_formatada'],
                'tamanho': len(file_data)
            }
        })
        
    except Exception as e:
        print(f"❌ Erro no upload: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# ==================== ATUALIZAR DOCUMENTO ====================
@documentos_bp.route('/api/atualizar', methods=['POST'])
def atualizar_documento():
    """Atualizar um documento existente"""
    try:
        documento_id = request.form.get('documento_id')
        if not documento_id:
            return jsonify({'sucesso': False, 'erro': 'ID do documento não informado'}), 400
        
        # Buscar documento existente
        colecao = db.db.documentos
        doc_existente = colecao.find_one({'_id': ObjectId(documento_id)})
        if not doc_existente:
            return jsonify({'sucesso': False, 'erro': 'Documento não encontrado'}), 404
        
        # Receber dados do formulário
        tipo = request.form.get('tipo')
        unidade = request.form.get('unidade')
        nome_pessoa = request.form.get('nome_pessoa', '').strip()
        mes = request.form.get('mes')
        ano = request.form.get('ano')
        nota_fiscal = request.form.get('nota_fiscal', '').strip()
        
        # Validar campos obrigatórios
        if not tipo:
            return jsonify({'sucesso': False, 'erro': 'Tipo de documento é obrigatório'}), 400
        if not unidade:
            return jsonify({'sucesso': False, 'erro': 'Unidade é obrigatória'}), 400
        if not nome_pessoa:
            return jsonify({'sucesso': False, 'erro': 'Nome é obrigatório'}), 400
        if not mes:
            return jsonify({'sucesso': False, 'erro': 'Mês é obrigatório'}), 400
        if not ano:
            return jsonify({'sucesso': False, 'erro': 'Ano é obrigatório'}), 400
        
        mes_nome = MESES.get(mes, mes)
        
        # Preparar dados de atualização
        dados_atualizacao = {
            'nome_pessoa': nome_pessoa,
            'nome_lower': nome_pessoa.lower(),
            'tipo': tipo,
            'unidade': unidade,
            'mes': mes_nome,
            'ano': ano,
            'data_atualizacao': datetime.now(),
            'data_formatada': datetime.now().strftime('%d/%m/%Y %H:%M')
        }
        
        # Adiciona categoria se for prestação
        if tipo == 'prestacao':
            categoria = request.form.get('categoria')
            if categoria:
                dados_atualizacao['categoria'] = categoria
            else:
                # Se não veio categoria, remove do documento
                dados_atualizacao['categoria'] = None
        
        # Adiciona nota fiscal se tiver
        if nota_fiscal:
            dados_atualizacao['nota_fiscal'] = nota_fiscal
        else:
            dados_atualizacao['nota_fiscal'] = None
        
        # Verificar se veio um novo arquivo
        if 'arquivo' in request.files:
            file = request.files['arquivo']
            if file and file.filename:
                # Gerar novo nome do arquivo
                extensao = file.filename.rsplit('.', 1)[-1].lower()
                nome_arquivo = f"{nome_pessoa}_{mes_nome}_{ano}"
                if tipo == 'atestado':
                    nome_arquivo += "_atestado"
                elif tipo == 'prestacao':
                    nome_arquivo += "_prestacao"
                nome_arquivo += f".{extensao}"
                
                # Ler arquivo
                file_data = file.read()
                
                # Excluir arquivo antigo do GridFS
                fs.delete(doc_existente['file_id'])
                
                # Salvar novo arquivo no GridFS
                metadata = {
                    'tipo': tipo,
                    'unidade': unidade,
                    'nome_pessoa': nome_pessoa,
                    'mes': mes_nome,
                    'ano': ano,
                    'data_upload': datetime.now()
                }
                if tipo == 'prestacao' and dados_atualizacao.get('categoria'):
                    metadata['categoria'] = dados_atualizacao['categoria']
                if nota_fiscal:
                    metadata['nota_fiscal'] = nota_fiscal
                
                novo_file_id = fs.put(
                    file_data,
                    filename=nome_arquivo,
                    content_type=file.content_type,
                    metadata=metadata
                )
                
                dados_atualizacao['file_id'] = novo_file_id
                dados_atualizacao['nome_arquivo'] = nome_arquivo
                dados_atualizacao['extensao'] = extensao
                dados_atualizacao['tamanho'] = len(file_data)
        
        # Atualizar no banco
        colecao.update_one(
            {'_id': ObjectId(documento_id)},
            {'$set': dados_atualizacao}
        )
        
        print(f"✅ Documento atualizado: {doc_existente['nome_arquivo']}")
        
        return jsonify({
            'sucesso': True,
            'mensagem': 'Documento atualizado com sucesso!'
        })
        
    except Exception as e:
        print(f"❌ Erro ao atualizar documento: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# ==================== DOWNLOAD DE DOCUMENTO ====================
@documentos_bp.route('/api/download/<documento_id>', methods=['GET'])
def download_documento(documento_id):
    """Download de um documento pelo ID"""
    try:
        # Buscar documento na coleção
        colecao = db.db.documentos
        doc = colecao.find_one({'_id': ObjectId(documento_id)})
        if not doc:
            return jsonify({'erro': 'Documento não encontrado'}), 404
        
        # Buscar arquivo no GridFS
        arquivo = fs.get(doc['file_id'])
        
        # Determinar o tipo MIME
        mime_type = 'application/octet-stream'
        if doc['extensao'] in ['jpg', 'jpeg']:
            mime_type = 'image/jpeg'
        elif doc['extensao'] == 'png':
            mime_type = 'image/png'
        elif doc['extensao'] == 'pdf':
            mime_type = 'application/pdf'
        
        return send_file(
            io.BytesIO(arquivo.read()),
            mimetype=mime_type,
            as_attachment=True,
            download_name=doc['nome_arquivo']
        )
        
    except Exception as e:
        print(f"❌ Erro no download: {e}")
        return jsonify({'erro': str(e)}), 500


# ==================== VISUALIZAR DOCUMENTO ====================
@documentos_bp.route('/api/visualizar/<documento_id>', methods=['GET'])
def visualizar_documento(documento_id):
    """Visualizar um documento pelo ID"""
    try:
        colecao = db.db.documentos
        doc = colecao.find_one({'_id': ObjectId(documento_id)})
        if not doc:
            return jsonify({'erro': 'Documento não encontrado'}), 404
        
        arquivo = fs.get(doc['file_id'])
        
        # Determinar o tipo MIME
        mime_type = 'application/octet-stream'
        if doc['extensao'] in ['jpg', 'jpeg']:
            mime_type = 'image/jpeg'
        elif doc['extensao'] == 'png':
            mime_type = 'image/png'
        elif doc['extensao'] == 'pdf':
            mime_type = 'application/pdf'
        
        return send_file(
            io.BytesIO(arquivo.read()),
            mimetype=mime_type,
            as_attachment=False,
            download_name=doc['nome_arquivo']
        )
        
    except Exception as e:
        print(f"❌ Erro na visualização: {e}")
        return jsonify({'erro': str(e)}), 500


# ==================== EXCLUIR DOCUMENTO ====================
@documentos_bp.route('/api/excluir/<documento_id>', methods=['DELETE'])
def excluir_documento(documento_id):
    """Excluir um documento pelo ID"""
    try:
        colecao = db.db.documentos
        doc = colecao.find_one({'_id': ObjectId(documento_id)})
        if not doc:
            return jsonify({'erro': 'Documento não encontrado'}), 404
        
        # Excluir do GridFS
        fs.delete(doc['file_id'])
        
        # Excluir da coleção
        colecao.delete_one({'_id': ObjectId(documento_id)})
        
        print(f"✅ Documento excluído: {doc['nome_arquivo']}")
        
        return jsonify({
            'sucesso': True,
            'mensagem': 'Documento excluído com sucesso!'
        })
        
    except Exception as e:
        print(f"❌ Erro na exclusão: {e}")
        return jsonify({'erro': str(e)}), 500


# ==================== ESTATÍSTICAS ====================
@documentos_bp.route('/api/estatisticas', methods=['GET'])
def estatisticas():
    """Retorna estatísticas dos documentos"""
    try:
        colecao = db.db.documentos
        total_prestacao = colecao.count_documents({'tipo': 'prestacao'})
        total_atestado = colecao.count_documents({'tipo': 'atestado'})
        
        # Contagem por unidade
        por_unidade = []
        for unidade in UNIDADES:
            count = colecao.count_documents({'unidade': unidade})
            por_unidade.append({
                'unidade': unidade,
                'total': count
            })
        
        # Contagem por mês
        por_mes = []
        for mes in MESES_LISTA:
            count = colecao.count_documents({'mes': mes['nome']})
            por_mes.append({
                'mes': mes['nome'],
                'total': count
            })
        
        return jsonify({
            'sucesso': True,
            'estatisticas': {
                'total_geral': total_prestacao + total_atestado,
                'total_prestacao': total_prestacao,
                'total_atestado': total_atestado,
                'por_unidade': por_unidade,
                'por_mes': por_mes
            }
        })
        
    except Exception as e:
        print(f"❌ Erro nas estatísticas: {e}")
        return jsonify({'erro': str(e)}), 500