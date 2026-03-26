from flask import Blueprint, request, jsonify, render_template, send_file, redirect
from services.aluno_service import AlunoService
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import uuid
import traceback
import sys
import base64
from io import BytesIO
from bson import ObjectId

alunos_bp = Blueprint('alunos', __name__)
aluno_service = AlunoService()

# Detecta se está no Vercel
IS_VERCEL = os.environ.get('VERCEL') == '1' or os.environ.get('NOW') is not None

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file_to_db(file, campo):
    """Salva um arquivo como Base64 no MongoDB"""
    if file and allowed_file(file.filename):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{timestamp}_{unique_id}_{campo}.{ext}"
        
        # Lê o arquivo e converte para Base64
        file_data = file.read()
        base64_data = base64.b64encode(file_data).decode('utf-8')
        
        print(f"   ✅ Arquivo convertido para Base64: {filename} ({len(file_data)} bytes)")
        
        return {
            'campo': campo,
            'nome': filename,
            'dados': base64_data,
            'tipo': ext,
            'tamanho': len(file_data)
        }
    return None

def save_uploaded_file(file, subfolder, campo):
    """Salva um arquivo enviado - Prioriza MongoDB no Vercel"""
    # Detecta se está no Vercel
    IS_VERCEL = os.environ.get('VERCEL') == '1' or os.environ.get('NOW') is not None
    
    # No Vercel: salva apenas no MongoDB (sem tentar sistema de arquivos)
    if IS_VERCEL:
        info_db = save_uploaded_file_to_db(file, campo)
        if info_db:
            return info_db
        # Se falhou no MongoDB, retorna None sem tentar arquivo
        print(f"   ⚠️ Falha ao salvar no MongoDB: {campo}")
        return None
    
    # Fora do Vercel (desenvolvimento local): tenta MongoDB primeiro, depois arquivo
    info_db = save_uploaded_file_to_db(file, campo)
    if info_db:
        return info_db
    
    # Fallback: salva no sistema de arquivos (apenas local)
    if file and allowed_file(file.filename):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{timestamp}_{unique_id}_{campo}.{ext}"
        
        upload_path = os.path.join('uploads', subfolder)
        try:
            os.makedirs(upload_path, exist_ok=True)
            print(f"   📁 Pasta criada: {upload_path}")
        except Exception as e:
            print(f"   ⚠️ Não foi possível criar {upload_path}: {e}")
            upload_path = '/tmp'
        
        filepath = os.path.join(upload_path, filename)
        
        try:
            file.save(filepath)
            print(f"   ✅ Arquivo salvo em: {filepath}")
            
            return {
                'campo': campo,
                'nome': filename,
                'caminho': f"/uploads/{subfolder}/{filename}",
                'tipo': ext,
                'tamanho': os.path.getsize(filepath) if os.path.exists(filepath) else 0
            }
        except Exception as e:
            print(f"   ❌ Erro ao salvar arquivo: {e}")
            return None
    return None


# ============================================
# NOVOS ENDPOINTS PARA GRIDFS (UPLOAD DIRETO)
# ============================================

