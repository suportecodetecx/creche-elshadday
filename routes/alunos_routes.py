from flask import Blueprint, request, jsonify, render_template, send_file, redirect, abort
from services.aluno_service import AlunoService
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import uuid
import traceback
import sys
import base64
import json
import re
from io import BytesIO
from bson import ObjectId

alunos_bp = Blueprint('alunos', __name__)
aluno_service = AlunoService()

# Detecta se está no Vercel
IS_VERCEL = os.environ.get('VERCEL') == '1' or os.environ.get('NOW') is not None

# Apenas imagens são permitidas agora
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ============================================
# FUNÇÃO AUXILIAR PARA GERAR NÚMERO DE INSCRIÇÃO
# ============================================

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


# ============================================
# ENDPOINT PARA VERIFICAR DUPLICIDADE
# ============================================

@alunos_bp.route('/api/alunos/verificar-duplicidade', methods=['GET'])
def verificar_duplicidade():
    """Verifica se já existe aluno com o mesmo nome ou RA"""
    try:
        nome = request.args.get('nome', '').strip()
        ra = request.args.get('ra', '').strip()
        num_inscricao_ignore = request.args.get('ignore_inscricao', '')
        
        print(f"\n🔍 Verificando duplicidade: nome='{nome}', ra='{ra}'")
        
        from database.mongo import db
        
        resultado = {
            'existe': False,
            'mensagem': '',
            'duplicado_por': None
        }
        
        # Verificar por RA (mais preciso)
        if ra:
            query = {'dados_pessoais.ra': ra}
            if num_inscricao_ignore:
                query['num_inscricao'] = {'$ne': num_inscricao_ignore}
            
            aluno_ra = db.alunos.find_one(query)
            if aluno_ra:
                resultado['existe'] = True
                resultado['mensagem'] = f'Já existe um aluno cadastrado com o RA: {ra} (Aluno: {aluno_ra["dados_pessoais"]["nome"]})'
                resultado['duplicado_por'] = 'ra'
                print(f"   ⚠️ Duplicidade encontrada por RA")
                return jsonify(resultado)
        
        # Verificar por nome (case-insensitive)
        if nome:
            query = {
                'dados_pessoais.nome': {'$regex': f'^{re.escape(nome)}$', '$options': 'i'}
            }
            if num_inscricao_ignore:
                query['num_inscricao'] = {'$ne': num_inscricao_ignore}
            
            aluno_nome = db.alunos.find_one(query)
            if aluno_nome:
                resultado['existe'] = True
                resultado['mensagem'] = f'Já existe um aluno cadastrado com o nome: {nome} (RA: {aluno_nome["dados_pessoais"].get("ra", "N/A")})'
                resultado['duplicado_por'] = 'nome'
                print(f"   ⚠️ Duplicidade encontrada por nome")
                return jsonify(resultado)
        
        print(f"   ✅ Nenhuma duplicidade encontrada")
        return jsonify(resultado)
        
    except Exception as e:
        print(f"❌ Erro ao verificar duplicidade: {e}")
        traceback.print_exc()
        return jsonify({
            'existe': False, 
            'mensagem': 'Erro ao verificar duplicidade',
            'erro': str(e)
        }), 500


# ============================================
# ENDPOINTS PARA GRIDFS (UPLOAD DIRETO DE FOTOS)
# ============================================

@alunos_bp.route('/api/upload-arquivo', methods=['POST'])
def upload_arquivo():
    """Endpoint para upload direto de foto para GridFS"""
    try:
        print("\n📤 UPLOAD DIRETO PARA GRIDFS (FOTO)")
        
        campo = request.form.get('campo')
        if not campo:
            return jsonify({'sucesso': False, 'erro': 'Campo não informado'}), 400
        
        if 'arquivo' not in request.files:
            return jsonify({'sucesso': False, 'erro': 'Nenhum arquivo enviado'}), 400
        
        file = request.files['arquivo']
        if not file or not file.filename:
            return jsonify({'sucesso': False, 'erro': 'Arquivo inválido'}), 400
        
        # 🔥 VALIDAÇÃO: SÓ ACEITA IMAGENS
        if not file.content_type.startswith('image/'):
            return jsonify({
                'sucesso': False, 
                'erro': 'Apenas imagens são permitidas (JPG, PNG, etc)'
            }), 400
        
        # Verifica tamanho (máx 5MB para fotos)
        file.seek(0, os.SEEK_END)
        tamanho = file.tell()
        file.seek(0)
        
        if tamanho > 5 * 1024 * 1024:
            return jsonify({
                'sucesso': False, 
                'erro': 'Imagem muito grande (máx 5MB)'
            }), 400
        
        from database.mongo import salvar_arquivo_gridfs
        
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
    """Visualiza uma foto salva no GridFS"""
    try:
        from database.mongo import get_arquivo_gridfs
        
        arquivo = get_arquivo_gridfs(file_id)
        
        if not arquivo:
            return jsonify({'erro': 'Arquivo não encontrado'}), 404
        
        metadata = arquivo.metadata or {}
        content_type = metadata.get('content_type', 'image/jpeg')
        
        # Determina o content type baseado na extensão
        if arquivo.filename:
            ext = arquivo.filename.rsplit('.', 1)[-1].lower() if '.' in arquivo.filename else ''
            if ext in ['jpg', 'jpeg']:
                content_type = 'image/jpeg'
            elif ext == 'png':
                content_type = 'image/png'
            elif ext == 'gif':
                content_type = 'image/gif'
        
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
# ROTA PARA VISUALIZAR FOTOS (usada pelo frontend)
# ============================================

