from flask import Flask, render_template
from flask_cors import CORS
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Importa as rotas
from routes.alunos_routes import alunos_bp
from routes.uploads_routes import uploads_bp
from routes.termos_routes import termos_bp  # ← ADICIONADO

app = Flask(__name__)
CORS(app)

# Configurações
app.config['UPLOAD_FOLDER'] = 'uploads'
# app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limite removido (comentado)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-123')

# Garantir que as pastas de upload existem
os.makedirs(os.path.join('uploads', 'alunos'), exist_ok=True)
os.makedirs(os.path.join('uploads', 'pais'), exist_ok=True)
os.makedirs(os.path.join('uploads', 'terceiros'), exist_ok=True)
os.makedirs(os.path.join('uploads', 'documentos'), exist_ok=True)

# Garantir que a pasta de termos gerados existe
os.makedirs('generated_terms', exist_ok=True)  # ← ADICIONADO

# Registra os blueprints
app.register_blueprint(alunos_bp)
app.register_blueprint(uploads_bp)
app.register_blueprint(termos_bp)  # ← ADICIONADO

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

if __name__ == '__main__':
    app.run(debug=True, port=5000)