@alunos_bp.route('/api/upload-arquivo', methods=['POST'])
def upload_arquivo():
    """
    Endpoint para upload direto de arquivo para GridFS
    Retorna o file_id para ser salvo no documento do aluno
    """
    try:
        print("\n📤 UPLOAD DIRETO PARA GRIDFS")
        
        campo = request.form.get('campo')
        if not campo:
            return jsonify({'sucesso': False, 'erro': 'Campo não informado'}), 400
        
        if 'arquivo' not in request.files:
            return jsonify({'sucesso': False, 'erro': 'Nenhum arquivo enviado'}), 400
        
        file = request.files['arquivo']
        if not file or not file.filename:
            return jsonify({'sucesso': False, 'erro': 'Arquivo inválido'}), 400
        
        from database.mongo import salvar_arquivo_gridfs
        
        # Salva no GridFS
        file_id = salvar_arquivo_gridfs(file, file.filename, campo)
        
        if not file_id:
            return jsonify({'sucesso': False, 'erro': 'Erro ao salvar arquivo'}), 500
        
        print(f"✅ Upload concluído! ID: {file_id}")
        
        return jsonify({
            'sucesso': True,
            'file_id': file_id,
            'campo': campo,
            'nome_original': file.filename
        })
        
    except Exception as e:
        print(f"❌ Erro no upload: {e}")
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@alunos_bp.route('/api/visualizar-gridfs/<file_id>', methods=['GET'])
def visualizar_gridfs(file_id):
    """Visualiza um arquivo salvo no GridFS"""
    try:
        from database.mongo import get_arquivo_gridfs
        
        arquivo = get_arquivo_gridfs(file_id)
        
        if not arquivo:
            return jsonify({'erro': 'Arquivo não encontrado'}), 404
        
        # Determina o tipo MIME
        metadata = arquivo.metadata or {}
        content_type = metadata.get('content_type', 'application/octet-stream')
        
        # Se for PDF ou imagem, define MIME correto
        if arquivo.filename:
            ext = arquivo.filename.rsplit('.', 1)[-1].lower() if '.' in arquivo.filename else ''
            if ext in ['jpg', 'jpeg']:
                content_type = 'image/jpeg'
            elif ext == 'png':
                content_type = 'image/png'
            elif ext == 'pdf':
                content_type = 'application/pdf'
        
        return send_file(
            BytesIO(arquivo.read()),
            mimetype=content_type,
            as_attachment=False,
            download_name=arquivo.filename
        )
        
    except Exception as e:
        print(f"❌ Erro ao visualizar arquivo: {e}")
        traceback.print_exc()
        return jsonify({'erro': str(e)}), 500


# ============================================
# NOVO ENDPOINT DE CADASTRO VIA JSON
# ============================================