@alunos_bp.route('/api/alunos/arquivo/<file_id>', methods=['GET'])
def visualizar_arquivo_aluno(file_id):
    """Visualiza uma foto salva no GridFS pelo ID (usado pelo frontend)"""
    try:
        from database.mongo import get_arquivo_gridfs
        
        print(f"🔍 Buscando foto: {file_id}")
        
        arquivo = get_arquivo_gridfs(file_id)
        
        if not arquivo:
            print(f"❌ Foto não encontrada: {file_id}")
            return jsonify({'erro': 'Arquivo não encontrado'}), 404
        
        # Determina o content type baseado na extensão
        ext = arquivo.filename.rsplit('.', 1)[-1].lower() if '.' in arquivo.filename else ''
        if ext in ['jpg', 'jpeg']:
            mime_type = 'image/jpeg'
        elif ext == 'png':
            mime_type = 'image/png'
        elif ext == 'gif':
            mime_type = 'image/gif'
        else:
            mime_type = 'image/jpeg'  # fallback
        
        print(f"✅ Foto encontrada: {arquivo.filename} - Tipo: {mime_type}")
        
        return send_file(
            BytesIO(arquivo.read()),
            mimetype=mime_type,
            as_attachment=False,
            download_name=arquivo.filename
        )
        
    except Exception as e:
        print(f"❌ Erro ao visualizar foto: {e}")
        traceback.print_exc()
        return jsonify({'erro': str(e)}), 500


# ============================================
# ROTAS DE VISUALIZAÇÃO DE TERMOS COM SUPORTE AO RESPONSÁVEL SELECIONADO
# ============================================

@alunos_bp.route('/visualizar/termo/matricula/<num_inscricao>')
def visualizar_termo_matricula(num_inscricao):
    """Visualiza termo de matrícula"""
    try:
        from database.mongo import db
        
        aluno = db.alunos.find_one({'num_inscricao': num_inscricao})
        
        if not aluno:
            abort(404, description="Aluno não encontrado")
        
        if '_id' in aluno:
            aluno['_id'] = str(aluno['_id'])
        
        # Dados da unidade
        unidade = {
            'nome': 'CEIC El Shadday',
            'tipo': 'CEIC - Centro de Educação Infantil',
            'cnpj': '03.067.526/0001-87',
            'INEP': '35195340',
            'endereco': 'Rua Francisco Vilani Bicudo, 470',
            'bairro': 'Vila Nova Aparecida',
            'cidade': 'Mogi das Cruzes',
            'uf': 'SP',
            'cep': '08830-340',
            'telefone': '(11) 4739-3549',
            'email': 'contato@crecheelshadday.com.br'
        }
        
        data_atual = datetime.now().strftime('%d/%m/%Y')
        
        return render_template('componentes/termo_matricula.html',
                             aluno=aluno,
                             unidade=unidade,
                             data_atual=data_atual)
    except Exception as e:
        print(f"❌ Erro ao visualizar termo matrícula: {e}")
        abort(500)


@alunos_bp.route('/visualizar/termo/imagem/<num_inscricao>')
def visualizar_termo_imagem(num_inscricao):
    """Visualiza termo de autorização de imagem com suporte ao responsável selecionado"""
    try:
        from database.mongo import db
        
        aluno = db.alunos.find_one({'num_inscricao': num_inscricao})
        
        if not aluno:
            abort(404, description="Aluno não encontrado")
        
        if '_id' in aluno:
            aluno['_id'] = str(aluno['_id'])
        
        # PEGA OS PARÂMETROS DO RESPONSÁVEL SELECIONADO
        responsavel_nome = request.args.get('responsavel_nome', '')
        responsavel_parentesco = request.args.get('responsavel_parentesco', '')
        responsavel_rg = request.args.get('responsavel_rg', '')
        responsavel_cpf = request.args.get('responsavel_cpf', '')
        responsavel_telefone = request.args.get('responsavel_telefone', '')
        
        # Cria objeto dados_impressao com o responsável selecionado
        dados_impressao = {
            'responsavel_nome': responsavel_nome,
            'responsavel_parentesco': responsavel_parentesco,
            'responsavel_rg': responsavel_rg,
            'responsavel_cpf': responsavel_cpf,
            'responsavel_telefone': responsavel_telefone,
            'nome': aluno.get('dados_pessoais', {}).get('nome', ''),
            'data_nasc': aluno.get('dados_pessoais', {}).get('data_nasc', ''),
            'turma': aluno.get('turma', {}).get('turma', ''),
            'unidade': aluno.get('turma', {}).get('unidade', ''),
            'endereco': aluno.get('endereco', {}).get('logradouro', ''),
            'numero': aluno.get('endereco', {}).get('numero', ''),
            'bairro': aluno.get('endereco', {}).get('bairro', ''),
            'cidade': aluno.get('endereco', {}).get('cidade', ''),
            'uf': aluno.get('endereco', {}).get('uf', ''),
            'cep': aluno.get('endereco', {}).get('cep', ''),
            'sexo': aluno.get('dados_pessoais', {}).get('sexo', '')
        }
        
        # Dados da unidade
        unidade = {
            'nome': 'CEIC El Shadday',
            'tipo': 'CEIC - Centro de Educação Infantil',
            'cnpj': '03.067.526/0001-87',
            'INEP': '35195340',
            'endereco': 'Rua Francisco Vilani Bicudo, 470',
            'bairro': 'Vila Nova Aparecida',
            'cidade': 'Mogi das Cruzes',
            'uf': 'SP',
            'cep': '08830-340',
            'telefone': '(11) 4739-3549',
            'email': 'contato@crecheelshadday.com.br'
        }
        
        data_atual = datetime.now().strftime('%d/%m/%Y')
        
        return render_template('componentes/autorizacao_imagem.html',
                             aluno=aluno,
                             unidade=unidade,
                             data_atual=data_atual,
                             dados_impressao=dados_impressao)
    except Exception as e:
        print(f"❌ Erro ao visualizar termo imagem: {e}")
        traceback.print_exc()
        abort(500)


