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
    """Salva um arquivo enviado (fallback para sistema de arquivos)"""
    # Tenta salvar no MongoDB primeiro (para Vercel)
    info_db = save_uploaded_file_to_db(file, campo)
    if info_db:
        return info_db
    
    # Fallback: salva no sistema de arquivos (local)
    if file and allowed_file(file.filename):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{timestamp}_{unique_id}_{campo}.{ext}"
        
        upload_path = os.path.join('uploads', subfolder)
        try:
            os.makedirs(upload_path, exist_ok=True)
        except Exception as e:
            print(f"⚠️ Não foi possível criar {upload_path}: {e}")
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

@alunos_bp.route('/api/visualizar/<campo>/<num_inscricao>', methods=['GET'])
def visualizar_arquivo(campo, num_inscricao):
    """Visualiza um arquivo salvo no MongoDB (Base64)"""
    try:
        # Busca o aluno
        aluno = aluno_service.get_aluno_by_inscricao(num_inscricao)
        if not aluno:
            return jsonify({'erro': 'Aluno não encontrado'}), 404
        
        # Busca o arquivo pelo campo
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
            
            # Define o tipo MIME corretamente
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
        
        # Fallback para caminho
        if arquivo.get('caminho'):
            return redirect(arquivo['caminho'])
        
        return jsonify({'erro': 'Arquivo não encontrado'}), 404
        
    except Exception as e:
        print(f"❌ Erro ao visualizar arquivo: {e}")
        traceback.print_exc()
        return jsonify({'erro': str(e)}), 500

@alunos_bp.route('/api/alunos/proximo-numero', methods=['GET'])
def proximo_numero():
    """Retorna o próximo número de inscrição APENAS PARA VISUALIZAÇÃO (não incrementa o contador)"""
    try:
        print("🔍 Buscando próximo número de inscrição (pré-visualização)...")
        from database.mongo import db
        from datetime import datetime
        
        ano = datetime.now().year
        
        # Busca o último aluno cadastrado no ano
        ultimo_aluno = db.alunos.find_one(
            {'num_inscricao': {'$regex': f'-{ano}$'}},
            sort=[('num_inscricao', -1)]
        )
        
        if ultimo_aluno and ultimo_aluno.get('num_inscricao'):
            partes = ultimo_aluno['num_inscricao'].split('-')
            valor = int(partes[0]) + 1
            numero = f"{str(valor).zfill(3)}-{ano}"
        else:
            # Primeiro aluno do ano
            numero = f"001-{ano}"
        
        print(f"📌 Próximo número (pré-visualização): {numero}")
        
        return jsonify({
            'sucesso': True,
            'numero': numero,
            'preview': True  # Indica que é apenas pré-visualização
        })
        
    except Exception as e:
        print(f"❌ Erro ao buscar próximo número: {str(e)}")
        traceback.print_exc()
        
        # Fallback
        from datetime import datetime
        numero_temp = f"001-{datetime.now().year}"
        return jsonify({
            'sucesso': True,
            'numero': numero_temp,
            'preview': True
        })


