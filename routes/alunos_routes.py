from flask import Blueprint, request, jsonify, render_template, send_file, redirect
from services.aluno_service import AlunoService
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import uuid
import traceback
import sys
import base64
import json
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
    IS_VERCEL = os.environ.get('VERCEL') == '1' or os.environ.get('NOW') is not None
    
    if IS_VERCEL:
        info_db = save_uploaded_file_to_db(file, campo)
        if info_db:
            return info_db
        print(f"   ⚠️ Falha ao salvar no MongoDB: {campo}")
        return None
    
    info_db = save_uploaded_file_to_db(file, campo)
    if info_db:
        return info_db
    
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
# ENDPOINTS PARA GRIDFS (UPLOAD DIRETO)
# ============================================

@alunos_bp.route('/api/upload-arquivo', methods=['POST'])
def upload_arquivo():
    """Endpoint para upload direto de arquivo para GridFS"""
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
        
        metadata = arquivo.metadata or {}
        content_type = metadata.get('content_type', 'application/octet-stream')
        
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
# ENDPOINT DE CADASTRO VIA JSON - CORRIGIDO
# ============================================

@alunos_bp.route('/api/alunos/cadastrar-json', methods=['POST'])
def cadastrar_aluno_json():
    """Endpoint para cadastrar um novo aluno (recebe JSON com IDs dos arquivos do GridFS)"""
    try:
        print("\n" + "="*60)
        print("📥 RECEBENDO REQUISIÇÃO DE CADASTRO (JSON - GRIDFS)")
        print("="*60)
        
        dados = request.get_json()
        
        if not dados:
            return jsonify({'sucesso': False, 'erro': 'Dados não enviados'}), 400
        
        arquivos_ids = dados.pop('arquivos_ids', {})
        
        print(f"📦 Dados recebidos:")
        print(f"   📝 Campos de texto: {len(dados)}")
        print(f"   📎 IDs de arquivos: {len(arquivos_ids)}")
        
        # ===== VERIFICA SE OS DADOS VIERAM COMO ARRAY =====
        print(f"\n🔍 VERIFICANDO ARRAYS:")
        print(f"   responsaveis array: {'SIM' if dados.get('responsaveis') else 'NÃO'}")
        print(f"   terceiros array: {'SIM' if dados.get('terceiros') else 'NÃO'}")
        
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
            'arquivos_ids': arquivos_ids,
            'usando_gridfs': True
        }
        
        # ===== PROCESSA RESPONSÁVEIS - ACEITA AMBOS OS FORMATOS =====
        responsaveis_lista = []
        
        # FORMATO 1: Array 'responsaveis' (enviado pelo frontend)
        if dados.get('responsaveis') and isinstance(dados['responsaveis'], list):
            responsaveis_lista = dados['responsaveis']
            print(f"   ✅ Usando array responsaveis: {len(responsaveis_lista)} responsáveis")
            for resp in responsaveis_lista:
                print(f"      - {resp.get('tipo', 'desconhecido')}: {resp.get('nome', 'sem nome')}")
        
        # FORMATO 2: Campos individuais (fallback)
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
                print(f"   ✅ Responsável principal: {responsavel_principal['nome']}")
            
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
                    print(f"   ✅ Responsável adicional {i}: {nome}")
        
        aluno['responsaveis'] = responsaveis_lista
        print(f"   📌 Total de responsáveis: {len(responsaveis_lista)}")
        
        # ===== PROCESSA TERCEIROS - ACEITA AMBOS OS FORMATOS =====
        terceiros_lista = []
        
        # FORMATO 1: Array 'terceiros' (enviado pelo frontend)
        if dados.get('terceiros') and isinstance(dados['terceiros'], list):
            terceiros_lista = dados['terceiros']
            print(f"   ✅ Usando array terceiros: {len(terceiros_lista)} terceiros")
            for terc in terceiros_lista:
                print(f"      - {terc.get('nome', 'sem nome')}")
        
        # FORMATO 2: Campos individuais (fallback)
        else:
            for i in range(1, 4):
                nome = dados.get(f'terceiro{i}_nome', '')
                if nome and nome.strip():
                    terceiro = {
                        'nome': nome,
                        'telefone': dados.get(f'terceiro{i}_telefone', ''),
                        'cpf': dados.get(f'terceiro{i}_cpf', ''),
                        'rg': dados.get(f'terceiro{i}_rg', ''),
                        'email': dados.get(f'terceiro{i}_email', '')
                    }
                    terceiros_lista.append(terceiro)
                    print(f"   ✅ Terceiro {i}: {nome}")
        
        if terceiros_lista:
            aluno['terceiros'] = terceiros_lista
            print(f"   📌 Total de terceiros: {len(terceiros_lista)}")
        
        # ===== PROCESSA TRANSPORTE - ACEITA AMBOS OS FORMATOS =====
        if dados.get('utiliza_transporte') == '1':
            # FORMATO 1: Objeto 'transporte' (enviado pelo frontend)
            if dados.get('transporte') and isinstance(dados['transporte'], dict):
                aluno['transporte'] = dados['transporte']
                print(f"   ✅ Transporte (objeto): {aluno['transporte'].get('nome', 'sem nome')}")
            # FORMATO 2: Campos individuais (fallback)
            else:
                aluno['transporte'] = {
                    'nome': dados.get('transporte_nome', ''),
                    'cnpj': dados.get('transporte_cnpj', ''),
                    'cpf': dados.get('transporte_cpf', ''),
                    'rg': dados.get('transporte_rg', ''),
                    'telefone': dados.get('transporte_telefone', ''),
                    'email': dados.get('transporte_email', '')
                }
                print(f"   ✅ Transporte: {aluno['transporte']['nome']}")
        
        # ===== RESUMO FINAL =====
        print(f"\n📊 RESUMO DO CADASTRO:")
        print(f"   👤 Responsáveis: {len(aluno['responsaveis'])}")
        for resp in aluno['responsaveis']:
            print(f"      - {resp.get('tipo', 'desconhecido')}: {resp.get('nome', 'sem nome')}")
        print(f"   👥 Terceiros: {len(aluno.get('terceiros', []))}")
        for terc in aluno.get('terceiros', []):
            print(f"      - {terc.get('nome', 'sem nome')}")
        print(f"   🚍 Transporte: {'Sim' if aluno.get('transporte') else 'Não'}")
        if aluno.get('transporte'):
            print(f"      - {aluno['transporte'].get('nome', 'sem nome')}")
        print(f"   📎 Arquivos IDs: {len(arquivos_ids)}")
        
        # Salva no banco
        result = db.alunos.insert_one(aluno)
        
        print(f"\n✅ Cadastro realizado! Nº: {num_inscricao}")
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
# ENDPOINT DE ATUALIZAÇÃO DE ALUNO
# ============================================