@alunos_bp.route('/api/alunos/cadastrar-json', methods=['POST'])
def cadastrar_aluno_json():
    """Endpoint para cadastrar um novo aluno (recebe JSON com IDs dos arquivos do GridFS)"""
    try:
        print("\n" + "="*60)
        print("📥 RECEBENDO REQUISIÇÃO DE CADASTRO (JSON - GRIDFS)")
        print("="*60)
        
        # Recebe JSON, não form-data
        dados = request.get_json()
        
        if not dados:
            return jsonify({'sucesso': False, 'erro': 'Dados não enviados'}), 400
        
        # Extrai os arquivos_ids
        arquivos_ids = dados.pop('arquivos_ids', {})
        
        print(f"📦 Dados recebidos:")
        print(f"   📝 Campos de texto: {len(dados)}")
        print(f"   📎 IDs de arquivos: {len(arquivos_ids)}")
        
        # ===== GERAR NÚMERO DE INSCRIÇÃO =====
        from database.mongo import db
        from datetime import datetime
        
        ano = datetime.now().year
        num_inscricao = dados.get('num_inscricao')
        
        if not num_inscricao:
            num_inscricao = _gerar_novo_numero_inscricao(db, ano)
            print(f"🆕 Número gerado: {num_inscricao}")
        else:
            print(f"📌 Número recebido: {num_inscricao}")
        
        # ===== PREPARA O DOCUMENTO DO ALUNO =====
        aluno = {
            'num_inscricao': num_inscricao,
            'status': 'ativo',
            'data_cadastro': datetime.now(),
            'dados_pessoais': {
                'nome': dados.get('nome', ''),
                'data_nasc': dados.get('data_nasc', ''),
                'sexo': dados.get('sexo', ''),
                'raca': dados.get('raca', ''),
                'naturalidade': dados.get('naturalidade', ''),
                'nacionalidade': dados.get('nacionalidade', 'Brasileira'),
                'ra': dados.get('ra', '')
            },
            'endereco': {
                'cep': dados.get('cep', ''),
                'logradouro': dados.get('endereco', ''),
                'numero': dados.get('numero', ''),
                'complemento': dados.get('complemento', ''),
                'bairro': dados.get('bairro', ''),
                'cidade': dados.get('cidade', ''),
                'uf': dados.get('uf', '')
            },
            'turma': {
                'unidade': dados.get('unidade', ''),
                'turma': dados.get('turma', ''),
                'periodo': dados.get('periodo', ''),
                'ano_letivo': dados.get('ano_letivo', '2026')
            },
            'saude': {
                'tipo_sanguineo': dados.get('tipo_sanguineo', ''),
                'plano_saude': dados.get('plano_saude', ''),
                'alergias': dados.get('alergias', ''),
                'medicamentos': dados.get('medicamentos', ''),
                'restricoes': dados.get('restricoes', ''),
                'pediatra': dados.get('pediatra', ''),
                'contato_pediatra': dados.get('contato_pediatra', ''),
                'deficiencia': dados.get('deficiencia', 'nao'),
                'deficiencia_desc': dados.get('deficiencia_desc', '')
            },
            'responsaveis': [],
            'arquivos_ids': arquivos_ids,  # IDs dos arquivos no GridFS
            'usando_gridfs': True
        }
        
        # ===== PROCESSA RESPONSÁVEL PRINCIPAL =====
        responsavel_principal = {
            'nome': dados.get('responsavel1_nome', ''),
            'parentesco': dados.get('responsavel1_parentesco', ''),
            'telefone': dados.get('responsavel1_telefone', ''),
            'telefone_contato': dados.get('responsavel1_telefone_contato', ''),
            'cpf': dados.get('responsavel1_cpf', ''),
            'rg': dados.get('responsavel1_rg', ''),
            'email': dados.get('responsavel1_email', ''),
            'tipo': 'principal'
        }
        aluno['responsaveis'].append(responsavel_principal)
        
        # Processa responsáveis adicionais
        for i in range(2, 6):
            nome = dados.get(f'responsavel{i}_nome', '')
            if nome:
                resp_adicional = {
                    'nome': nome,
                    'parentesco': dados.get(f'responsavel{i}_parentesco', ''),
                    'telefone': dados.get(f'responsavel{i}_telefone', ''),
                    'telefone_contato': dados.get(f'responsavel{i}_telefone_contato', ''),
                    'cpf': dados.get(f'responsavel{i}_cpf', ''),
                    'rg': dados.get(f'responsavel{i}_rg', ''),
                    'email': dados.get(f'responsavel{i}_email', ''),
                    'tipo': 'adicional'
                }
                aluno['responsaveis'].append(resp_adicional)
        
        # Processa terceiros
        terceiros = []
        for i in range(1, 4):
            nome = dados.get(f'terceiro{i}_nome', '')
            if nome:
                terceiro = {
                    'nome': nome,
                    'telefone': dados.get(f'terceiro{i}_telefone', ''),
                    'cpf': dados.get(f'terceiro{i}_cpf', ''),
                    'rg': dados.get(f'terceiro{i}_rg', ''),
                    'email': dados.get(f'terceiro{i}_email', '')
                }
                terceiros.append(terceiro)
        
        if terceiros:
            aluno['terceiros'] = terceiros
        
        # Processa transporte
        if dados.get('utiliza_transporte') == '1':
            aluno['transporte'] = {
                'nome': dados.get('transporte_nome', ''),
                'cnpj': dados.get('transporte_cnpj', ''),
                'cpf': dados.get('transporte_cpf', ''),
                'rg': dados.get('transporte_rg', ''),
                'telefone': dados.get('transporte_telefone', ''),
                'email': dados.get('transporte_email', '')
            }
        
        # Salva no banco
        result = db.alunos.insert_one(aluno)
        
        print(f"✅ Cadastro realizado! Nº: {num_inscricao}")
        print(f"📎 IDs dos arquivos: {list(arquivos_ids.keys())}")
        print("="*60)
        
        return jsonify({
            'sucesso': True,
            'mensagem': 'Aluno cadastrado com sucesso!',
            'num_inscricao': num_inscricao,
            'id': str(result.inserted_id)
        })
        
    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# ============================================
# ENDPOINT DE VISUALIZAÇÃO VIA GRIDFS
# ============================================