@alunos_bp.route('/visualizar/termo/regulamento/<num_inscricao>')
def visualizar_termo_regulamento(num_inscricao):
    """Visualiza termo de regulamento com suporte ao responsável selecionado"""
    try:
        from database.mongo import db
        
        aluno = db.alunos.find_one({'num_inscricao': num_inscricao})
        
        if not aluno:
            abort(404, description="Aluno não encontrado")
        
        if '_id' in aluno:
            aluno['_id'] = str(aluno['_id'])
        
        # PEGA OS PARÂMETROS DO RESPONSÁVEL SELECIONADO
        responsavel_nome = request.args.get('responsavel_nome', '')
        responsavel_parentesco = request.args.get('responsavel_parentesco', '')
        responsavel_rg = request.args.get('responsavel_rg', '')
        responsavel_cpf = request.args.get('responsavel_cpf', '')
        responsavel_telefone = request.args.get('responsavel_telefone', '')
        
        dados_impressao = {
            'responsavel_nome': responsavel_nome,
            'responsavel_parentesco': responsavel_parentesco,
            'responsavel_rg': responsavel_rg,
            'responsavel_cpf': responsavel_cpf,
            'responsavel_telefone': responsavel_telefone,
            'nome': aluno.get('dados_pessoais', {}).get('nome', ''),
            'data_nasc': aluno.get('dados_pessoais', {}).get('data_nasc', ''),
            'turma': aluno.get('turma', {}).get('turma', ''),
            'unidade': aluno.get('turma', {}).get('unidade', '')
        }
        
        unidade = {
            'nome': 'CEIC El Shadday',
            'tipo': 'CEIC - Centro de Educação Infantil',
            'cnpj': '03.067.526/0001-87',
            'INEP': '35195340'
        }
        
        data_atual = datetime.now().strftime('%d/%m/%Y')
        
        return render_template('componentes/regulamento.html',
                             aluno=aluno,
                             unidade=unidade,
                             data_atual=data_atual,
                             dados_impressao=dados_impressao)
    except Exception as e:
        print(f"❌ Erro ao visualizar termo regulamento: {e}")
        abort(500)


@alunos_bp.route('/visualizar/termo/saude/<num_inscricao>')
def visualizar_termo_saude(num_inscricao):
    """Visualiza termo de saúde com suporte ao responsável selecionado"""
    try:
        from database.mongo import db
        
        aluno = db.alunos.find_one({'num_inscricao': num_inscricao})
        
        if not aluno:
            abort(404, description="Aluno não encontrado")
        
        if '_id' in aluno:
            aluno['_id'] = str(aluno['_id'])
        
        # PEGA OS PARÂMETROS DO RESPONSÁVEL SELECIONADO
        responsavel_nome = request.args.get('responsavel_nome', '')
        responsavel_parentesco = request.args.get('responsavel_parentesco', '')
        responsavel_rg = request.args.get('responsavel_rg', '')
        responsavel_cpf = request.args.get('responsavel_cpf', '')
        responsavel_telefone = request.args.get('responsavel_telefone', '')
        
        dados_impressao = {
            'responsavel_nome': responsavel_nome,
            'responsavel_parentesco': responsavel_parentesco,
            'responsavel_rg': responsavel_rg,
            'responsavel_cpf': responsavel_cpf,
            'responsavel_telefone': responsavel_telefone,
            'nome': aluno.get('dados_pessoais', {}).get('nome', ''),
            'data_nasc': aluno.get('dados_pessoais', {}).get('data_nasc', ''),
            'turma': aluno.get('turma', {}).get('turma', ''),
            'unidade': aluno.get('turma', {}).get('unidade', '')
        }
        
        unidade = {
            'nome': 'CEIC El Shadday',
            'tipo': 'CEIC - Centro de Educação Infantil',
            'cnpj': '03.067.526/0001-87',
            'INEP': '35195340'
        }
        
        data_atual = datetime.now().strftime('%d/%m/%Y')
        
        return render_template('componentes/termo_saude.html',
                             aluno=aluno,
                             unidade=unidade,
                             data_atual=data_atual,
                             dados_impressao=dados_impressao)
    except Exception as e:
        print(f"❌ Erro ao visualizar termo saúde: {e}")
        abort(500)


