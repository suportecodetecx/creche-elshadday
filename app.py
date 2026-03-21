from flask import Flask, render_template, session, jsonify
from flask_cors import CORS
import os
import logging
import sys
from dotenv import load_dotenv
from datetime import timedelta

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

app = Flask(__name__)
CORS(app)

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
    os.makedirs(os.path.join('uploads', 'documentos'), exist_ok=True)
    os.makedirs('generated_terms', exist_ok=True)
    logger.info("✅ Pastas criadas com sucesso")
except Exception as e:
    logger.warning(f"⚠️ Não foi possível criar pastas: {e}")

# Registra os blueprints
app.register_blueprint(alunos_bp)
app.register_blueprint(uploads_bp)
app.register_blueprint(termos_bp)
app.register_blueprint(auth_bp)


# ==================== ROTAS PRINCIPAIS ====================

@app.route('/')
def index():
    """Página inicial"""
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Erro ao renderizar index: {e}")
        return jsonify({'erro': str(e)}), 500


@app.route('/login')
def login_page():
    """Página de login"""
    try:
        return render_template('login.html')
    except Exception as e:
        logger.error(f"Erro ao renderizar login: {e}")
        return jsonify({'erro': str(e)}), 500


@app.route('/alunos/cadastro')
def cadastro_aluno():
    """Página de cadastro de alunos"""
    try:
        return render_template('alunos/cadastro_aluno.html')
    except Exception as e:
        logger.error(f"Erro ao renderizar cadastro: {e}")
        return jsonify({'erro': str(e)}), 500


@app.route('/alunos/buscar')
def buscar_alunos():
    """Página de busca de alunos"""
    try:
        return render_template('alunos/buscar_aluno.html')
    except Exception as e:
        logger.error(f"Erro ao renderizar buscar: {e}")
        return jsonify({'erro': str(e)}), 500


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


@app.route('/documentos/dashboard')
def dashboard_documentos():
    """Dashboard de documentos"""
    try:
        return render_template('documentos/dashboard.html')
    except Exception as e:
        logger.error(f"Erro ao renderizar dashboard: {e}")
        return jsonify({'erro': str(e)}), 500


@app.route('/documentos/doc-prof')
def doc_prof():
    """Documentos profissionais"""
    try:
        return render_template('documentos/doc_prof.html')
    except Exception as e:
        logger.error(f"Erro ao renderizar doc-prof: {e}")
        return jsonify({'erro': str(e)}), 500


@app.route('/documentos/atestado')
def atestado_upload():
    """Upload de atestados"""
    try:
        return render_template('documentos/atestado_upload.html')
    except Exception as e:
        logger.error(f"Erro ao renderizar atestado: {e}")
        return jsonify({'erro': str(e)}), 500


# ==================== ROTAS PARA VISUALIZAÇÃO DE TERMOS ====================

@app.route('/visualizar/termo/matricula/<num_inscricao>')
def visualizar_termo_matricula(num_inscricao):
    """Visualiza termo de matrícula"""
    try:
        return render_template('componentes/termo_matricula.html', num_inscricao=num_inscricao)
    except Exception as e:
        logger.error(f"Erro ao renderizar termo matricula: {e}")
        return jsonify({'erro': str(e)}), 500


@app.route('/visualizar/termo/imagem/<num_inscricao>')
def visualizar_termo_imagem(num_inscricao):
    """Visualiza termo de autorização de imagem"""
    try:
        return render_template('componentes/autorizacao_imagem.html', num_inscricao=num_inscricao)
    except Exception as e:
        logger.error(f"Erro ao renderizar termo imagem: {e}")
        return jsonify({'erro': str(e)}), 500


@app.route('/visualizar/termo/transporte/<num_inscricao>')
def visualizar_termo_transporte(num_inscricao):
    """Visualiza termo de transporte"""
    try:
        return render_template('componentes/termo_transporte.html', num_inscricao=num_inscricao)
    except Exception as e:
        logger.error(f"Erro ao renderizar termo transporte: {e}")
        return jsonify({'erro': str(e)}), 500


@app.route('/visualizar/termo/terceiro/<num_inscricao>')
def visualizar_termo_terceiro(num_inscricao):
    """Visualiza termo de terceiros autorizados"""
    try:
        return render_template('componentes/termo_terceiro.html', num_inscricao=num_inscricao)
    except Exception as e:
        logger.error(f"Erro ao renderizar termo terceiro: {e}")
        return jsonify({'erro': str(e)}), 500


@app.route('/visualizar/termo/regulamento/<num_inscricao>')
def visualizar_termo_regulamento(num_inscricao):
    """Visualiza regulamento interno"""
    try:
        return render_template('componentes/regulamento.html', num_inscricao=num_inscricao)
    except Exception as e:
        logger.error(f"Erro ao renderizar termo regulamento: {e}")
        return jsonify({'erro': str(e)}), 500


@app.route('/visualizar/termo/saude/<num_inscricao>')
def visualizar_termo_saude(num_inscricao):
    """Visualiza termo de saúde"""
    try:
        return render_template('componentes/termo_saude.html', num_inscricao=num_inscricao)
    except Exception as e:
        logger.error(f"Erro ao renderizar termo saude: {e}")
        return jsonify({'erro': str(e)}), 500


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


# ==================== ROTA DE TESTE PARA DIAGNÓSTICO ====================

@app.route('/api/test', methods=['GET'])
def test_api():
    """Rota de teste para diagnóstico"""
    try:
        from database.mongo import db
        collections = db.list_collection_names()
        return jsonify({
            'status': 'ok',
            'mongodb': 'connected',
            'collections': collections
        })
    except Exception as e:
        logger.error(f"Erro no teste: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
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
    
    app.run(debug=debug_mode, host='0.0.0.0', port=port)