@alunos_bp.route('/api/alunos/arquivo/<file_id>', methods=['GET'])
def visualizar_arquivo_gridfs(file_id):
    """Visualiza um arquivo salvo no GridFS pelo ID"""
    try:
        from database.mongo import get_arquivo_gridfs
        
        arquivo = get_arquivo_gridfs(file_id)
        
        if not arquivo:
            return jsonify({'erro': 'Arquivo não encontrado'}), 404
        
        # Determina o tipo MIME
        ext = arquivo.filename.rsplit('.', 1)[-1].lower() if '.' in arquivo.filename else ''
        if ext in ['jpg', 'jpeg']:
            mime_type = 'image/jpeg'
        elif ext == 'png':
            mime_type = 'image/png'
        elif ext == 'pdf':
            mime_type = 'application/pdf'
        else:
            mime_type = 'application/octet-stream'
        
        return send_file(
            BytesIO(arquivo.read()),
            mimetype=mime_type,
            as_attachment=False,
            download_name=arquivo.filename
        )
        
    except Exception as e:
        print(f"❌ Erro ao visualizar arquivo: {e}")
        traceback.print_exc()
        return jsonify({'erro': str(e)}), 500


@alunos_bp.route('/api/visualizar/<campo>/<num_inscricao>', methods=['GET'])
def visualizar_arquivo(campo, num_inscricao):
    """Visualiza um arquivo salvo no MongoDB (Base64) - LEGADO"""
    try:
        # Busca o aluno
        aluno = aluno_service.get_aluno_by_inscricao(num_inscricao)
        if not aluno:
            return jsonify({'erro': 'Aluno não encontrado'}), 404
        
        # Verifica se usa GridFS
        if aluno.get('usando_gridfs') and aluno.get('arquivos_ids', {}).get(campo):
            file_id = aluno['arquivos_ids'][campo]
            return redirect(f'/api/alunos/arquivo/{file_id}')
        
        # Busca o arquivo pelo campo no modo legado
        arquivo = None
        for arq in aluno.get('arquivos', []):
            if arq.get('campo') == campo:
                arquivo = arq
                break
        
        if not arquivo:
            return jsonify({'erro': 'Arquivo não encontrado'}), 404
        
        # Se tem dados em Base64, renderiza
        if arquivo.get('dados'):
            dados_bytes = base64.b64decode(arquivo['dados'])
            
            if arquivo.get('tipo') in ['jpg', 'jpeg']:
                mime_type = 'image/jpeg'
            elif arquivo.get('tipo') == 'png':
                mime_type = 'image/png'
            elif arquivo.get('tipo') == 'gif':
                mime_type = 'image/gif'
            elif arquivo.get('tipo') == 'pdf':
                mime_type = 'application/pdf'
            else:
                mime_type = 'application/octet-stream'
            
            return send_file(
                BytesIO(dados_bytes),
                mimetype=mime_type,
                as_attachment=False,
                download_name=arquivo.get('nome', 'arquivo')
            )
        
        if arquivo.get('caminho'):
            return redirect(arquivo['caminho'])
        
        return jsonify({'erro': 'Arquivo não encontrado'}), 404
        
    except Exception as e:
        print(f"❌ Erro ao visualizar arquivo: {e}")
        traceback.print_exc()
        return jsonify({'erro': str(e)}), 500


# ============================================
# RESTANTE DO CÓDIGO (SEM ALTERAÇÕES)
# ============================================

@alunos_bp.route('/api/alunos/proximo-numero', methods=['GET'])
def proximo_numero():
    """Retorna o próximo número de inscrição APENAS PARA VISUALIZAÇÃO"""
    try:
        print("🔍 Buscando próximo número de inscrição...")
        from database.mongo import db
        from datetime import datetime
        
        ano = datetime.now().year
        
        ultimo_aluno = db.alunos.find_one(
            {'num_inscricao': {'$regex': f'-{ano}$'}},
            sort=[('num_inscricao', -1)]
        )
        
        if ultimo_aluno and ultimo_aluno.get('num_inscricao'):
            partes = ultimo_aluno['num_inscricao'].split('-')
            valor = int(partes[0]) + 1
            numero = f"{str(valor).zfill(3)}-{ano}"
        else:
            numero = f"001-{ano}"
        
        print(f"📌 Próximo número: {numero}")
        
        return jsonify({
            'sucesso': True,
            'numero': numero,
            'preview': True
        })
        
    except Exception as e:
        print(f"❌ Erro ao buscar próximo número: {str(e)}")
        traceback.print_exc()
        from datetime import datetime
        numero_temp = f"001-{datetime.now().year}"
        return jsonify({
            'sucesso': True,
            'numero': numero_temp,
            'preview': True
        })