@alunos_bp.route('/visualizar/termo/transporte/<num_inscricao>')
def visualizar_termo_transporte(num_inscricao):
    """Visualiza termo de transporte com suporte ao responsável selecionado"""
    try:
        from database.mongo import db
        
        aluno = db.alunos.find_one({'num_inscricao': num_inscricao})
        
        if not aluno:
            abort(404, description="Aluno não encontrado")
        
        if '_id' in aluno:
            aluno['_id'] = str(aluno['_id'])
        
        # PEGA OS PARÂMETROS DO RESPONSÁVEL SELECIONADO
        responsavel_nome = request.args.get('responsavel_nome', '')
        responsavel_parentesco = request.args.get('responsavel_parentesco', '')
        responsavel_rg = request.args.get('responsavel_rg', '')
        responsavel_cpf = request.args.get('responsavel_cpf', '')
        responsavel_telefone = request.args.get('responsavel_telefone', '')
        
        dados_impressao = {
            'responsavel_nome': responsavel_nome,
            'responsavel_parentesco': responsavel_parentesco,
            'responsavel_rg': responsavel_rg,
            'responsavel_cpf': responsavel_cpf,
            'responsavel_telefone': responsavel_telefone,
            'nome': aluno.get('dados_pessoais', {}).get('nome', ''),
            'data_nasc': aluno.get('dados_pessoais', {}).get('data_nasc', ''),
            'turma': aluno.get('turma', {}).get('turma', ''),
            'unidade': aluno.get('turma', {}).get('unidade', '')
        }
        
        unidade = {
            'nome': 'CEIC El Shadday',
            'tipo': 'CEIC - Centro de Educação Infantil',
            'cnpj': '03.067.526/0001-87',
            'INEP': '35195340'
        }
        
        data_atual = datetime.now().strftime('%d/%m/%Y')
        
        return render_template('componentes/termo_transporte.html',
                             aluno=aluno,
                             unidade=unidade,
                             data_atual=data_atual,
                             dados_impressao=dados_impressao)
    except Exception as e:
        print(f"❌ Erro ao visualizar termo transporte: {e}")
        abort(500)


@alunos_bp.route('/visualizar/termo/terceiro/<num_inscricao>')
def visualizar_termo_terceiro(num_inscricao):
    """Visualiza termo de terceiro autorizado"""
    try:
        from database.mongo import db
        
        aluno = db.alunos.find_one({'num_inscricao': num_inscricao})
        
        if not aluno:
            abort(404, description="Aluno não encontrado")
        
        if '_id' in aluno:
            aluno['_id'] = str(aluno['_id'])
        
        terceiro_num = request.args.get('terceiro', '1')
        terceiro_idx = int(terceiro_num) - 1
        
        terceiro = aluno.get('terceiros', [])[terceiro_idx] if aluno.get('terceiros') and terceiro_idx < len(aluno.get('terceiros', [])) else None
        
        unidade = {
            'nome': 'CEIC El Shadday',
            'tipo': 'CEIC - Centro de Educação Infantil',
            'cnpj': '03.067.526/0001-87',
            'INEP': '35195340'
        }
        
        data_atual = datetime.now().strftime('%d/%m/%Y')
        
        return render_template('componentes/termo_terceiro.html',
                             aluno=aluno,
                             terceiro=terceiro,
                             unidade=unidade,
                             data_atual=data_atual)
    except Exception as e:
        print(f"❌ Erro ao visualizar termo terceiro: {e}")
        abort(500)


# ============================================
# ENDPOINT DE CADASTRO VIA JSON - COM VERIFICAÇÃO DE DUPLICIDADE
# ============================================