@alunos_bp.route('/api/alunos/atualizar', methods=['POST', 'PUT'])
def atualizar_aluno():
    """Endpoint para atualizar um aluno existente"""
    try:
        print("\n" + "="*60)
        print("📝 RECEBENDO REQUISIÇÃO DE ATUALIZAÇÃO")
        print("="*60)
        
        if request.is_json:
            dados = request.get_json()
            num_inscricao_original = dados.get('num_inscricao_original') or dados.get('num_inscricao')
            arquivos_ids = dados.get('arquivos_ids', {})
            print(f"📌 JSON recebido")
        else:
            dados = request.form
            num_inscricao_original = dados.get('num_inscricao_original')
            arquivos_ids_json = dados.get('arquivos_ids', '{}')
            try:
                arquivos_ids = json.loads(arquivos_ids_json) if arquivos_ids_json else {}
            except:
                arquivos_ids = {}
            print(f"📌 FormData recebido")
        
        print(f"📌 Número de inscrição original: {num_inscricao_original}")
        
        if not num_inscricao_original:
            return jsonify({'sucesso': False, 'erro': 'Número de inscrição não fornecido'}), 400
        
        from database.mongo import db
        from datetime import datetime
        
        aluno_existente = db.alunos.find_one({'num_inscricao': num_inscricao_original})
        
        if not aluno_existente:
            print(f"❌ Aluno não encontrado: {num_inscricao_original}")
            return jsonify({'sucesso': False, 'erro': 'Aluno não encontrado'}), 404
        
        print(f"📌 Atualizando aluno: {aluno_existente['dados_pessoais']['nome']}")
        
        # ===== PROCESSA RESPONSÁVEIS - ACEITA AMBOS OS FORMATOS =====
        responsaveis = []
        
        # Verifica se veio como array
        if dados.get('responsaveis') and isinstance(dados.get('responsaveis'), list):
            responsaveis = dados.get('responsaveis')
            print(f"   ✅ Usando array responsaveis na atualização")
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
                responsaveis.append(responsavel_principal)
                print(f"   ✅ Responsável principal: {responsavel_principal['nome']}")
            
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
                    responsaveis.append(resp_adicional)
                    print(f"   ✅ Responsável adicional {i}: {nome}")
        
        # ===== PROCESSA TERCEIROS - ACEITA AMBOS OS FORMATOS =====
        terceiros = []
        
        if dados.get('terceiros') and isinstance(dados.get('terceiros'), list):
            terceiros = dados.get('terceiros')
            print(f"   ✅ Usando array terceiros na atualização")
        else:
            for i in range(1, 4):
                nome = dados.get(f'terceiro{i}_nome', '')
                if nome and nome.strip():
                    terceiro = {
                        'nome': nome,
                        'telefone': dados.get(f'terceiro{i}_telefone', ''),
                        'cpf': dados.get(f'terceiro{i}_cpf', ''),
                        'rg': dados.get(f'terceiro{i}_rg', ''),
                        'email': dados.get(f'terceiro{i}_email', '')
                    }
                    terceiros.append(terceiro)
                    print(f"   ✅ Terceiro {i}: {nome}")
        
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
            'arquivos_ids': arquivos_ids if arquivos_ids else aluno_existente.get('arquivos_ids', {}),
            'usando_gridfs': True
        }
        
        if terceiros:
            dados_atualizados['terceiros'] = terceiros
        elif 'terceiros' in aluno_existente:
            dados_atualizados['terceiros'] = []
        
        if dados.get('utiliza_transporte') == '1':
            if dados.get('transporte') and isinstance(dados.get('transporte'), dict):
                dados_atualizados['transporte'] = dados.get('transporte')
            else:
                dados_atualizados['transporte'] = {
                    'nome': dados.get('transporte_nome', ''),
                    'cnpj': dados.get('transporte_cnpj', ''),
                    'cpf': dados.get('transporte_cpf', ''),
                    'rg': dados.get('transporte_rg', ''),
                    'telefone': dados.get('transporte_telefone', ''),
                    'email': dados.get('transporte_email', '')
                }
            print(f"   ✅ Transporte: {dados_atualizados['transporte']['nome']}")
        elif 'transporte' in aluno_existente:
            dados_atualizados['transporte'] = None
        
        print(f"\n📊 RESUMO DA ATUALIZAÇÃO:")
        print(f"   👤 Responsáveis: {len(responsaveis)}")
        print(f"   👥 Terceiros: {len(terceiros)}")
        print(f"   🚍 Transporte: {'Sim' if dados_atualizados.get('transporte') else 'Não'}")
        print(f"   📎 Arquivos IDs: {len(arquivos_ids)}")
        
        resultado = db.alunos.update_one(
            {'num_inscricao': num_inscricao_original},
            {'$set': dados_atualizados}
        )
        
        if resultado.matched_count == 0:
            print(f"❌ Aluno não encontrado: {num_inscricao_original}")
            return jsonify({'sucesso': False, 'erro': 'Aluno não encontrado'}), 404
        
        print(f"✅ Aluno atualizado! Nº: {num_inscricao_original}")
        print("="*60)
        
        return jsonify({
            'sucesso': True,
            'mensagem': 'Aluno atualizado com sucesso!',
            'num_inscricao': num_inscricao_original
        })
        
    except Exception as e:
        print(f"\n❌ ERRO NA ATUALIZAÇÃO: {str(e)}")
        import traceback
        traceback.print_exc()
        print("="*60)
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


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
        aluno = aluno_service.get_aluno_by_inscricao(num_inscricao)
        if not aluno:
            return jsonify({'erro': 'Aluno não encontrado'}), 404
        
        if aluno.get('usando_gridfs') and aluno.get('arquivos_ids', {}).get(campo):
            file_id = aluno['arquivos_ids'][campo]
            return redirect(f'/api/alunos/arquivo/{file_id}')
        
        arquivo = None
        for arq in aluno.get('arquivos', []):
            if arq.get('campo') == campo:
                arquivo = arq
                break
        
        if not arquivo:
            return jsonify({'erro': 'Arquivo não encontrado'}), 404
        
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
# ENDPOINTS PARA BUSCA E LISTAGEM
# ============================================