def _gerar_novo_numero_inscricao(db, ano):
    """Função auxiliar para gerar um novo número de inscrição de forma atômica"""
    try:
        contador = db.contadores.find_one_and_update(
            {'nome': 'num_inscricao', 'ano': ano},
            {'$inc': {'valor': 1}},
            upsert=True,
            return_document=True
        )
        
        valor_atual = contador.get('valor', 1)
        numero = f"{str(valor_atual).zfill(3)}-{ano}"
        
        print(f"   📌 Contador atualizado: {valor_atual} -> {numero}")
        return numero
        
    except Exception as e:
        print(f"   ⚠️ Erro ao atualizar contador: {e}")
        ultimo_aluno = db.alunos.find_one(
            {'num_inscricao': {'$regex': f'-{ano}$'}},
            sort=[('num_inscricao', -1)]
        )
        
        if ultimo_aluno and ultimo_aluno.get('num_inscricao'):
            partes = ultimo_aluno['num_inscricao'].split('-')
            valor = int(partes[0]) + 1
            numero = f"{str(valor).zfill(3)}-{ano}"
        else:
            numero = f"001-{ano}"
        
        return numero


@alunos_bp.route('/api/alunos/cadastrar', methods=['POST'])
def cadastrar_aluno():
    """Endpoint para cadastrar um novo aluno (método tradicional - mantido para compatibilidade)"""
    try:
        print("\n" + "="*60)
        print("📥 RECEBENDO REQUISIÇÃO DE CADASTRO (TRADICIONAL)")
        print("="*60)
        
        print("\n🔍 ARQUIVOS RECEBIDOS NO REQUEST:")
        for key in request.files.keys():
            file = request.files[key]
            if file and file.filename:
                print(f"   📁 {key}: {file.filename}")
        
        print(f"\n📦 DADOS DO FORMULÁRIO:")
        for key, value in request.form.items():
            print(f"   📝 {key}: {value[:30] if value else 'vazio'}")
        
        from database.mongo import db
        from datetime import datetime
        
        ano = datetime.now().year
        num_inscricao_frontend = request.form.get('num_inscricao')
        
        if num_inscricao_frontend and num_inscricao_frontend != '':
            aluno_existente = aluno_service.get_aluno_by_inscricao(num_inscricao_frontend)
            
            if aluno_existente:
                num_inscricao = num_inscricao_frontend
                print(f"📝 Modo atualização - mantendo número: {num_inscricao}")
            else:
                if aluno_service.get_aluno_by_inscricao(num_inscricao_frontend):
                    print(f"⚠️ Número {num_inscricao_frontend} já existe, gerando novo...")
                    num_inscricao = _gerar_novo_numero_inscricao(db, ano)
                else:
                    num_inscricao = num_inscricao_frontend
                    print(f"✅ Usando número pré-gerado: {num_inscricao}")
                    
                    try:
                        partes = num_inscricao.split('-')
                        valor = int(partes[0])
                        db.contadores.find_one_and_update(
                            {'nome': 'num_inscricao', 'ano': ano},
                            {'$set': {'valor': valor}},
                            upsert=True
                        )
                        print(f"   📌 Contador atualizado para: {valor}")
                    except Exception as e:
                        print(f"   ⚠️ Erro ao atualizar contador: {e}")
        else:
            num_inscricao = _gerar_novo_numero_inscricao(db, ano)
            print(f"🆕 Gerando novo número: {num_inscricao}")
        
        arquivos_salvos = []
        
        # Processa fotos
        fotos = {
            'foto_aluno': 'alunos',
            'foto_responsavel1': 'pais',
            'foto_responsavel2': 'pais',
            'foto_responsavel3': 'pais',
            'foto_terceiro1': 'terceiros',
            'foto_terceiro2': 'terceiros',
            'foto_terceiro3': 'terceiros',
            'foto_transporte': 'documentos'
        }
        
        for campo, pasta in fotos.items():
            if campo in request.files:
                file = request.files[campo]
                if file and file.filename:
                    print(f"\n📸 Processando FOTO: {campo}")
                    info = save_uploaded_file(file, pasta, campo)
                    if info:
                        arquivos_salvos.append(info)
                        print(f"   ✅ Foto processada: {info['nome']}")
        
        # Processa documentos
        documentos = {
            'aluno_certidao': 'documentos',
            'aluno_cpf': 'documentos',
            'aluno_rg': 'documentos',
            'aluno_vacinacao': 'documentos',
            'aluno_laudos': 'documentos',
            'resp_rg': 'documentos',
            'resp_cpf': 'documentos',
            'resp_comprovante': 'documentos',
            'resp2_rg': 'documentos',
            'resp2_cpf': 'documentos',
            'terceiro_rg': 'documentos',
            'transporte_rg': 'documentos',
            'transporte_cpf': 'documentos',
            'transporte_cnh': 'documentos'
        }
        
        for campo, pasta in documentos.items():
            if campo in request.files:
                file = request.files[campo]
                if file and file.filename:
                    print(f"\n📄 Processando DOCUMENTO: {campo}")
                    info = save_uploaded_file(file, pasta, campo)
                    if info:
                        arquivos_salvos.append(info)
                        print(f"   ✅ Documento processado: {info['nome']}")
        
        print("\n💾 Salvando dados no banco...")
        
        form_data = request.form.copy()
        form_data['num_inscricao'] = num_inscricao
        
        resultado = aluno_service.salvar_aluno(form_data, arquivos_salvos)
        print(f"✅ Cadastro realizado! Nº: {resultado['num_inscricao']}")
        print("="*60)
        
        return jsonify({
            'sucesso': True,
            'mensagem': 'Aluno cadastrado com sucesso!',
            'num_inscricao': resultado['num_inscricao'],
            'id': resultado['id'],
            'arquivos_salvos': len(arquivos_salvos)
        })
        
    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")
        traceback.print_exc()
        print("="*60)
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