@alunos_bp.route('/api/alunos/cadastrar-json', methods=['POST'])
def cadastrar_aluno_json():
    """Endpoint para cadastrar um novo aluno (recebe JSON com IDs das fotos do GridFS)"""
    try:
        print("\n" + "="*60)
        print("📥 RECEBENDO REQUISIÇÃO DE CADASTRO (JSON - GRIDFS)")
        print("="*60)
        
        dados = request.get_json()
        
        if not dados:
            return jsonify({'sucesso': False, 'erro': 'Dados não enviados'}), 400
        
        arquivos_ids = dados.pop('arquivos_ids', {})
        
        # LOG PARA VERIFICAR FOTOS RECEBIDAS
        print(f"📎 FOTOS IDs RECEBIDOS:")
        for key, value in arquivos_ids.items():
            print(f"   - {key}: {value}")
        
        print(f"📦 Dados recebidos:")
        print(f"   📝 Campos de texto: {len(dados)}")
        print(f"   📎 IDs das fotos: {len(arquivos_ids)}")
        
        # ===== VALIDAÇÃO DE DUPLICIDADE =====
        nome = dados.get('nome', '').strip()
        ra = dados.get('ra', '').strip()
        
        from database.mongo import db
        from database.mongo import verificar_duplicidade_aluno
        
        verificacao = verificar_duplicidade_aluno(nome=nome, ra=ra)
        
        if verificacao['existe']:
            print(f"   ❌ {verificacao['mensagem']}")
            return jsonify({
                'sucesso': False,
                'erro': verificacao['mensagem']
            }), 400
        
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
            'terceiros': [],
            'arquivos_ids': arquivos_ids,
            'usando_gridfs': True
        }
        
        # ===== PROCESSA RESPONSÁVEIS =====
        responsaveis_lista = []
        
        if dados.get('responsaveis') and isinstance(dados['responsaveis'], list):
            responsaveis_lista = dados['responsaveis']
            print(f"   ✅ Usando array responsaveis: {len(responsaveis_lista)} responsáveis")
        else:
            # Responsável principal
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
            if responsavel_principal['nome']:
                responsaveis_lista.append(responsavel_principal)
            
            # Responsáveis adicionais (2 a 5)
            for i in range(2, 6):
                nome = dados.get(f'responsavel{i}_nome', '')
                if nome and nome.strip():
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
                    responsaveis_lista.append(resp_adicional)
        
        aluno['responsaveis'] = responsaveis_lista
        print(f"   📌 Total de responsáveis: {len(responsaveis_lista)}")
        
        # ===== PROCESSA TERCEIROS =====
        terceiros_lista = []
        
        if dados.get('terceiros') and isinstance(dados['terceiros'], list):
            for idx, terc in enumerate(dados['terceiros']):
                numero = idx + 1
                rg_file_id = arquivos_ids.get(f'terceiro{numero}_rg', '')
                
                terceiros_lista.append({
                    'nome': terc.get('nome', ''),
                    'telefone': terc.get('telefone', ''),
                    'cpf': terc.get('cpf', ''),
                    'rg': terc.get('rg', ''),
                    'email': terc.get('email', ''),
                    'rg_file_id': rg_file_id
                })
                print(f"   ✅ Terceiro {numero}: {terc.get('nome')}")
        else:
            for i in range(1, 11):
                nome_terceiro = dados.get(f'terceiro{i}_nome', '')
                if nome_terceiro and nome_terceiro.strip():
                    rg_key = f'terceiro{i}_rg'
                    rg_file_id = arquivos_ids.get(rg_key, '')
                    
                    terceiros_lista.append({
                        'nome': nome_terceiro,
                        'telefone': dados.get(f'terceiro{i}_telefone', ''),
                        'cpf': dados.get(f'terceiro{i}_cpf', ''),
                        'rg': dados.get(f'terceiro{i}_rg', ''),
                        'email': dados.get(f'terceiro{i}_email', ''),
                        'rg_file_id': rg_file_id
                    })
                    print(f"   ✅ Terceiro {i}: {nome_terceiro}")
        
        if terceiros_lista:
            aluno['terceiros'] = terceiros_lista
            print(f"   📌 Total de terceiros: {len(terceiros_lista)}")
        
        # ===== PROCESSA TRANSPORTE =====
        if dados.get('utiliza_transporte') == '1' or dados.get('utiliza_transporte') == True:
            transporte_rg_file_id = arquivos_ids.get('transporte_rg', '')
            
            if dados.get('transporte') and isinstance(dados['transporte'], dict):
                aluno['transporte'] = {
                    'nome': dados['transporte'].get('nome', ''),
                    'cnpj': dados['transporte'].get('cnpj', ''),
                    'cpf': dados['transporte'].get('cpf', ''),
                    'rg': dados['transporte'].get('rg', ''),
                    'telefone': dados['transporte'].get('telefone', ''),
                    'email': dados['transporte'].get('email', ''),
                    'rg_file_id': dados['transporte'].get('rg_file_id', transporte_rg_file_id)
                }
                print(f"   ✅ Transporte: {aluno['transporte'].get('nome')}")
            else:
                aluno['transporte'] = {
                    'nome': dados.get('transporte_nome', ''),
                    'cnpj': dados.get('transporte_cnpj', ''),
                    'cpf': dados.get('transporte_cpf', ''),
                    'rg': dados.get('transporte_rg', ''),
                    'telefone': dados.get('transporte_telefone', ''),
                    'email': dados.get('transporte_email', ''),
                    'rg_file_id': transporte_rg_file_id
                }
                print(f"   ✅ Transporte: {aluno['transporte']['nome']}")
        
        # ===== RESUMO FINAL =====
        print(f"\n📊 RESUMO DO CADASTRO:")
        print(f"   👤 Responsáveis: {len(aluno['responsaveis'])}")
        print(f"   👥 Terceiros: {len(aluno.get('terceiros', []))}")
        print(f"   🚍 Transporte: {'Sim' if aluno.get('transporte') else 'Não'}")
        print(f"   📎 Fotos IDs: {len(arquivos_ids)}")
        
        # Salva no banco
        result = db.alunos.insert_one(aluno)
        
        print(f"\n✅ Cadastro realizado! Nº: {num_inscricao}")
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
# ENDPOINT DE ATUALIZAÇÃO DE ALUNO COM VERIFICAÇÃO
# ============================================

