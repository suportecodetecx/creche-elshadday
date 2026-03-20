from flask import Flask, render_template
from flask_cors import CORS
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Importa as rotas
from routes.alunos_routes import alunos_bp
from routes.uploads_routes import uploads_bp
from routes.termos_routes import termos_bp

app = Flask(__name__)
CORS(app)

# Configurações
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-123')

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

# Rota principal
@app.route('/')
def index():
    return render_template('index.html')

# Rota para cadastro de aluno
@app.route('/alunos/cadastro')
def cadastro_aluno():
    return render_template('alunos/cadastro_aluno.html')

# Rota para busca de alunos
@app.route('/alunos/buscar')
def buscar_alunos():
    return render_template('alunos/buscar_aluno.html')

# IMPORTANTE: Para o Vercel, precisamos exportar a app
# O Vercel vai usar 'app' como entry point

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)