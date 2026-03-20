from flask import Blueprint, request, jsonify, render_template
from services.aluno_service import AlunoService
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import uuid
import traceback
import sys

alunos_bp = Blueprint('alunos', __name__)
aluno_service = AlunoService()

# Detecta se está no Vercel
IS_VERCEL = os.environ.get('VERCEL') == '1' or os.environ.get('NOW') is not None

# Configurações de upload - usa /tmp no Vercel
if IS_VERCEL:
    UPLOAD_FOLDER = '/tmp/uploads'
    print("📁 Modo Vercel - usando /tmp/uploads")
else:
    UPLOAD_FOLDER = 'uploads'
    print("📁 Modo local - usando uploads/")

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file, subfolder, campo):
    """Salva um arquivo enviado e retorna informações"""
    if file and allowed_file(file.filename):
        # Gera nome único
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{timestamp}_{unique_id}_{campo}.{ext}"
        
        # Caminho completo
        upload_path = os.path.join(UPLOAD_FOLDER, subfolder)
        
        # Tenta criar a pasta, se falhar no Vercel, usa /tmp direto
        try:
            os.makedirs(upload_path, exist_ok=True)
        except Exception as e:
            print(f"⚠️ Não foi possível criar {upload_path}: {e}")
            if IS_VERCEL:
                upload_path = '/tmp'
                print(f"📁 Usando fallback: {upload_path}")
        
        filepath = os.path.join(upload_path, filename)
        
        try:
            # Salva arquivo
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

@alunos_bp.route('/api/alunos/proximo-numero', methods=['GET'])
def proximo_numero():
    """Retorna o próximo número de inscrição"""
    try:
        print("🔍 Buscando próximo número de inscrição...")
        num_inscricao = aluno_service.get_proximo_numero_inscricao()
        print(f"✅ Número gerado: {num_inscricao}")
        return jsonify({
            'sucesso': True,
            'numero': num_inscricao
        })
    except Exception as e:
        print(f"❌ Erro ao gerar número: {str(e)}")
        traceback.print_exc()
        
        # Fallback: busca direto no MongoDB
        try:
            from database.mongo import db
            ano = datetime.now().year
            ultimo_aluno = db.alunos.find_one(
                {'num_inscricao': {'$regex': f'-{ano}$'}},
                sort=[('num_inscricao', -1)]
            )
            if ultimo_aluno and ultimo_aluno.get('num_inscricao'):
                partes = ultimo_aluno['num_inscricao'].split('-')
                valor = int(partes[0]) + 1
                numero = f"{str(valor).zfill(3)}-{ano}"
                print(f"📌 Fallback: próximo número: {numero}")
                return jsonify({
                    'sucesso': True,
                    'numero': numero
                })
        except Exception as e2:
            print(f"Fallback também falhou: {e2}")
        
        # Último recurso
        from datetime import datetime
        numero_temp = f"001-{datetime.now().year}"
        print(f"📌 Usando número temporário: {numero_temp}")
        return jsonify({
            'sucesso': True,
            'numero': numero_temp
        })