# ===== ROTA PARA ATUALIZAR ALUNO =====
@alunos_bp.route('/api/alunos/atualizar', methods=['POST'])
def atualizar_aluno():
    """Endpoint para atualizar um aluno existente"""
    try:
        print("\n" + "="*60)
        print("📝 RECEBENDO REQUISIÇÃO DE ATUALIZAÇÃO")
        print("="*60)
        
        num_inscricao_original = request.form.get('num_inscricao_original')
        
        if not num_inscricao_original:
            return jsonify({'sucesso': False, 'erro': 'Número de inscrição não fornecido'}), 400
            
        print(f"📌 Atualizando aluno: {num_inscricao_original}")
        
        aluno_existente = aluno_service.get_aluno_by_inscricao(num_inscricao_original)
        
        print("\n🔍 ARQUIVOS RECEBIDOS NO REQUEST:")
        for key in request.files.keys():
            file = request.files[key]
            if file and file.filename:
                print(f"   📁 {key}: {file.filename}")
        
        print(f"\n📦 DADOS DO FORMULÁRIO:")
        for key, value in request.form.items():
            print(f"   📝 {key}: {value[:30] if value else 'vazio'}")
        
        arquivos_salvos = []
        
        if aluno_existente and aluno_existente.get('arquivos'):
            for arq in aluno_existente['arquivos']:
                campo = arq.get('campo')
                if campo in request.files and request.files[campo] and request.files[campo].filename:
                    print(f"   🔄 Campo {campo} será substituído")
                else:
                    arquivos_salvos.append(arq)
                    print(f"   📌 Mantendo arquivo existente: {campo}")
        
        # Processa fotos
        fotos = {
            'foto_aluno': 'alunos',
            'foto_responsavel1': 'pais',
            'foto_responsavel2': 'pais',
            'foto_responsavel3': 'pais',
            'foto_terceiro1': 'terceiros',
            'foto_terceiro2': 'terceiros',
            'foto_terceiro3': 'terceiros',
            'foto_transporte': 'documentos'
        }
        
        for campo, pasta in fotos.items():
            if campo in request.files:
                file = request.files[campo]
                if file and file.filename:
                    print(f"\n📸 Processando nova FOTO: {campo}")
                    info = save_uploaded_file(file, pasta, campo)
                    if info:
                        arquivos_salvos = [a for a in arquivos_salvos if a.get('campo') != campo]
                        arquivos_salvos.append(info)
                        print(f"   ✅ Nova foto processada: {info['nome']}")
        
        # Processa documentos
        documentos = {
            'aluno_certidao': 'documentos',
            'aluno_cpf': 'documentos',
            'aluno_rg': 'documentos',
            'aluno_vacinacao': 'documentos',
            'aluno_laudos': 'documentos',
            'resp_rg': 'documentos',
            'resp_cpf': 'documentos',
            'resp_comprovante': 'documentos',
            'resp2_rg': 'documentos',
            'resp2_cpf': 'documentos',
            'terceiro_rg': 'documentos',
            'transporte_rg': 'documentos',
            'transporte_cpf': 'documentos',
            'transporte_cnh': 'documentos'
        }
        
        for campo, pasta in documentos.items():
            if campo in request.files:
                file = request.files[campo]
                if file and file.filename:
                    print(f"\n📄 Processando novo DOCUMENTO: {campo}")
                    info = save_uploaded_file(file, pasta, campo)
                    if info:
                        arquivos_salvos = [a for a in arquivos_salvos if a.get('campo') != campo]
                        arquivos_salvos.append(info)
                        print(f"   ✅ Novo documento processado: {info['nome']}")
        
        print("\n💾 Atualizando dados no banco...")
        resultado = aluno_service.atualizar_aluno(
            num_inscricao_original, 
            request.form, 
            arquivos_salvos
        )
        
        print(f"✅ Aluno atualizado! Nº: {resultado['num_inscricao']}")
        print("="*60)
        
        return jsonify({
            'sucesso': True,
            'mensagem': 'Aluno atualizado com sucesso!',
            'num_inscricao': resultado['num_inscricao']
        })
        
    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")
        traceback.print_exc()
        print("="*60)
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