@alunos_bp.route('/api/alunos/buscar', methods=['GET'])
def buscar_alunos():
    """Endpoint para buscar alunos"""
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
        
        alunos = list(db.alunos.find(filtro).sort('data_cadastro', -1))
        
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
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


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


# ============================================
# ENDPOINT PARA EXCLUIR ALUNO
# ============================================

@alunos_bp.route('/api/alunos/excluir', methods=['POST', 'DELETE'])
def excluir_aluno():
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
            return jsonify({
                'sucesso': False, 
                'erro': 'Número de inscrição não fornecido'
            }), 400
        
        from database.mongo import db
        
        aluno = db.alunos.find_one({'num_inscricao': num_inscricao})
        
        if not aluno:
            print(f"❌ Aluno não encontrado: {num_inscricao}")
            return jsonify({
                'sucesso': False,
                'erro': 'Aluno não encontrado'
            }), 404
        
        print(f"✅ Aluno encontrado: {aluno['dados_pessoais']['nome']}")
        
        resultado = db.alunos.delete_one({'num_inscricao': num_inscricao})
        
        if resultado.deleted_count == 0:
            print(f"❌ Falha ao excluir aluno: {num_inscricao}")
            return jsonify({
                'sucesso': False,
                'erro': 'Falha ao excluir aluno'
            }), 500
        
        print(f"✅ Aluno excluído com sucesso: {num_inscricao}")
        print("="*60)
        
        return jsonify({
            'sucesso': True,
            'mensagem': 'Aluno excluído com sucesso!',
            'num_inscricao': num_inscricao
        })
        
    except Exception as e:
        print(f"\n❌ ERRO NA EXCLUSÃO: {str(e)}")
        import traceback
        traceback.print_exc()
        print("="*60)
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


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
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500