@alunos_bp.route('/api/alunos/cadastrar', methods=['POST'])
def cadastrar_aluno():
    """Endpoint para cadastrar um novo aluno"""
    try:
        print("\n" + "="*60)
        print("📥 RECEBENDO REQUISIÇÃO DE CADASTRO")
        print("="*60)
        
        # ===== LOG DETALHADO DOS ARQUIVOS RECEBIDOS =====
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
        # ================================================
        
        # Processa os arquivos enviados
        arquivos_salvos = []
        
        # ===== PRIORIDADE MÁXIMA: FOTOS =====
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
                    print(f"\n📸 Salvando FOTO: {campo} -> pasta '{pasta}'")
                    print(f"   Nome original: {file.filename}")
                    # Não ler tamanho completo para não consumir memória
                    file.seek(0, 2)  # vai para o fim
                    size = file.tell()
                    file.seek(0)
                    print(f"   Tamanho: {size} bytes")
                    
                    info = save_uploaded_file(file, pasta, campo)
                    if info:
                        arquivos_salvos.append(info)
                        print(f"   ✅ FOTO salva: {info['nome']} ({info['tamanho']} bytes)")
                else:
                    print(f"   ⚠️ Campo {campo} presente mas sem arquivo válido")
            else:
                print(f"   ❌ Campo {campo} não encontrado no request")
        
        # ===== DOCUMENTOS =====
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
                    print(f"\n📄 Salvando DOCUMENTO: {campo} -> pasta '{pasta}'")
                    print(f"   Nome original: {file.filename}")
                    file.seek(0, 2)
                    size = file.tell()
                    file.seek(0)
                    print(f"   Tamanho: {size} bytes")
                    
                    info = save_uploaded_file(file, pasta, campo)
                    if info:
                        arquivos_salvos.append(info)
                        print(f"   ✅ Documento salvo: {info['nome']} ({info['tamanho']} bytes)")
        
        # ===== RESUMO FINAL =====
        print("\n" + "="*60)
        print(f"📦 RESUMO DO CADASTRO:")
        print(f"   Total de arquivos recebidos: {len(arquivos_recebidos)}")
        print(f"   Total de arquivos salvos: {len(arquivos_salvos)}")
        
        if arquivos_salvos:
            print("\n   📁 Arquivos salvos:")
            for arq in arquivos_salvos:
                print(f"      - {arq['campo']}: {arq['nome']} ({arq['tamanho']} bytes)")
        
        # Salva no banco de dados
        print("\n💾 Salvando dados no banco...")
        resultado = aluno_service.salvar_aluno(request.form, arquivos_salvos)
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
        print("📸 Processando substituição de fotos...")
        
        # ===== LOG DETALHADO DOS ARQUIVOS RECEBIDOS =====
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
        # ================================================
        
        # Processa os arquivos enviados (apenas os novos)
        arquivos_salvos = []
        
        # ===== PRIORIDADE MÁXIMA: FOTOS =====
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
                    print(f"\n📸 Salvando FOTO: {campo} -> pasta '{pasta}'")
                    print(f"   Nome original: {file.filename}")
                    file.seek(0, 2)
                    size = file.tell()
                    file.seek(0)
                    print(f"   Tamanho: {size} bytes")
                    
                    info = save_uploaded_file(file, pasta, campo)
                    if info:
                        arquivos_salvos.append(info)
                        print(f"   ✅ FOTO salva: {info['nome']} ({info['tamanho']} bytes)")
                else:
                    print(f"   ⚠️ Campo {campo} presente mas sem arquivo válido")
            else:
                print(f"   ❌ Campo {campo} não encontrado no request")
        
        # ===== DOCUMENTOS =====
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
                    print(f"\n📄 Salvando DOCUMENTO: {campo} -> pasta '{pasta}'")
                    print(f"   Nome original: {file.filename}")
                    file.seek(0, 2)
                    size = file.tell()
                    file.seek(0)
                    print(f"   Tamanho: {size} bytes")
                    
                    info = save_uploaded_file(file, pasta, campo)
                    if info:
                        arquivos_salvos.append(info)
                        print(f"   ✅ Documento salvo: {info['nome']} ({info['tamanho']} bytes)")
        
        # ===== RESUMO FINAL =====
        print("\n" + "="*60)
        print(f"📦 RESUMO DA ATUALIZAÇÃO:")
        print(f"   Total de arquivos recebidos: {len(arquivos_recebidos)}")
        print(f"   Total de novos arquivos salvos: {len(arquivos_salvos)}")
        
        if arquivos_salvos:
            print("\n   📁 Novos arquivos salvos:")
            for arq in arquivos_salvos:
                print(f"      - {arq['campo']}: {arq['nome']} ({arq['tamanho']} bytes)")
        
        # Atualiza no banco de dados
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
        
        # Pega os dados do JSON
        dados = request.get_json()
        num_inscricao = dados.get('num_inscricao')
        
        if not num_inscricao:
            return jsonify({
                'sucesso': False, 
                'erro': 'Número de inscrição não fornecido'
            }), 400
        
        print(f"📌 Excluindo aluno: {num_inscricao}")
        
        # Busca o aluno antes de excluir (para pegar os arquivos)
        aluno = aluno_service.get_aluno_by_inscricao(num_inscricao)
        
        if not aluno:
            return jsonify({
                'sucesso': False,
                'erro': 'Aluno não encontrado'
            }), 404
        
        # Exclui os arquivos físicos (fotos e documentos)
        if aluno.get('arquivos'):
            arquivos_excluidos = 0
            for arquivo in aluno['arquivos']:
                try:
                    # Converte o caminho da URL para caminho do sistema
                    caminho_relativo = arquivo['caminho'].lstrip('/')
                    if IS_VERCEL:
                        caminho_completo = os.path.join('/tmp', caminho_relativo.replace('uploads/', '', 1))
                    else:
                        caminho_completo = os.path.join(UPLOAD_FOLDER, caminho_relativo.replace('uploads/', '', 1))
                    
                    if os.path.exists(caminho_completo):
                        os.remove(caminho_completo)
                        arquivos_excluidos += 1
                        print(f"   ✅ Arquivo excluído: {caminho_completo}")
                except Exception as e:
                    print(f"   ⚠️ Erro ao excluir arquivo: {e}")
            
            print(f"   📦 Total de arquivos excluídos: {arquivos_excluidos}")
        
        # Exclui do banco de dados
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

# ===== ROTA PARA PÁGINA DE CADASTRO COM EDIÇÃO =====
@alunos_bp.route('/alunos/cadastro')
def cadastro_aluno():
    """Rota para página de cadastro com suporte a edição"""
    try:
        num_inscricao = request.args.get('editar')
        aluno_data = None
        
        if num_inscricao:
            print(f"📝 Modo edição - buscando aluno: {num_inscricao}")
            # Busca o aluno no banco de dados pelo número de inscrição
            aluno = aluno_service.get_aluno_by_inscricao(num_inscricao)
            if aluno:
                aluno_data = aluno
                print(f"✅ Aluno encontrado: {aluno_data['dados_pessoais']['nome']}")
            else:
                print(f"❌ Aluno não encontrado: {num_inscricao}")
        
        return render_template('alunos/cadastro_aluno.html', aluno=aluno_data)
        
    except Exception as e:
        print(f"❌ Erro ao carregar página de cadastro: {str(e)}")
        return render_template('alunos/cadastro_aluno.html', aluno=None)

@alunos_bp.route('/api/alunos/buscar', methods=['GET'])
def buscar_alunos():
    """Endpoint para buscar alunos"""
    try:
        # Pega parâmetros de busca
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
        
        # Conta turmas únicas
        turmas = set()
        for aluno in alunos:
            if aluno.get('turma', {}).get('turma'):
                turmas.add(aluno['turma']['turma'])
        
        # Conta responsáveis
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