# ===== ROTA PARA EXCLUIR ALUNO =====
@alunos_bp.route('/api/alunos/excluir', methods=['POST'])
def excluir_aluno():
    """Endpoint para excluir um aluno"""
    try:
        print("\n" + "="*60)
        print("🗑️ RECEBENDO REQUISIÇÃO DE EXCLUSÃO")
        print("="*60)
        
        dados = request.get_json()
        num_inscricao = dados.get('num_inscricao')
        
        if not num_inscricao:
            return jsonify({
                'sucesso': False, 
                'erro': 'Número de inscrição não fornecido'
            }), 400
        
        print(f"📌 Excluindo aluno: {num_inscricao}")
        
        aluno = aluno_service.get_aluno_by_inscricao(num_inscricao)
        
        if not aluno:
            return jsonify({
                'sucesso': False,
                'erro': 'Aluno não encontrado'
            }), 404
        
        resultado = aluno_service.excluir_aluno(num_inscricao)
        
        print(f"✅ Aluno excluído: {num_inscricao}")
        print("="*60)
        
        return jsonify({
            'sucesso': True,
            'mensagem': 'Aluno excluído com sucesso!',
            'num_inscricao': num_inscricao
        })
        
    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")
        traceback.print_exc()
        print("="*60)
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


# ===== ROTA PARA PÁGINA DE CADASTRO =====
@alunos_bp.route('/alunos/cadastro')
def cadastro_aluno():
    """Rota para página de cadastro"""
    try:
        num_inscricao = request.args.get('editar')
        aluno_data = None
        
        if num_inscricao:
            print(f"📝 Modo edição - buscando aluno: {num_inscricao}")
            aluno = aluno_service.get_aluno_by_inscricao(num_inscricao)
            if aluno:
                if '_id' in aluno:
                    aluno['_id'] = str(aluno['_id'])
                
                if aluno.get('arquivos'):
                    print(f"📁 Encontrados {len(aluno['arquivos'])} arquivos")
                    arquivos_dict = {}
                    for arquivo in aluno['arquivos']:
                        campo = arquivo.get('campo')
                        arquivos_dict[campo] = arquivo
                        
                        if arquivo.get('dados') and arquivo.get('tipo') in ['jpg', 'jpeg', 'png', 'gif']:
                            arquivo['data_url'] = f"data:image/{arquivo['tipo']};base64,{arquivo['dados']}"
                            print(f"   ✅ Imagem {campo} preparada para exibição")
                        elif arquivo.get('dados') and arquivo.get('tipo') == 'pdf':
                            arquivo['data_url'] = f"data:application/pdf;base64,{arquivo['dados']}"
                            print(f"   ✅ PDF {campo} preparado para download")
                    
                    aluno['arquivos_dict'] = arquivos_dict
                
                aluno_data = aluno
                print(f"✅ Aluno encontrado: {aluno_data['dados_pessoais']['nome']}")
            else:
                print(f"❌ Aluno não encontrado: {num_inscricao}")
        
        return render_template('alunos/cadastro_aluno.html', aluno=aluno_data)
        
    except Exception as e:
        print(f"❌ Erro ao carregar página de cadastro: {str(e)}")
        traceback.print_exc()
        return render_template('alunos/cadastro_aluno.html', aluno=None)


