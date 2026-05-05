from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from datetime import datetime, timedelta
import uuid
from database.mongo import db

app = Flask(__name__)
CORS(app)

# ==================== CONFIGURAÇÃO DE LICENÇA ====================
# Data de expiração do sistema (troque para a data que desejar)
# Formato: ANO, MES, DIA
DATA_EXPIRACAO = datetime(2026, 12, 31)  # EXEMPLO: expira em 31/12/2026

# Para teste: DATA_EXPIRACAO = datetime(2025, 1, 1)  # já expirado

def verificar_licenca():
    """Verifica se a licença está válida"""
    try:
        # Buscar data de expiração do banco (se existir)
        licenca_col = db.get_collection('licenca')
        config = licenca_col.find_one({'_id': 'config'})
        
        if config and config.get('data_expiracao'):
            data_expiracao = config['data_expiracao']
        else:
            # Usar data fixa do código
            data_expiracao = DATA_EXPIRACAO
        
        hoje = datetime.now()
        
        if hoje > data_expiracao:
            dias_expirado = (hoje - data_expiracao).days
            return {
                'valida': False,
                'mensagem': f'Sistema expirado há {dias_expirado} dias. Entre em contato com o suporte.',
                'dias_restantes': 0,
                'data_expiracao': data_expiracao.strftime('%d/%m/%Y')
            }
        
        dias_restantes = (data_expiracao - hoje).days
        return {
            'valida': True,
            'mensagem': f'Sistema válido por mais {dias_restantes} dias',
            'dias_restantes': dias_restantes,
            'data_expiracao': data_expiracao.strftime('%d/%m/%Y')
        }
        
    except Exception as e:
        print(f"Erro ao verificar licença: {e}")
        # Em caso de erro, permitir acesso (modo seguro)
        return {
            'valida': True,
            'mensagem': 'Modo seguro - sistema ativo',
            'dias_restantes': 999,
            'data_expiracao': 'N/A'
        }

def verificar_licenca_decorator(f):
    """Decorator para verificar licença em rotas"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Rotas que NÃO devem ser bloqueadas
        rotas_livres = ['/', '/licenca-expirada', '/api/verificar-licenca', '/static', '/teste_uploads']
        
        for rota_livre in rotas_livres:
            if request.path.startswith(rota_livre):
                return f(*args, **kwargs)
        
        status = verificar_licenca()
        if not status['valida']:
            if request.path.startswith('/api/'):
                return jsonify({
                    'sucesso': False,
                    'erro': 'licenca_expirada',
                    'mensagem': status['mensagem'],
                    'data_expiracao': status['data_expiracao']
                }), 403
            return render_template('licenca_expirada.html', status=status)
        
        return f(*args, **kwargs)
    return decorated_function

# ==================== CONFIGURAÇÕES DE UPLOAD ====================
UPLOAD_FOLDER = 'teste_uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

# Garantir que a pasta de teste existe
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file, campo):
    """Salva um arquivo enviado e retorna informações"""
    if file and allowed_file(file.filename):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{timestamp}_{unique_id}_{campo}.{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        return {
            'campo': campo,
            'nome': filename,
            'caminho': f"/teste_uploads/{filename}",
            'tipo': ext,
            'tamanho': os.path.getsize(filepath)
        }
    return None

# ==================== ROTAS ====================

@app.route('/')
def index():
    """Página inicial"""
    status = verificar_licenca()
    return render_template('pai_cadastro.html', licenca=status)

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
    data = request.get_json()
    nova_data = data.get('data_expiracao')  # formato: '2026-12-31'
    
    try:
        from database.mongo import db
        licenca_col = db.get_collection('licenca')
        licenca_col.update_one(
            {'_id': 'config'},
            {'$set': {'data_expiracao': datetime.strptime(nova_data, '%Y-%m-%d')}},
            upsert=True
        )
        return jsonify({'sucesso': True, 'mensagem': f'Licença atualizada para {nova_data}'})
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 400

@app.route('/upload', methods=['POST'])
@verificar_licenca_decorator
def upload():
    """Endpoint simples para teste de upload"""
    print("\n" + "="*60)
    print("🔍 TESTE DE UPLOAD RECEBIDO")
    print("="*60)
    
    print(f"📦 Limite de upload: {app.config['MAX_CONTENT_LENGTH'] / (1024*1024)}MB")
    
    resultados = []
    
    for key in request.files:
        file = request.files[key]
        if file and file.filename:
            print(f"\n📁 Arquivo recebido: {key}")
            print(f"   Nome original: {file.filename}")
            print(f"   Tamanho: {len(file.read())} bytes")
            file.seek(0)
            
            info = save_uploaded_file(file, key)
            if info:
                resultados.append(info)
                print(f"   ✅ Salvo como: {info['nome']}")
                print(f"   📦 Tamanho salvo: {info['tamanho']} bytes")
    
    print(f"\n📦 Total de arquivos salvos: {len(resultados)}")
    print("="*60)
    
    return jsonify({
        'sucesso': True,
        'arquivos': resultados,
        'mensagem': f'{len(resultados)} arquivo(s) salvo(s) com sucesso!'
    })

@app.route('/teste_uploads/<path:filename>')
def uploaded_file(filename):
    """Serve os arquivos enviados para visualização"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ==================== ADMIN - PÁGINA DE CONFIGURAÇÃO DE LICENÇA ====================
@app.route('/admin/licenca')
def admin_licenca():
    """Página administrativa para configurar licença"""
    status = verificar_licenca()
    return render_template('admin_licenca.html', status=status)

if __name__ == '__main__':
    # Criar coleção de licença se não existir
    try:
        from database.mongo import init_db
        init_db()
        licenca_col = db.get_collection('licenca')
        if not licenca_col.find_one({'_id': 'config'}):
            licenca_col.insert_one({
                '_id': 'config',
                'data_expiracao': DATA_EXPIRACAO,
                'criado_em': datetime.now()
            })
            print(f"✅ Licença configurada com expiração em: {DATA_EXPIRACAO.strftime('%d/%m/%Y')}")
    except Exception as e:
        print(f"⚠️ Não foi possível conectar ao MongoDB: {e}")
        print(f"⚠️ Usando data fixa: {DATA_EXPIRACAO.strftime('%d/%m/%Y')}")
    
    print(f"🚀 Servidor de teste rodando na porta 5001")
    print(f"📁 Pasta de upload: {UPLOAD_FOLDER}")
    print(f"📦 Limite: 100MB")
    print(f"🔒 Licença expira em: {DATA_EXPIRACAO.strftime('%d/%m/%Y')}")
    app.run(debug=True, port=5001)