@alunos_bp.route('/api/alunos/atualizar', methods=['POST', 'PUT'])
def atualizar_aluno():
    """Endpoint para atualizar um aluno existente"""
    try:
        print("\n" + "="*60)
        print("📝 RECEBENDO REQUISIÇÃO DE ATUALIZAÇÃO")
        print("="*60)
        
        num_inscricao_original = None
        arquivos_ids = {}
        
        if request.is_json:
            dados = request.get_json()
            num_inscricao_original = dados.get('num_inscricao_original') or dados.get('num_inscricao')
            arquivos_ids = dados.get('arquivos_ids', {})
            print(f"📌 JSON recebido")
            dados_dict = dados
        else:
            dados_dict = {}
            for key, value in request.form.items():
                dados_dict[key] = value
            
            num_inscricao_original = dados_dict.get('num_inscricao_original')
            arquivos_ids_json = dados_dict.get('arquivos_ids', '{}')
            try:
                arquivos_ids = json.loads(arquivos_ids_json) if arquivos_ids_json else {}
            except:
                arquivos_ids = {}
            print(f"📌 FormData recebido e convertido para dict")
        
        dados = dados_dict
        
        print(f"📌 Número de inscrição original: {num_inscricao_original}")
        
        if not num_inscricao_original:
            return jsonify({'sucesso': False, 'erro': 'Número de inscrição não fornecido'}), 400
        
        from database.mongo import db
        from database.mongo import verificar_duplicidade_aluno
        from datetime import datetime
        
        aluno_existente = db.alunos.find_one({'num_inscricao': num_inscricao_original})
        
        if not aluno_existente:
            print(f"❌ Aluno não encontrado: {num_inscricao_original}")
            return jsonify({'sucesso': False, 'erro': 'Aluno não encontrado'}), 404
        
        # ===== VALIDAÇÃO DE DUPLICIDADE NA ATUALIZAÇÃO =====
        nome = dados.get('nome', '').strip()
        ra = dados.get('ra', '').strip()
        
        verificacao = verificar_duplicidade_aluno(nome=nome, ra=ra, num_inscricao_ignore=num_inscricao_original)
        
        if verificacao['existe']:
            print(f"   ❌ {verificacao['mensagem']}")
            return jsonify({
                'sucesso': False,
                'erro': verificacao['mensagem']
            }), 400
        
        print(f"📌 Atualizando aluno: {aluno_existente['dados_pessoais']['nome']}")
        
        # ===== PROCESSA RESPONSÁVEIS =====
        responsaveis = []
        
        if dados.get('responsaveis') and isinstance(dados.get('responsaveis'), list):
            responsaveis = dados.get('responsaveis')
            print(f"   ✅ Usando array responsaveis na atualização")
        else:
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
            if responsavel_principal['nome']:
                responsaveis.append(responsavel_principal)
            
            for i in range(2, 6):
                nome = dados.get(f'responsavel{i}_nome', '')
                if nome and nome.strip():
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
                    responsaveis.append(resp_adicional)
        
        # ===== PROCESSA TERCEIROS =====
        terceiros = []
        
        if dados.get('terceiros') and isinstance(dados.get('terceiros'), list):
            for idx, terc in enumerate(dados.get('terceiros')):
                numero = idx + 1
                terceiros.append({
                    'nome': terc.get('nome', ''),
                    'telefone': terc.get('telefone', ''),
                    'cpf': terc.get('cpf', ''),
                    'rg': terc.get('rg', ''),
                    'email': terc.get('email', ''),
                    'rg_file_id': arquivos_ids.get(f'terceiro{numero}_rg', terc.get('rg_file_id', ''))
                })
                print(f"   ✅ Terceiro {numero}: {terc.get('nome')}")
        else:
            for i in range(1, 11):
                nome_terceiro = dados.get(f'terceiro{i}_nome', '')
                if nome_terceiro and nome_terceiro.strip():
                    rg_key = f'terceiro{i}_rg'
                    terceiros.append({
                        'nome': nome_terceiro,
                        'telefone': dados.get(f'terceiro{i}_telefone', ''),
                        'cpf': dados.get(f'terceiro{i}_cpf', ''),
                        'rg': dados.get(f'terceiro{i}_rg', ''),
                        'email': dados.get(f'terceiro{i}_email', ''),
                        'rg_file_id': arquivos_ids.get(rg_key, '')
                    })
                    print(f"   ✅ Terceiro {i}: {nome_terceiro}")
        
        # ===== PREPARA OS DADOS ATUALIZADOS =====
        dados_atualizados = {
            'data_atualizacao': datetime.now(),
            'dados_pessoais': {
                'nome': dados.get('nome', aluno_existente['dados_pessoais'].get('nome', '')),
                'data_nasc': dados.get('data_nasc', aluno_existente['dados_pessoais'].get('data_nasc', '')),
                'sexo': dados.get('sexo', aluno_existente['dados_pessoais'].get('sexo', '')),
                'raca': dados.get('raca', aluno_existente['dados_pessoais'].get('raca', '')),
                'naturalidade': dados.get('naturalidade', aluno_existente['dados_pessoais'].get('naturalidade', '')),
                'nacionalidade': dados.get('nacionalidade', aluno_existente['dados_pessoais'].get('nacionalidade', 'Brasileira')),
                'ra': dados.get('ra', aluno_existente['dados_pessoais'].get('ra', ''))
            },
            'endereco': {
                'cep': dados.get('cep', aluno_existente['endereco'].get('cep', '')),
                'logradouro': dados.get('endereco', aluno_existente['endereco'].get('logradouro', '')),
                'numero': dados.get('numero', aluno_existente['endereco'].get('numero', '')),
                'complemento': dados.get('complemento', aluno_existente['endereco'].get('complemento', '')),
                'bairro': dados.get('bairro', aluno_existente['endereco'].get('bairro', '')),
                'cidade': dados.get('cidade', aluno_existente['endereco'].get('cidade', '')),
                'uf': dados.get('uf', aluno_existente['endereco'].get('uf', ''))
            },
            'turma': {
                'unidade': dados.get('unidade', aluno_existente['turma'].get('unidade', '')),
                'turma': dados.get('turma', aluno_existente['turma'].get('turma', '')),
                'periodo': dados.get('periodo', aluno_existente['turma'].get('periodo', '')),
                'ano_letivo': dados.get('ano_letivo', aluno_existente['turma'].get('ano_letivo', '2026'))
            },
            'saude': {
                'tipo_sanguineo': dados.get('tipo_sanguineo', aluno_existente['saude'].get('tipo_sanguineo', '')),
                'plano_saude': dados.get('plano_saude', aluno_existente['saude'].get('plano_saude', '')),
                'alergias': dados.get('alergias', aluno_existente['saude'].get('alergias', '')),
                'medicamentos': dados.get('medicamentos', aluno_existente['saude'].get('medicamentos', '')),
                'restricoes': dados.get('restricoes', aluno_existente['saude'].get('restricoes', '')),
                'pediatra': dados.get('pediatra', aluno_existente['saude'].get('pediatra', '')),
                'contato_pediatra': dados.get('contato_pediatra', aluno_existente['saude'].get('contato_pediatra', '')),
                'deficiencia': dados.get('deficiencia', aluno_existente['saude'].get('deficiencia', 'nao')),
                'deficiencia_desc': dados.get('deficiencia_desc', aluno_existente['saude'].get('deficiencia_desc', ''))
            },
            'responsaveis': responsaveis,
            'terceiros': terceiros if terceiros else aluno_existente.get('terceiros', []),
            'arquivos_ids': arquivos_ids if arquivos_ids else aluno_existente.get('arquivos_ids', {}),
            'usando_gridfs': True
        }
        
        # ===== PROCESSAMENTO DO TRANSPORTE =====
        if dados.get('utiliza_transporte') == '1' or dados.get('utiliza_transporte') == True:
            transporte_rg_file_id = arquivos_ids.get('transporte_rg', '')
            
            if dados.get('transporte') and isinstance(dados.get('transporte'), dict):
                dados_atualizados['transporte'] = {
                    'nome': dados['transporte'].get('nome', ''),
                    'cnpj': dados['transporte'].get('cnpj', ''),
                    'cpf': dados['transporte'].get('cpf', ''),
                    'rg': dados['transporte'].get('rg', ''),
                    'telefone': dados['transporte'].get('telefone', ''),
                    'email': dados['transporte'].get('email', ''),
                    'rg_file_id': dados['transporte'].get('rg_file_id', transporte_rg_file_id)
                }
                print(f"   ✅ Transporte atualizado: {dados_atualizados['transporte'].get('nome')}")
            else:
                dados_atualizados['transporte'] = {
                    'nome': dados.get('transporte_nome', ''),
                    'cnpj': dados.get('transporte_cnpj', ''),
                    'cpf': dados.get('transporte_cpf', ''),
                    'rg': dados.get('transporte_rg', ''),
                    'telefone': dados.get('transporte_telefone', ''),
                    'email': dados.get('transporte_email', ''),
                    'rg_file_id': transporte_rg_file_id
                }
                print(f"   ✅ Transporte atualizado: {dados_atualizados['transporte'].get('nome')}")
        elif 'transporte' in dados_atualizados:
            dados_atualizados['transporte'] = None
        
        # Remove campos que não devem ser atualizados
        dados_atualizados.pop('num_inscricao', None)
        dados_atualizados.pop('data_cadastro', None)
        
        # Atualiza no banco
        result = db.alunos.update_one(
            {'num_inscricao': num_inscricao_original},
            {'$set': dados_atualizados}
        )
        
        print(f"\n✅ Atualização realizada! Documentos modificados: {result.modified_count}")
        print("="*60)
        
        return jsonify({
            'sucesso': True,
            'mensagem': 'Aluno atualizado com sucesso!',
            'num_inscricao': num_inscricao_original
        })
        
    except Exception as e:
        print(f"\n❌ ERRO NA ATUALIZAÇÃO: {str(e)}")
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# ============================================
# ENDPOINTS BÁSICOS (LISTAGEM, BUSCA, EDIÇÃO, EXCLUSÃO)
# ============================================