def _gerar_novo_numero_inscricao(db, ano):
    """Função auxiliar para gerar um novo número de inscrição de forma atômica (APENAS NO SALVAMENTO)"""
    try:
        # Usa atomic operation para incrementar o contador
        contador = db.contadores.find_one_and_update(
            {'nome': 'num_inscricao', 'ano': ano},
            {'$inc': {'valor': 1}},
            upsert=True,
            return_document=True
        )
        
        # Se o contador foi criado agora, valor inicial é 1
        valor_atual = contador.get('valor', 1)
        numero = f"{str(valor_atual).zfill(3)}-{ano}"
        
        print(f"   📌 Contador atualizado: {valor_atual} -> {numero}")
        return numero
        
    except Exception as e:
        print(f"   ⚠️ Erro ao atualizar contador: {e}")
        # Fallback: busca o último número
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
# NOVO ENDPOINT 1: CRIAR RASCUNHO DO ALUNO
# ============================================
@alunos_bp.route('/api/alunos/criar-esboco', methods=['POST'])
def criar_esboco_aluno():
    """
    ETAPA 1: Cria um rascunho do aluno apenas com dados textuais
    Retorna um ID temporário para anexar os documentos depois
    """
    try:
        print("\n" + "="*60)
        print("📝 ETAPA 1: CRIANDO RASCUNHO DO ALUNO")
        print("="*60)
        
        from database.mongo import db
        from datetime import datetime
        
        print("\n📦 DADOS RECEBIDOS:")
        for key, value in request.form.items():
            print(f"   📝 {key}: {value[:50] if value else 'vazio'}")
        
        # Gera número de inscrição
        ano = datetime.now().year
        num_inscricao = request.form.get('num_inscricao')
        
        if not num_inscricao:
            # Gera um número para o rascunho
            num_inscricao = _gerar_novo_numero_inscricao(db, ano)
            print(f"🆕 Número gerado: {num_inscricao}")
        else:
            print(f"📌 Número fornecido: {num_inscricao}")
        
        # Prepara os dados do aluno (apenas textuais, sem arquivos)
        dados_aluno = {
            'num_inscricao': num_inscricao,
            'status': 'rascunho',
            'criado_em': datetime.now(),
            'ultima_atualizacao': datetime.now(),
            'arquivos': [],
            'upload_completo': False,
            'dados_pessoais': {
                'nome': request.form.get('nome', ''),
                'data_nasc': request.form.get('data_nasc', ''),
                'sexo': request.form.get('sexo', ''),
                'raca': request.form.get('raca', ''),
                'naturalidade': request.form.get('naturalidade', ''),
                'nacionalidade': request.form.get('nacionalidade', 'Brasileira'),
                'ra': request.form.get('ra', '')
            },
            'endereco': {
                'cep': request.form.get('cep', ''),
                'logradouro': request.form.get('endereco', ''),
                'numero': request.form.get('numero', ''),
                'complemento': request.form.get('complemento', ''),
                'bairro': request.form.get('bairro', ''),
                'cidade': request.form.get('cidade', ''),
                'uf': request.form.get('uf', '')
            },
            'turma': {
                'unidade': request.form.get('unidade', ''),
                'turma': request.form.get('turma', ''),
                'periodo': request.form.get('periodo', ''),
                'ano_letivo': request.form.get('ano_letivo', '2026')
            },
            'saude': {
                'tipo_sanguineo': request.form.get('tipo_sanguineo', ''),
                'plano_saude': request.form.get('plano_saude', ''),
                'alergias': request.form.get('alergias', ''),
                'medicamentos': request.form.get('medicamentos', ''),
                'restricoes': request.form.get('restricoes', ''),
                'pediatra': request.form.get('pediatra', ''),
                'contato_pediatra': request.form.get('contato_pediatra', ''),
                'deficiencia': request.form.get('deficiencia', 'nao'),
                'deficiencia_desc': request.form.get('deficiencia_desc', '')
            },
            'responsaveis': []
        }
        
        # Processa responsável principal
        responsavel_principal = {
            'nome': request.form.get('responsavel1_nome', ''),
            'parentesco': request.form.get('responsavel1_parentesco', ''),
            'telefone': request.form.get('responsavel1_telefone', ''),
            'telefone_contato': request.form.get('responsavel1_telefone_contato', ''),
            'cpf': request.form.get('responsavel1_cpf', ''),
            'rg': request.form.get('responsavel1_rg', ''),
            'email': request.form.get('responsavel1_email', ''),
            'tipo': 'principal'
        }
        dados_aluno['responsaveis'].append(responsavel_principal)
        
        # Processa responsáveis adicionais
        for i in range(2, 6):
            nome = request.form.get(f'responsavel{i}_nome', '')
            if nome:
                resp_adicional = {
                    'nome': nome,
                    'parentesco': request.form.get(f'responsavel{i}_parentesco', ''),
                    'telefone': request.form.get(f'responsavel{i}_telefone', ''),
                    'telefone_contato': request.form.get(f'responsavel{i}_telefone_contato', ''),
                    'cpf': request.form.get(f'responsavel{i}_cpf', ''),
                    'rg': request.form.get(f'responsavel{i}_rg', ''),
                    'email': request.form.get(f'responsavel{i}_email', ''),
                    'tipo': 'adicional'
                }
                dados_aluno['responsaveis'].append(resp_adicional)
        
        # Processa terceiros
        terceiros = []
        for i in range(1, 4):
            nome = request.form.get(f'terceiro{i}_nome', '')
            if nome:
                terceiro = {
                    'nome': nome,
                    'telefone': request.form.get(f'terceiro{i}_telefone', ''),
                    'cpf': request.form.get(f'terceiro{i}_cpf', ''),
                    'rg': request.form.get(f'terceiro{i}_rg', ''),
                    'email': request.form.get(f'terceiro{i}_email', '')
                }
                terceiros.append(terceiro)
        
        if terceiros:
            dados_aluno['terceiros'] = terceiros
        
        # Processa transporte
        if request.form.get('utiliza_transporte') == '1':
            dados_aluno['transporte'] = {
                'nome': request.form.get('transporte_nome', ''),
                'cnpj': request.form.get('transporte_cnpj', ''),
                'cpf': request.form.get('transporte_cpf', ''),
                'rg': request.form.get('transporte_rg', ''),
                'telefone': request.form.get('transporte_telefone', ''),
                'email': request.form.get('transporte_email', '')
            }
        
        # Salva no banco
        result = db.alunos.insert_one(dados_aluno)
        aluno_id = str(result.inserted_id)
        
        print(f"✅ Rascunho criado com ID: {aluno_id}, Nº: {num_inscricao}")
        print("="*60)
        
        return jsonify({
            'sucesso': True,
            'id': aluno_id,
            'num_inscricao': num_inscricao,
            'mensagem': 'Rascunho criado com sucesso'
        })
        
    except Exception as e:
        print(f"\n❌ ERRO ao criar rascunho: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


# ============================================
# NOVO ENDPOINT 2: ANEXAR DOCUMENTOS EM LOTES
# ============================================
@alunos_bp.route('/api/alunos/anexar-documentos', methods=['POST'])
def anexar_documentos():
    """
    ETAPA 2: Anexa documentos em lotes ao rascunho do aluno
    Recebe id_aluno e os arquivos
    """
    try:
        print("\n" + "="*60)
        print("📎 ETAPA 2: ANEXANDO DOCUMENTOS EM LOTES")
        print("="*60)
        
        from database.mongo import db
        from bson import ObjectId
        from datetime import datetime
        
        id_aluno = request.form.get('id_aluno')
        num_inscricao = request.form.get('num_inscricao')
        
        if not id_aluno and not num_inscricao:
            return jsonify({
                'sucesso': False,
                'erro': 'ID do aluno ou número de inscrição é obrigatório'
            }), 400
        
        print(f"📌 Processando para aluno ID: {id_aluno}, Nº: {num_inscricao}")
        
        # Busca o aluno
        aluno = None
        if id_aluno:
            try:
                aluno = db.alunos.find_one({'_id': ObjectId(id_aluno)})
            except:
                pass
        
        if not aluno and num_inscricao:
            aluno = db.alunos.find_one({'num_inscricao': num_inscricao})
        
        if not aluno:
            return jsonify({
                'sucesso': False,
                'erro': 'Aluno não encontrado'
            }), 404
        
        print(f"✅ Aluno encontrado: {aluno.get('num_inscricao')}")
        
        # Processa os arquivos recebidos neste lote
        novos_arquivos = []
        
        for key in request.files.keys():
            file = request.files[key]
            if file and file.filename:
                print(f"\n📄 Processando arquivo: {key} - {file.filename}")
                
                # Salva o arquivo
                info = save_uploaded_file(file, 'documentos', key)
                if info:
                    novos_arquivos.append(info)
                    print(f"   ✅ Arquivo processado: {info['nome']} ({info['tamanho']} bytes)")
        
        if not novos_arquivos:
            print("⚠️ Nenhum arquivo recebido neste lote")
            return jsonify({
                'sucesso': True,
                'arquivos_recebidos': 0,
                'mensagem': 'Nenhum arquivo para anexar'
            })
        
        # Atualiza o aluno com os novos arquivos
        arquivos_existentes = aluno.get('arquivos', [])
        arquivos_atualizados = arquivos_existentes + novos_arquivos
        
        result = db.alunos.update_one(
            {'_id': aluno['_id']},
            {
                '$set': {
                    'arquivos': arquivos_atualizados,
                    'ultima_atualizacao': datetime.now()
                }
            }
        )
        
        print(f"✅ {len(novos_arquivos)} arquivos anexados com sucesso!")
        print(f"📊 Total de arquivos agora: {len(arquivos_atualizados)}")
        print("="*60)
        
        return jsonify({
            'sucesso': True,
            'arquivos_recebidos': len(novos_arquivos),
            'total_arquivos': len(arquivos_atualizados),
            'mensagem': f'{len(novos_arquivos)} arquivos anexados com sucesso'
        })
        
    except Exception as e:
        print(f"\n❌ ERRO ao anexar documentos: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


# ============================================
# NOVO ENDPOINT 3: FINALIZAR CADASTRO
# ============================================
@alunos_bp.route('/api/alunos/finalizar-cadastro', methods=['POST'])
def finalizar_cadastro():
    """
    ETAPA 3: Finaliza o cadastro, valida documentos e marca como ativo
    """
    try:
        print("\n" + "="*60)
        print("✅ ETAPA 3: FINALIZANDO CADASTRO")
        print("="*60)
        
        from database.mongo import db
        from bson import ObjectId
        from datetime import datetime
        
        id_aluno = request.form.get('id_aluno')
        num_inscricao = request.form.get('num_inscricao')
        finalizar = request.form.get('finalizar') == 'true'
        
        if not finalizar:
            return jsonify({
                'sucesso': False,
                'erro': 'Parâmetro finalizar é obrigatório'
            }), 400
        
        if not id_aluno and not num_inscricao:
            return jsonify({
                'sucesso': False,
                'erro': 'ID do aluno ou número de inscrição é obrigatório'
            }), 400
        
        # Busca o aluno
        aluno = None
        if id_aluno:
            try:
                aluno = db.alunos.find_one({'_id': ObjectId(id_aluno)})
            except:
                pass
        
        if not aluno and num_inscricao:
            aluno = db.alunos.find_one({'num_inscricao': num_inscricao})
        
        if not aluno:
            return jsonify({
                'sucesso': False,
                'erro': 'Aluno não encontrado'
            }), 404
        
        print(f"📌 Finalizando cadastro: {aluno.get('num_inscricao')}")
        
        # Valida documentos obrigatórios
        documentos_obrigatorios = [
            'aluno_certidao', 'aluno_rg', 'aluno_vacinacao',
            'resp_rg', 'resp_cpf', 'resp_comprovante'
        ]
        
        arquivos_existentes = [a.get('campo') for a in aluno.get('arquivos', [])]
        faltantes = [doc for doc in documentos_obrigatorios if doc not in arquivos_existentes]
        
        if faltantes:
            print(f"⚠️ Documentos faltantes: {faltantes}")
            return jsonify({
                'sucesso': False,
                'erro': f'Documentos obrigatórios faltantes: {", ".join(faltantes)}'
            }), 400
        
        # Verifica fotos obrigatórias
        fotos_obrigatorias = ['foto_aluno', 'foto_responsavel1']
        fotos_faltantes = [foto for foto in fotos_obrigatorias if foto not in arquivos_existentes]
        
        if fotos_faltantes:
            print(f"⚠️ Fotos faltantes: {fotos_faltantes}")
            return jsonify({
                'sucesso': False,
                'erro': f'Fotos obrigatórias faltantes: {", ".join(fotos_faltantes)}'
            }), 400
        
        # Se tiver terceiros, valida documentos deles
        if aluno.get('terceiros') and len(aluno['terceiros']) > 0:
            if 'terceiro_rg' not in arquivos_existentes:
                return jsonify({
                    'sucesso': False,
                    'erro': 'Documento do terceiro (RG) é obrigatório'
                }), 400
        
        # Se tiver transporte, valida documentos
        if aluno.get('transporte'):
            docs_transporte = ['transporte_rg', 'transporte_cpf', 'transporte_cnh']
            docs_faltantes = [doc for doc in docs_transporte if doc not in arquivos_existentes]
            if docs_faltantes:
                return jsonify({
                    'sucesso': False,
                    'erro': f'Documentos do transporte faltantes: {", ".join(docs_faltantes)}'
                }), 400
        
        # Atualiza status para ativo
        result = db.alunos.update_one(
            {'_id': aluno['_id']},
            {
                '$set': {
                    'status': 'ativo',
                    'finalizado_em': datetime.now(),
                    'data_cadastro': datetime.now(),
                    'upload_completo': True
                }
            }
        )
        
        print(f"✅ Cadastro finalizado com sucesso! Nº: {aluno['num_inscricao']}")
        print("="*60)
        
        return jsonify({
            'sucesso': True,
            'mensagem': 'Cadastro finalizado com sucesso!',
            'num_inscricao': aluno['num_inscricao'],
            'id': str(aluno['_id'])
        })
        
    except Exception as e:
        print(f"\n❌ ERRO ao finalizar cadastro: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@alunos_bp.route('/api/alunos/cadastrar', methods=['POST'])
def cadastrar_aluno():
    """Endpoint para cadastrar um novo aluno (método tradicional)"""
    try:
        print("\n" + "="*60)
        print("📥 RECEBENDO REQUISIÇÃO DE CADASTRO")
        print("="*60)
        
        print("\n🔍 ARQUIVOS RECEBIDOS NO REQUEST:")
        arquivos_recebidos = []
        for key in request.files.keys():
            file = request.files[key]
            if file and file.filename:
                arquivos_recebidos.append({
                    'campo': key,
                    'nome': file.filename,
                    'tipo': file.content_type
                })
                print(f"   📁 {key}: {file.filename} ({file.content_type})")
        
        print(f"\n📦 DADOS DO FORMULÁRIO:")
        for key, value in request.form.items():
            print(f"   📝 {key}: {value[:30] if value else 'vazio'}")
        
        # ===== GERAR NÚMERO DE INSCRIÇÃO DEFINITIVO APENAS NO SALVAMENTO =====
        from database.mongo import db
        from datetime import datetime
        
        ano = datetime.now().year
        
        # Verifica se o número já foi enviado pelo frontend
        num_inscricao_frontend = request.form.get('num_inscricao')
        
        # Se veio um número do frontend, verifica se é um novo cadastro ou edição
        if num_inscricao_frontend and num_inscricao_frontend != '':
            # Verifica se já existe um aluno com esse número
            aluno_existente = aluno_service.get_aluno_by_inscricao(num_inscricao_frontend)
            
            if aluno_existente:
                # É uma atualização, não gera novo número (não deveria cair aqui)
                num_inscricao = num_inscricao_frontend
                print(f"📝 Modo atualização - mantendo número: {num_inscricao}")
            else:
                # É um novo cadastro com número já gerado (pré-visualização)
                # Verifica se o número já está em uso (double-check)
                if aluno_service.get_aluno_by_inscricao(num_inscricao_frontend):
                    # Número já existe, precisa gerar outro
                    print(f"⚠️ Número {num_inscricao_frontend} já existe, gerando novo...")
                    num_inscricao = _gerar_novo_numero_inscricao(db, ano)
                else:
                    # Usa o número que veio do frontend
                    num_inscricao = num_inscricao_frontend
                    print(f"✅ Usando número pré-gerado: {num_inscricao}")
                    
                    # Atualiza o contador para refletir este número usado
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
            # Novo cadastro sem número, gera um novo
            num_inscricao = _gerar_novo_numero_inscricao(db, ano)
            print(f"🆕 Gerando novo número: {num_inscricao}")
        
        arquivos_salvos = []
        
        # ===== PROCESSANDO FOTOS =====
        print("\n📸 PROCESSANDO FOTOS...")
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
        
        # ===== PROCESSANDO DOCUMENTOS =====
        print("\n📄 PROCESSANDO DOCUMENTOS...")
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
        
        # Adiciona o número de inscrição definitivo aos dados do formulário
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
        
        # Buscar aluno existente para manter arquivos que não foram substituídos
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
        
        # Manter arquivos existentes que não foram substituídos
        if aluno_existente and aluno_existente.get('arquivos'):
            for arq in aluno_existente['arquivos']:
                campo = arq.get('campo')
                # Verifica se este campo foi enviado novamente no request
                if campo in request.files and request.files[campo] and request.files[campo].filename:
                    # Será substituído, não manter
                    print(f"   🔄 Campo {campo} será substituído")
                else:
                    # Manter arquivo existente
                    arquivos_salvos.append(arq)
                    print(f"   📌 Mantendo arquivo existente: {campo}")
        
        # ===== PROCESSANDO FOTOS =====
        print("\n📸 PROCESSANDO FOTOS...")
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
                        # Remover o arquivo antigo da lista se existir
                        arquivos_salvos = [a for a in arquivos_salvos if a.get('campo') != campo]
                        arquivos_salvos.append(info)
                        print(f"   ✅ Nova foto processada: {info['nome']}")
        
        # ===== PROCESSANDO DOCUMENTOS =====
        print("\n📄 PROCESSANDO DOCUMENTOS...")
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
                        # Remover o documento antigo da lista se existir
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


# ===== ROTA PARA PÁGINA DE CADASTRO COM EDIÇÃO - CORRIGIDA =====
@alunos_bp.route('/alunos/cadastro')
def cadastro_aluno():
    """Rota para página de cadastro com suporte a edição - CARREGA TODOS OS ARQUIVOS"""
    try:
        num_inscricao = request.args.get('editar')
        aluno_data = None
        
        if num_inscricao:
            print(f"📝 Modo edição - buscando aluno: {num_inscricao}")
            aluno = aluno_service.get_aluno_by_inscricao(num_inscricao)
            if aluno:
                # Converter ObjectId para string para JSON
                if '_id' in aluno:
                    aluno['_id'] = str(aluno['_id'])
                
                # Preparar os arquivos para exibição no formulário
                if aluno.get('arquivos'):
                    print(f"📁 Encontrados {len(aluno['arquivos'])} arquivos")
                    
                    # Criar um dicionário para fácil acesso no template
                    arquivos_dict = {}
                    for arquivo in aluno['arquivos']:
                        campo = arquivo.get('campo')
                        arquivos_dict[campo] = arquivo
                        
                        # Se for imagem, adicionar data_url para exibição
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
        
        # Converter imagens para base64 para exibição
        for aluno in alunos:
            if aluno.get('arquivos'):
                for arquivo in aluno['arquivos']:
                    if arquivo.get('dados'):
                        # Criar data_url para exibição
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