from flask import Flask, render_template, session, jsonify, request, abort
from flask_cors import CORS
import os
import logging
import sys
from dotenv import load_dotenv
from datetime import datetime, timedelta
from functools import wraps
import traceback

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Carrega variáveis de ambiente
load_dotenv()

# Importa as rotas
from routes.alunos_routes import alunos_bp
from routes.uploads_routes import uploads_bp
from routes.termos_routes import termos_bp
from routes.auth_routes import auth_bp
from routes.justificativa_routes import justificativa_bp
from routes.funcionarios_routes import funcionarios_bp

app = Flask(__name__)
CORS(app)

# ============================================================
# 🔓 LICENÇA DESATIVADA - SISTEMA SEM BLOQUEIO
# ============================================================

def verificar_licenca():
    """Sempre retorna licença válida - sem bloqueio"""
    return {
        'valida': True,
        'mensagem': 'Sistema ativo',
        'dias_restantes': 9999,
        'data_expiracao': '31/12/2099'
    }

# ============================================================
# 🔓 MIDDLEWARE DESATIVADO - NÃO BLOQUEIA NADA
# ============================================================
@app.before_request
def verificar_licenca_global():
    """Middleware desativado - não bloqueia nenhuma requisição"""
    return None

def licenca_obrigatoria(f):
    """Decorator desativado - não bloqueia"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function

# ============================================================

# ============================================================
# 🔧 CONFIGURAÇÃO CRÍTICA - AUMENTAR LIMITE DE UPLOAD
# ============================================================
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB
# ============================================================

# Configurações do Flask
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-123')
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)

# Em produção, o Vercel não permite criar pastas
try:
    os.makedirs(os.path.join('uploads', 'alunos'), exist_ok=True)
    os.makedirs(os.path.join('uploads', 'pais'), exist_ok=True)
    os.makedirs(os.path.join('uploads', 'terceiros'), exist_ok=True)
    os.makedirs('generated_terms', exist_ok=True)
    logger.info("✅ Pastas criadas com sucesso")
except Exception as e:
    logger.warning(f"⚠️ Não foi possível criar pastas: {e}")

# Registra os blueprints
app.register_blueprint(alunos_bp)
app.register_blueprint(uploads_bp)
app.register_blueprint(termos_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(justificativa_bp)
app.register_blueprint(funcionarios_bp)


# ==================== ROTAS PRINCIPAIS ====================

@app.route('/')
def index():
    """Página inicial"""
    try:
        status_licenca = verificar_licenca()
        return render_template('index.html', licenca=status_licenca)
    except Exception as e:
        logger.error(f"Erro ao renderizar index: {e}")
        return jsonify({'erro': str(e)}), 500


@app.route('/login')
def login_page():
    """Página de login (sempre livre)"""
    try:
        return render_template('login.html')
    except Exception as e:
        logger.error(f"Erro ao renderizar login: {e}")
        return jsonify({'erro': str(e)}), 500


@app.route('/alunos/buscar')
def buscar_alunos():
    """Página de busca de alunos"""
    try:
        return render_template('alunos/buscar_aluno.html')
    except Exception as e:
        logger.error(f"Erro ao renderizar buscar: {e}")
        return jsonify({'erro': str(e)}), 500


# ==================== ROTA PARA BENEFÍCIOS ====================

@app.route('/beneficios')
def beneficios():
    """Página de gestão de benefícios (Odontológico e Plano de Saúde)"""
    try:
        return render_template('beneficios.html')
    except Exception as e:
        logger.error(f"Erro ao renderizar beneficios: {e}")
        return jsonify({'erro': str(e)}), 500


# ==================== ROTA PARA CADASTRO DE ALUNO ====================

@app.route('/alunos/cadastro')
def cadastro_aluno():
    """Página de cadastro de aluno"""
    try:
        num_inscricao = request.args.get('editar')
        aluno_data = None
        
        if num_inscricao:
            print(f"📝 Modo edição - buscando aluno: {num_inscricao}")
            from database.mongo import db
            
            # Busca o aluno diretamente no MongoDB
            aluno = db.alunos.find_one({'num_inscricao': num_inscricao})
            
            if aluno:
                # Converte ObjectId para string
                if '_id' in aluno:
                    aluno['_id'] = str(aluno['_id'])
                
                # Converte data_cadastro para string se for datetime
                if aluno.get('data_cadastro') and hasattr(aluno['data_cadastro'], 'strftime'):
                    aluno['data_cadastro'] = aluno['data_cadastro'].strftime('%Y-%m-%d %H:%M:%S')
                
                print(f"✅ Aluno encontrado: {aluno['dados_pessoais']['nome']}")
                print(f"📁 Fotos IDs: {list(aluno.get('arquivos_ids', {}).keys())}")
                print(f"👥 Responsáveis: {len(aluno.get('responsaveis', []))}")
                print(f"👤 Terceiros: {len(aluno.get('terceiros', []))}")
                
                aluno_data = aluno
            else:
                print(f"❌ Aluno não encontrado: {num_inscricao}")
        
        return render_template('alunos/cadastro_aluno.html', aluno=aluno_data)
        
    except Exception as e:
        print(f"❌ Erro ao carregar página de cadastro: {str(e)}")
        import traceback
        traceback.print_exc()
        return render_template('alunos/cadastro_aluno.html', aluno=None)


@app.route('/alunos/ficha/<num_inscricao>')
def ficha_aluno(num_inscricao):
    """Página de ficha do aluno"""
    try:
        return render_template('alunos/ficha_aluno.html', num_inscricao=num_inscricao)
    except Exception as e:
        logger.error(f"Erro ao renderizar ficha: {e}")
        return jsonify({'erro': str(e)}), 500


@app.route('/alunos/gerar-termo/<num_inscricao>')
def gerar_termo(num_inscricao):
    """Página de geração de termos"""
    try:
        return render_template('alunos/gerar_termo.html', num_inscricao=num_inscricao)
    except Exception as e:
        logger.error(f"Erro ao renderizar gerar-termo: {e}")
        return jsonify({'erro': str(e)}), 500


# ==================== ROTAS PARA FUNCIONÁRIOS E JUSTIFICATIVA ====================

@app.route('/funcionarios/cadastro')
def cadastro_funcionario():
    """Página de cadastro de funcionários"""
    try:
        return render_template('administracao/cadastro_func.html')
    except Exception as e:
        logger.error(f"Erro ao renderizar cadastro_funcionario: {e}")
        return jsonify({'erro': str(e)}), 500


@app.route('/justificativa')
def justificativa():
    """Página de justificativa de saída"""
    try:
        return render_template('administracao/justificativa.html')
    except Exception as e:
        logger.error(f"Erro ao renderizar justificativa: {e}")
        return jsonify({'erro': str(e)}), 500


# ==================== ROTAS PARA VISUALIZAÇÃO DE TERMOS ====================

def capitalizar_nome(nome):
    """Capitaliza nome próprio"""
    if not nome:
        return ''
    palavras_minusculas = ['da', 'de', 'do', 'das', 'dos', 'e', 'a', 'o', 'as', 'os']
    palavras = nome.lower().split(' ')
    palavras = [palavra if palavra in palavras_minusculas else palavra.capitalize() for palavra in palavras]
    return ' '.join(palavras)

def capitalizar_texto(texto):
    """Capitaliza texto"""
    if not texto:
        return ''
    palavras_especiais = ['RG', 'CPF', 'CIN', 'CNPJ', 'TEA', 'TDAH', 'HIV', 'AIDS', 'SP', 'RJ', 'MG']
    palavras = texto.lower().split(' ')
    palavras = [palavra.upper() if palavra.upper() in palavras_especiais else palavra.capitalize() for palavra in palavras]
    return ' '.join(palavras)

@app.route('/visualizar/termo/matricula/<num_inscricao>')
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
        
        # Dados do responsável principal
        responsavel_principal = aluno.get('responsaveis', [{}])[0] if aluno.get('responsaveis') else {}
        
        dados_impressao = {
            'responsavel_nome': capitalizar_nome(responsavel_principal.get('nome', '')),
            'responsavel_parentesco': responsavel_principal.get('parentesco', 'Responsável'),
            'responsavel_rg': responsavel_principal.get('rg', ''),
            'responsavel_cpf': responsavel_principal.get('cpf', ''),
            'responsavel_telefone': responsavel_principal.get('telefone', ''),
            'nome': capitalizar_nome(aluno.get('dados_pessoais', {}).get('nome', '')),
            'data_nasc': aluno.get('dados_pessoais', {}).get('data_nasc', ''),
            'turma': capitalizar_texto(aluno.get('turma', {}).get('turma', '')),
            'unidade': capitalizar_texto(aluno.get('turma', {}).get('unidade', '')),
            'endereco': capitalizar_texto(aluno.get('endereco', {}).get('logradouro', '')),
            'numero': aluno.get('endereco', {}).get('numero', ''),
            'bairro': capitalizar_texto(aluno.get('endereco', {}).get('bairro', '')),
            'cidade': capitalizar_texto(aluno.get('endereco', {}).get('cidade', '')),
            'uf': aluno.get('endereco', {}).get('uf', ''),
            'cep': aluno.get('endereco', {}).get('cep', ''),
            'sexo': aluno.get('dados_pessoais', {}).get('sexo', '')
        }
        
        return render_template('componentes/termo_matricula.html',
                             aluno=aluno,
                             unidade=unidade,
                             data_atual=data_atual,
                             dados_impressao=dados_impressao)
    except Exception as e:
        print(f"❌ Erro ao visualizar termo matrícula: {e}")
        traceback.print_exc()
        abort(500)


@app.route('/visualizar/termo/imagem/<num_inscricao>')
def visualizar_termo_imagem(num_inscricao):
    """Visualiza termo de autorização de imagem"""
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
            'responsavel_nome': capitalizar_nome(responsavel_nome),
            'responsavel_parentesco': responsavel_parentesco,
            'responsavel_rg': responsavel_rg,
            'responsavel_cpf': responsavel_cpf,
            'responsavel_telefone': responsavel_telefone,
            'nome': capitalizar_nome(aluno.get('dados_pessoais', {}).get('nome', '')),
            'data_nasc': aluno.get('dados_pessoais', {}).get('data_nasc', ''),
            'turma': capitalizar_texto(aluno.get('turma', {}).get('turma', '')),
            'unidade': capitalizar_texto(aluno.get('turma', {}).get('unidade', '')),
            'endereco': capitalizar_texto(aluno.get('endereco', {}).get('logradouro', '')),
            'numero': aluno.get('endereco', {}).get('numero', ''),
            'bairro': capitalizar_texto(aluno.get('endereco', {}).get('bairro', '')),
            'cidade': capitalizar_texto(aluno.get('endereco', {}).get('cidade', '')),
            'uf': aluno.get('endereco', {}).get('uf', ''),
            'cep': aluno.get('endereco', {}).get('cep', ''),
            'sexo': aluno.get('dados_pessoais', {}).get('sexo', '')
        }
        
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


@app.route('/visualizar/termo/regulamento/<num_inscricao>')
def visualizar_termo_regulamento(num_inscricao):
    """Visualiza regulamento interno"""
    try:
        from database.mongo import db
        
        aluno = db.alunos.find_one({'num_inscricao': num_inscricao})
        
        if not aluno:
            abort(404, description="Aluno não encontrado")
        
        if '_id' in aluno:
            aluno['_id'] = str(aluno['_id'])
        
        responsavel_nome = request.args.get('responsavel_nome', '')
        responsavel_parentesco = request.args.get('responsavel_parentesco', '')
        responsavel_rg = request.args.get('responsavel_rg', '')
        responsavel_cpf = request.args.get('responsavel_cpf', '')
        responsavel_telefone = request.args.get('responsavel_telefone', '')
        
        dados_impressao = {
            'responsavel_nome': capitalizar_nome(responsavel_nome),
            'responsavel_parentesco': responsavel_parentesco,
            'responsavel_rg': responsavel_rg,
            'responsavel_cpf': responsavel_cpf,
            'responsavel_telefone': responsavel_telefone,
            'nome': capitalizar_nome(aluno.get('dados_pessoais', {}).get('nome', '')),
            'data_nasc': aluno.get('dados_pessoais', {}).get('data_nasc', ''),
            'turma': capitalizar_texto(aluno.get('turma', {}).get('turma', '')),
            'unidade': capitalizar_texto(aluno.get('turma', {}).get('unidade', ''))
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
        traceback.print_exc()
        abort(500)


@app.route('/visualizar/termo/saude/<num_inscricao>')
def visualizar_termo_saude(num_inscricao):
    """Visualiza termo de saúde"""
    try:
        from database.mongo import db
        
        aluno = db.alunos.find_one({'num_inscricao': num_inscricao})
        
        if not aluno:
            abort(404, description="Aluno não encontrado")
        
        if '_id' in aluno:
            aluno['_id'] = str(aluno['_id'])
        
        responsavel_nome = request.args.get('responsavel_nome', '')
        responsavel_parentesco = request.args.get('responsavel_parentesco', '')
        responsavel_rg = request.args.get('responsavel_rg', '')
        responsavel_cpf = request.args.get('responsavel_cpf', '')
        responsavel_telefone = request.args.get('responsavel_telefone', '')
        
        dados_impressao = {
            'responsavel_nome': capitalizar_nome(responsavel_nome),
            'responsavel_parentesco': responsavel_parentesco,
            'responsavel_rg': responsavel_rg,
            'responsavel_cpf': responsavel_cpf,
            'responsavel_telefone': responsavel_telefone,
            'nome': capitalizar_nome(aluno.get('dados_pessoais', {}).get('nome', '')),
            'data_nasc': aluno.get('dados_pessoais', {}).get('data_nasc', ''),
            'turma': capitalizar_texto(aluno.get('turma', {}).get('turma', '')),
            'unidade': capitalizar_texto(aluno.get('turma', {}).get('unidade', ''))
        }
        
        # Dados de saúde
        saude = aluno.get('saude', {})
        dados_saude = {
            'tipo_sanguineo': saude.get('tipo_sanguineo', ''),
            'plano_saude': saude.get('plano_saude', ''),
            'alergias': saude.get('alergias', ''),
            'medicamentos': saude.get('medicamentos', ''),
            'restricoes': saude.get('restricoes', ''),
            'pediatra': capitalizar_nome(saude.get('pediatra', '')),
            'contato_pediatra': saude.get('contato_pediatra', ''),
            'deficiencia': saude.get('deficiencia', False),
            'deficiencia_desc': saude.get('deficiencia_desc', '')
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
                             dados_impressao=dados_impressao,
                             dados_saude=dados_saude)
    except Exception as e:
        print(f"❌ Erro ao visualizar termo saúde: {e}")
        traceback.print_exc()
        abort(500)


@app.route('/visualizar/termo/transporte/<num_inscricao>')
def visualizar_termo_transporte(num_inscricao):
    """Visualiza termo de transporte"""
    try:
        from database.mongo import db
        
        aluno = db.alunos.find_one({'num_inscricao': num_inscricao})
        
        if not aluno:
            abort(404, description="Aluno não encontrado")
        
        if '_id' in aluno:
            aluno['_id'] = str(aluno['_id'])
        
        responsavel_nome = request.args.get('responsavel_nome', '')
        responsavel_parentesco = request.args.get('responsavel_parentesco', '')
        responsavel_rg = request.args.get('responsavel_rg', '')
        responsavel_cpf = request.args.get('responsavel_cpf', '')
        responsavel_telefone = request.args.get('responsavel_telefone', '')
        
        transporte = aluno.get('transporte', {})
        dados_transporte = {
            'nome': capitalizar_nome(transporte.get('nome', '')),
            'cnpj': transporte.get('cnpj', ''),
            'cpf': transporte.get('cpf', ''),
            'rg': transporte.get('rg', ''),
            'telefone': transporte.get('telefone', ''),
            'email': transporte.get('email', '')
        }
        
        dados_impressao = {
            'responsavel_nome': capitalizar_nome(responsavel_nome),
            'responsavel_parentesco': responsavel_parentesco,
            'responsavel_rg': responsavel_rg,
            'responsavel_cpf': responsavel_cpf,
            'responsavel_telefone': responsavel_telefone,
            'nome': capitalizar_nome(aluno.get('dados_pessoais', {}).get('nome', '')),
            'data_nasc': aluno.get('dados_pessoais', {}).get('data_nasc', ''),
            'turma': capitalizar_texto(aluno.get('turma', {}).get('turma', '')),
            'unidade': capitalizar_texto(aluno.get('turma', {}).get('unidade', ''))
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
                             dados_impressao=dados_impressao,
                             dados_transporte=dados_transporte)
    except Exception as e:
        print(f"❌ Erro ao visualizar termo transporte: {e}")
        traceback.print_exc()
        abort(500)


@app.route('/visualizar/termo/terceiro/<num_inscricao>')
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
        
        if not terceiro:
            abort(404, description="Terceiro não encontrado")
        
        dados_terceiro = {
            'nome': capitalizar_nome(terceiro.get('nome', '')),
            'telefone': terceiro.get('telefone', ''),
            'cpf': terceiro.get('cpf', ''),
            'rg': terceiro.get('rg', ''),
            'email': terceiro.get('email', ''),
            'numero': terceiro_num
        }
        
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
                             dados_terceiro=dados_terceiro,
                             unidade=unidade,
                             data_atual=data_atual)
    except Exception as e:
        print(f"❌ Erro ao visualizar termo terceiro: {e}")
        traceback.print_exc()
        abort(500)


# ==================== ROTAS DE TESTE E UTILITÁRIOS ====================

@app.route('/teste/foto')
def teste_foto():
    """Página de teste de foto"""
    try:
        return render_template('alunos/teste_foto.html')
    except Exception as e:
        logger.error(f"Erro ao renderizar teste foto: {e}")
        return jsonify({'erro': str(e)}), 500


@app.route('/pai/cadastro')
def pai_cadastro():
    """Cadastro de pais/responsáveis"""
    try:
        return render_template('pai_cadastro.html')
    except Exception as e:
        logger.error(f"Erro ao renderizar pai cadastro: {e}")
        return jsonify({'erro': str(e)}), 500


# ==================== ROTAS DE LICENÇA ====================

@app.route('/licenca-expirada')
def licenca_expirada():
    """Página de licença expirada"""
    status = verificar_licenca()
    return render_template('licenca_expirada.html', status=status)

@app.route('/api/verificar-licenca')
def api_verificar_licenca():
    """API para verificar status da licença"""
    status = verificar_licenca()
    return jsonify(status)

@app.route('/api/configurar-licenca', methods=['POST'])
def api_configurar_licenca():
    """API para configurar data de expiração (apenas admin)"""
    try:
        data = request.get_json()
        nova_data = data.get('data_expiracao')
        
        if not nova_data:
            return jsonify({'sucesso': False, 'erro': 'Data não informada'}), 400
        
        from database.mongo import db
        licenca_col = db.get_collection('licenca')
        
        nova_data_obj = datetime.strptime(nova_data, '%Y-%m-%d')
        licenca_col.update_one(
            {'_id': 'config'},
            {'$set': {'data_expiracao': nova_data_obj}},
            upsert=True
        )
        return jsonify({'sucesso': True, 'mensagem': f'Licença atualizada para {nova_data}'})
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 400

@app.route('/admin/licenca')
def admin_licenca():
    """Página administrativa para configurar licença"""
    status = verificar_licenca()
    return render_template('admin_licenca.html', status=status)


# ==================== ROTA DE TESTE PARA DIAGNÓSTICO ====================

@app.route('/api/test', methods=['GET'])
def api_test():
    """Rota de teste para diagnóstico"""
    try:
        from database.mongo import db
        collections = db.list_collection_names()
        return jsonify({
            'status': 'ok',
            'message': 'API funcionando',
            'environment': os.environ.get('FLASK_ENV', 'development'),
            'collections': collections
        })
    except Exception as e:
        logger.error(f"Erro no teste: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'environment': os.environ.get('FLASK_ENV', 'development')
        }), 500


# ==================== CONTEXTO GLOBAL PARA TEMPLATES ====================

@app.context_processor
def inject_user():
    """Injeta dados do usuário logado em todos os templates"""
    if session.get('user_id'):
        return {
            'user_logado': True,
            'user_nome': session.get('user_name'),
            'user_email': session.get('user_email'),
            'user_perfil': session.get('user_profile'),
            'user_unidade': session.get('user_unidade', '')
        }
    return {
        'user_logado': False,
        'user_nome': None,
        'user_email': None,
        'user_perfil': None,
        'user_unidade': None
    }


# ==================== MIDDLEWARES ====================

@app.after_request
def add_header(response):
    """Adiciona headers de segurança"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    return response


# ==================== HANDLERS DE ERRO ====================

@app.errorhandler(404)
def not_found(error):
    """Página 404 personalizada"""
    logger.warning(f"404 error: {error}")
    return jsonify({'erro': 'Página não encontrada'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Página 500 personalizada"""
    logger.error(f"500 error: {error}")
    return jsonify({'erro': 'Erro interno do servidor'}), 500


@app.errorhandler(Exception)
def handle_exception(e):
    """Handler global de exceções"""
    logger.error(f"Erro não tratado: {e}")
    import traceback
    logger.error(traceback.format_exc())
    return jsonify({
        'sucesso': False,
        'erro': str(e),
        'tipo': type(e).__name__
    }), 500


# ==================== INICIALIZAÇÃO ====================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV', 'development') == 'development'
    
    logger.info("🚀 Iniciando servidor Flask...")
    logger.info(f"📁 Pasta do projeto: {os.getcwd()}")
    logger.info(f"🔧 Debug mode: {debug_mode}")
    logger.info(f"🌐 Port: {port}")
    logger.info(f"📦 Limite de upload: 50MB")
    
    app.run(debug=debug_mode, host='0.0.0.0', port=port)