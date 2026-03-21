from flask import Flask, render_template, session
from flask_cors import CORS
import os
from dotenv import load_dotenv
from datetime import timedelta

# Carrega variáveis de ambiente
load_dotenv()

# Importa as rotas
from routes.alunos_routes import alunos_bp
from routes.uploads_routes import uploads_bp
from routes.termos_routes import termos_bp
from routes.auth_routes import auth_bp  # Importa o blueprint de autenticação

app = Flask(__name__)
CORS(app)

# Configurações do Flask
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-123')
app.config['SESSION_COOKIE_SECURE'] = False  # Mude para True em produção com HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)  # Sessão dura 8 horas

# Em produção, o Vercel não permite criar pastas
# Vamos tratar com try/except
try:
    # Garantir que as pastas de upload existem
    os.makedirs(os.path.join('uploads', 'alunos'), exist_ok=True)
    os.makedirs(os.path.join('uploads', 'pais'), exist_ok=True)
    os.makedirs(os.path.join('uploads', 'terceiros'), exist_ok=True)
    os.makedirs(os.path.join('uploads', 'documentos'), exist_ok=True)
    os.makedirs('generated_terms', exist_ok=True)
except Exception as e:
    print(f"⚠️ Aviso: Não foi possível criar pastas (Vercel não permite): {e}")

# Registra os blueprints
app.register_blueprint(alunos_bp)
app.register_blueprint(uploads_bp)
app.register_blueprint(termos_bp)
app.register_blueprint(auth_bp)  # Registra o blueprint de autenticação


# ==================== ROTAS PRINCIPAIS ====================

@app.route('/')
def index():
    """Página inicial com os 4 acessos (Pedagógico, Admin, Professores, Colaboradores)"""
    return render_template('index.html')


@app.route('/login')
def login_page():
    """Página de login (pode ser usada como fallback)"""
    return render_template('login.html')


@app.route('/alunos/cadastro')
def cadastro_aluno():
    """Página de cadastro de alunos"""
    return render_template('alunos/cadastro_aluno.html')


@app.route('/alunos/buscar')
def buscar_alunos():
    """Página de busca de alunos"""
    return render_template('alunos/buscar_aluno.html')


@app.route('/alunos/ficha/<num_inscricao>')
def ficha_aluno(num_inscricao):
    """Página de ficha do aluno"""
    return render_template('alunos/ficha_aluno.html', num_inscricao=num_inscricao)


@app.route('/alunos/gerar-termo/<num_inscricao>')
def gerar_termo(num_inscricao):
    """Página de geração de termos"""
    return render_template('alunos/gerar_termo.html', num_inscricao=num_inscricao)


@app.route('/documentos/dashboard')
def dashboard_documentos():
    """Dashboard de documentos"""
    return render_template('documentos/dashboard.html')


@app.route('/documentos/doc-prof')
def doc_prof():
    """Documentos profissionais"""
    return render_template('documentos/doc_prof.html')


@app.route('/documentos/atestado')
def atestado_upload():
    """Upload de atestados"""
    return render_template('documentos/atestado_upload.html')


# ==================== ROTAS PARA VISUALIZAÇÃO DE TERMOS ====================

@app.route('/visualizar/termo/matricula/<num_inscricao>')
def visualizar_termo_matricula(num_inscricao):
    """Visualiza termo de matrícula"""
    return render_template('componentes/termo_matricula.html', num_inscricao=num_inscricao)


@app.route('/visualizar/termo/imagem/<num_inscricao>')
def visualizar_termo_imagem(num_inscricao):
    """Visualiza termo de autorização de imagem"""
    return render_template('componentes/autorizacao_imagem.html', num_inscricao=num_inscricao)


@app.route('/visualizar/termo/transporte/<num_inscricao>')
def visualizar_termo_transporte(num_inscricao):
    """Visualiza termo de transporte"""
    return render_template('componentes/termo_transporte.html', num_inscricao=num_inscricao)


@app.route('/visualizar/termo/terceiro/<num_inscricao>')
def visualizar_termo_terceiro(num_inscricao):
    """Visualiza termo de terceiros autorizados"""
    return render_template('componentes/termo_terceiro.html', num_inscricao=num_inscricao)


@app.route('/visualizar/termo/regulamento/<num_inscricao>')
def visualizar_termo_regulamento(num_inscricao):
    """Visualiza regulamento interno"""
    return render_template('componentes/regulamento.html', num_inscricao=num_inscricao)


@app.route('/visualizar/termo/saude/<num_inscricao>')
def visualizar_termo_saude(num_inscricao):
    """Visualiza termo de saúde"""
    return render_template('componentes/termo_saude.html', num_inscricao=num_inscricao)


# ==================== ROTAS DE TESTE E UTILITÁRIOS ====================

@app.route('/teste/foto')
def teste_foto():
    """Página de teste de foto"""
    return render_template('alunos/teste_foto.html')


@app.route('/pai/cadastro')
def pai_cadastro():
    """Cadastro de pais/responsáveis"""
    return render_template('pai_cadastro.html')


# ==================== CONTEXTO GLOBAL PARA TEMPLATES ====================

@app.context_processor
def inject_user():
    """Injeta dados do usuário logado em todos os templates"""
    if session.get('user_id'):
        return {
            'user_logado': True,
            'user_nome': session.get('user_name'),
            'user_email': session.get('user_email'),
            'user_perfil': session.get('user_profile')
        }
    return {
        'user_logado': False,
        'user_nome': None,
        'user_email': None,
        'user_perfil': None
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
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    """Página 500 personalizada"""
    return render_template('500.html'), 500


# ==================== INICIALIZAÇÃO ====================

# IMPORTANTE: Para o Vercel, precisamos exportar a app
# O Vercel vai usar 'app' como entry point

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    # Em desenvolvimento, debug=True
    debug_mode = os.environ.get('FLASK_ENV', 'development') == 'development'
    app.run(debug=debug_mode, host='0.0.0.0', port=port)