@alunos_bp.route('/api/alunos/buscar', methods=['GET'])
def buscar_alunos():
    """Endpoint para buscar alunos"""
    try:
        nome = request.args.get('nome', '')
        num_inscricao = request.args.get('num_inscricao', '')
        turma = request.args.get('turma', '')
        unidade = request.args.get('unidade', '')
        
        print(f"\n🔍 Buscando alunos com filtros: nome='{nome}', inscrição='{num_inscricao}', turma='{turma}', unidade='{unidade}'")
        
        filtro = {}
        if nome:
            filtro['dados_pessoais.nome'] = {'$regex': nome, '$options': 'i'}
        if num_inscricao:
            filtro['num_inscricao'] = {'$regex': num_inscricao, '$options': 'i'}
        if turma:
            filtro['turma.turma'] = turma
        if unidade:
            filtro['turma.unidade'] = unidade
        
        alunos = aluno_service.buscar_alunos(filtro)
        
        for aluno in alunos:
            if aluno.get('arquivos'):
                for arquivo in aluno['arquivos']:
                    if arquivo.get('dados'):
                        tipo = arquivo.get('tipo', 'jpeg')
                        if tipo in ['jpg', 'jpeg', 'png', 'gif']:
                            arquivo['data_url'] = f"data:image/{tipo};base64,{arquivo['dados']}"
        
        print(f"✅ Encontrados {len(alunos)} alunos")
        
        return jsonify({
            'sucesso': True,
            'alunos': alunos
        })
        
    except Exception as e:
        print(f"❌ Erro na busca: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@alunos_bp.route('/api/alunos/<id>', methods=['GET'])
def get_aluno(id):
    """Retorna dados de um aluno específico"""
    try:
        aluno = aluno_service.get_aluno_by_id(id)
        if aluno:
            return jsonify({
                'sucesso': True,
                'aluno': aluno
            })
        else:
            return jsonify({
                'sucesso': False,
                'erro': 'Aluno não encontrado'
            }), 404
    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@alunos_bp.route('/api/alunos/inscricao/<num_inscricao>', methods=['GET'])
def get_aluno_by_inscricao(num_inscricao):
    """Retorna dados de um aluno pelo número de inscrição"""
    try:
        aluno = aluno_service.get_aluno_by_inscricao(num_inscricao)
        if aluno:
            return jsonify({
                'sucesso': True,
                'aluno': aluno
            })
        else:
            return jsonify({
                'sucesso': False,
                'erro': 'Aluno não encontrado'
            }), 404
    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@alunos_bp.route('/api/alunos/estatisticas', methods=['GET'])
def estatisticas():
    """Retorna estatísticas gerais"""
    try:
        alunos = aluno_service.buscar_alunos({})
        
        total_alunos = len(alunos)
        
        turmas = set()
        for aluno in alunos:
            if aluno.get('turma', {}).get('turma'):
                turmas.add(aluno['turma']['turma'])
        
        total_responsaveis = 0
        for aluno in alunos:
            total_responsaveis += len(aluno.get('responsaveis', []))
        
        return jsonify({
            'sucesso': True,
            'estatisticas': {
                'total_alunos': total_alunos,
                'total_turmas': len(turmas),
                'total_responsaveis': total_responsaveis
            }
        })
    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500