@alunos_bp.route('/api/alunos', methods=['GET'])
def listar_alunos():
    """Lista todos os alunos"""
    try:
        from database.mongo import db
        
        alunos = list(db.alunos.find({}, {'_id': 1, 'num_inscricao': 1, 'dados_pessoais.nome': 1, 'dados_pessoais.ra': 1, 'status': 1, 'data_cadastro': 1}))
        
        for aluno in alunos:
            aluno['_id'] = str(aluno['_id'])
        
        return jsonify({
            'sucesso': True,
            'alunos': alunos
        })
        
    except Exception as e:
        print(f"❌ Erro ao listar alunos: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@alunos_bp.route('/api/alunos/<num_inscricao>', methods=['GET'])
def buscar_aluno(num_inscricao):
    """Busca um aluno pelo número de inscrição"""
    try:
        from database.mongo import db
        
        aluno = db.alunos.find_one({'num_inscricao': num_inscricao})
        
        if not aluno:
            return jsonify({'sucesso': False, 'erro': 'Aluno não encontrado'}), 404
        
        aluno['_id'] = str(aluno['_id'])
        
        return jsonify({
            'sucesso': True,
            'aluno': aluno
        })
        
    except Exception as e:
        print(f"❌ Erro ao buscar aluno: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@alunos_bp.route('/api/alunos/excluir/<num_inscricao>', methods=['DELETE'])
def excluir_aluno_route(num_inscricao):
    """Exclui um aluno (soft delete)"""
    try:
        from database.mongo import db
        
        result = db.alunos.update_one(
            {'num_inscricao': num_inscricao},
            {'$set': {'status': 'inativo', 'data_exclusao': datetime.now()}}
        )
        
        if result.modified_count == 0:
            return jsonify({'sucesso': False, 'erro': 'Aluno não encontrado'}), 404
        
        return jsonify({
            'sucesso': True,
            'mensagem': 'Aluno desativado com sucesso!'
        })
        
    except Exception as e:
        print(f"❌ Erro ao excluir aluno: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@alunos_bp.route('/api/alunos/buscar', methods=['GET'])
def buscar_alunos_query():
    """Endpoint para buscar alunos com filtros"""
    try:
        nome = request.args.get('nome', '')
        num_inscricao = request.args.get('num_inscricao', '')
        turma = request.args.get('turma', '')
        unidade = request.args.get('unidade', '')
        
        print(f"\n🔍 Buscando alunos com filtros: nome='{nome}', inscrição='{num_inscricao}', turma='{turma}', unidade='{unidade}'")
        
        from database.mongo import db
        
        filtro = {}
        if nome:
            filtro['dados_pessoais.nome'] = {'$regex': nome, '$options': 'i'}
        if num_inscricao:
            filtro['num_inscricao'] = {'$regex': num_inscricao, '$options': 'i'}
        if turma:
            filtro['turma.turma'] = turma
        if unidade:
            filtro['turma.unidade'] = unidade
        
        alunos = list(db.alunos.find(filtro).sort('dados_pessoais.nome', 1))
        
        for aluno in alunos:
            if '_id' in aluno:
                aluno['_id'] = str(aluno['_id'])
            if aluno.get('data_cadastro'):
                if hasattr(aluno['data_cadastro'], 'strftime'):
                    aluno['data_cadastro'] = aluno['data_cadastro'].strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"✅ Encontrados {len(alunos)} alunos")
        
        return jsonify({
            'sucesso': True,
            'alunos': alunos
        })
        
    except Exception as e:
        print(f"❌ Erro na busca: {str(e)}")
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


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


@alunos_bp.route('/api/alunos/<id>', methods=['GET'])
def get_aluno(id):
    """Retorna dados de um aluno específico"""
    try:
        from database.mongo import db
        from bson import ObjectId
        
        aluno = db.alunos.find_one({'_id': ObjectId(id)})
        if aluno:
            if '_id' in aluno:
                aluno['_id'] = str(aluno['_id'])
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
        from database.mongo import db
        
        aluno = db.alunos.find_one({'num_inscricao': num_inscricao})
        if aluno:
            if '_id' in aluno:
                aluno['_id'] = str(aluno['_id'])
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


@alunos_bp.route('/api/alunos/excluir', methods=['POST', 'DELETE'])
def excluir_aluno_endpoint():
    """Endpoint para excluir um aluno"""
    try:
        print("\n" + "="*60)
        print("🗑️ RECEBENDO REQUISIÇÃO DE EXCLUSÃO")
        print("="*60)
        
        if request.is_json:
            dados = request.get_json()
            num_inscricao = dados.get('num_inscricao') if dados else None
        else:
            num_inscricao = request.form.get('num_inscricao')
        
        print(f"📌 Número de inscrição: {num_inscricao}")
        
        if not num_inscricao:
            print("❌ Número de inscrição não fornecido")
            return jsonify({'sucesso': False, 'erro': 'Número de inscrição não fornecido'}), 400
        
        from database.mongo import db
        
        aluno = db.alunos.find_one({'num_inscricao': num_inscricao})
        
        if not aluno:
            print(f"❌ Aluno não encontrado: {num_inscricao}")
            return jsonify({'sucesso': False, 'erro': 'Aluno não encontrado'}), 404
        
        print(f"✅ Aluno encontrado: {aluno['dados_pessoais']['nome']}")
        
        resultado = db.alunos.delete_one({'num_inscricao': num_inscricao})
        
        if resultado.deleted_count == 0:
            print(f"❌ Falha ao excluir aluno: {num_inscricao}")
            return jsonify({'sucesso': False, 'erro': 'Falha ao excluir aluno'}), 500
        
        print(f"✅ Aluno excluído com sucesso: {num_inscricao}")
        print("="*60)
        
        return jsonify({
            'sucesso': True,
            'mensagem': 'Aluno excluído com sucesso!',
            'num_inscricao': num_inscricao
        })
        
    except Exception as e:
        print(f"\n❌ ERRO NA EXCLUSÃO: {str(e)}")
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@alunos_bp.route('/api/alunos/estatisticas', methods=['GET'])
def estatisticas():
    """Retorna estatísticas gerais"""
    try:
        from database.mongo import db
        
        alunos = list(db.alunos.find({}))
        
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
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# ============================================
# ROTAS DE RENDERIZAÇÃO
# ============================================

@alunos_bp.route('/cadastro')
def cadastro_aluno():
    """Renderiza a página de cadastro de alunos"""
    return render_template('cadastro_aluno.html')


@alunos_bp.route('/')
def index():
    """Página inicial"""
    return render_template('index.html')