from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from datetime import datetime
import uuid

app = Flask(__name__)
CORS(app)

# Configurações - 100MB
UPLOAD_FOLDER = 'teste_uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB (aumentado)

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

@app.route('/')
def index():
    return render_template('pai_cadastro.html')

@app.route('/upload', methods=['POST'])
def upload():
    """Endpoint simples para teste de upload"""
    print("\n" + "="*60)
    print("🔍 TESTE DE UPLOAD RECEBIDO")
    print("="*60)
    
    # Mostra limite configurado
    print(f"📦 Limite de upload: {app.config['MAX_CONTENT_LENGTH'] / (1024*1024)}MB")
    
    resultados = []
    
    # Processa cada arquivo recebido
    for key in request.files:
        file = request.files[key]
        if file and file.filename:
            print(f"\n📁 Arquivo recebido: {key}")
            print(f"   Nome original: {file.filename}")
            print(f"   Tamanho: {len(file.read())} bytes")
            file.seek(0)  # Volta ao início do arquivo
            
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

# Rota para servir os arquivos (opcional, só se precisar ver as imagens)
@app.route('/teste_uploads/<path:filename>')
def uploaded_file(filename):
    """Serve os arquivos enviados para visualização"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    print(f"🚀 Servidor de teste rodando na porta 5001")
    print(f"📁 Pasta de upload: {UPLOAD_FOLDER}")
    print(f"📦 Limite: 100MB")
    app.run(debug=True, port=5001)