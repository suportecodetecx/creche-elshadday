# mapear_projeto.py
import os
import sys
from pathlib import Path

def mapear_estrutura_pastas(caminho, nivel=0, max_nivel=3):
    """Mapeia a estrutura de pastas do projeto"""
    if nivel > max_nivel:
        return []
    
    resultado = []
    try:
        itens = sorted(os.listdir(caminho))
        for item in itens:
            if item.startswith('.') or item == '__pycache__' or item == 'venv' or item == 'env':
                continue
            
            caminho_completo = os.path.join(caminho, item)
            indent = "  " * nivel
            
            if os.path.isdir(caminho_completo):
                resultado.append(f"{indent}📁 {item}/")
                resultado.extend(mapear_estrutura_pastas(caminho_completo, nivel + 1, max_nivel))
            else:
                # Mostra apenas arquivos relevantes
                if item.endswith(('.py', '.html', '.js', '.css', '.json', '.txt', '.md')):
                    resultado.append(f"{indent}📄 {item}")
    except PermissionError:
        pass
    
    return resultado


def mapear_rotas(app):
    """Mapeia as rotas do Flask (se disponível)"""
    rotas = []
    if app:
        for rule in app.url_map.iter_rules():
            rotas.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods),
                'url': str(rule)
            })
    return rotas


def mapear_colecoes_mongodb():
    """Mapeia as coleções do MongoDB"""
    try:
        from database.mongo import db
        from gridfs import GridFS
        
        colecoes = db.list_collection_names()
        
        resultado = {}
        for colecao in colecoes:
            count = db[colecao].count_documents({})
            resultado[colecao] = {
                'total_documentos': count,
                'exemplo': None
            }
            
            if count > 0:
                exemplo = db[colecao].find_one({})
                if exemplo and '_id' in exemplo:
                    exemplo['_id'] = str(exemplo['_id'])
                
                # Se for a coleção de alunos, pega mais detalhes
                if colecao == 'alunos':
                    if exemplo.get('arquivos'):
                        resultado[colecao]['tem_arquivos_base64'] = len(exemplo.get('arquivos', []))
                    if exemplo.get('arquivos_ids'):
                        resultado[colecao]['tem_arquivos_gridfs'] = len(exemplo.get('arquivos_ids', {}))
                
                resultado[colecao]['exemplo'] = exemplo
        
        # Listar arquivos do GridFS
        try:
            fs = GridFS(db)
            gridfs_arquivos = []
            for arq in fs.find().limit(10):
                gridfs_arquivos.append({
                    '_id': str(arq._id),
                    'filename': arq.filename,
                    'length': arq.length,
                    'uploadDate': str(arq.uploadDate) if arq.uploadDate else None
                })
            resultado['_gridfs'] = {
                'total_arquivos': fs.find().count(),
                'primeiros_10': gridfs_arquivos
            }
        except:
            resultado['_gridfs'] = {'erro': 'Não foi possível acessar GridFS'}
        
        return resultado
        
    except Exception as e:
        return {'erro': str(e)}


def mapear_arquivos_importantes():
    """Mapeia arquivos importantes do projeto"""
    importantes = []
    
    # Arquivos de configuração
    config_files = ['app.py', 'config.py', '.env', 'requirements.txt', 'vercel.json']
    for file in config_files:
        if os.path.exists(file):
            importantes.append(f"✅ {file}")
        else:
            importantes.append(f"❌ {file}")
    
    # Pastas principais
    pastas = ['templates', 'static', 'routes', 'services', 'database', 'uploads', 'models']
    for pasta in pastas:
        if os.path.exists(pasta):
            qtd = len([f for f in os.listdir(pasta) if os.path.isfile(os.path.join(pasta, f))]) if os.path.isdir(pasta) else 0
            importantes.append(f"📁 {pasta}/ ({qtd} arquivos)")
        else:
            importantes.append(f"❌ {pasta}/ (não existe)")
    
    return importantes


def mapear_blueprints():
    """Mapeia os blueprints registrados"""
    try:
        from app import app
        blueprints = []
        for blueprint in app.blueprints:
            blueprints.append(f"🔵 {blueprint}")
        return blueprints
    except:
        return ["⚠️ Não foi possível carregar o app"]


def mapear_templates():
    """Mapeia os templates HTML disponíveis"""
    templates = {}
    if os.path.exists('templates'):
        for root, dirs, files in os.walk('templates'):
            for file in files:
                if file.endswith('.html'):
                    rel_path = os.path.relpath(os.path.join(root, file), 'templates')
                    pasta = os.path.dirname(rel_path) if os.path.dirname(rel_path) else 'raiz'
                    if pasta not in templates:
                        templates[pasta] = []
                    templates[pasta].append(file)
    
    return templates


def main():
    print("=" * 80)
    print("🔍 MAPEAMENTO COMPLETO DO PROJETO")
    print("=" * 80)
    
    # 1. Estrutura de Pastas
    print("\n📁 1. ESTRUTURA DE PASTAS DO PROJETO")
    print("-" * 50)
    caminho_atual = os.getcwd()
    estrutura = mapear_estrutura_pastas(caminho_atual)
    for linha in estrutura:
        print(linha)
    
    # 2. Arquivos Importantes
    print("\n\n📄 2. ARQUIVOS IMPORTANTES")
    print("-" * 50)
    for item in mapear_arquivos_importantes():
        print(item)
    
    # 3. Templates HTML
    print("\n\n🎨 3. TEMPLATES HTML")
    print("-" * 50)
    templates = mapear_templates()
    for pasta, arquivos in templates.items():
        print(f"\n📁 {pasta}/")
        for arquivo in arquivos:
            print(f"   📄 {arquivo}")
    
    # 4. Blueprints (Rotas)
    print("\n\n🔵 4. BLUEPRINTS (ROTAS REGISTRADAS)")
    print("-" * 50)
    blueprints = mapear_blueprints()
    for bp in blueprints:
        print(bp)
    
    # 5. MongoDB
    print("\n\n🍃 5. MONGODB - COLEÇÕES E ARQUIVOS")
    print("-" * 50)
    mongo_data = mapear_colecoes_mongodb()
    
    if 'erro' in mongo_data:
        print(f"❌ Erro ao conectar ao MongoDB: {mongo_data['erro']}")
    else:
        for colecao, dados in mongo_data.items():
            if colecao.startswith('_'):
                continue
            print(f"\n📚 {colecao}: {dados['total_documentos']} documentos")
            
            if dados.get('tem_arquivos_base64'):
                print(f"   📎 Arquivos Base64: {dados['tem_arquivos_base64']}")
            if dados.get('tem_arquivos_gridfs'):
                print(f"   🗃️ Arquivos GridFS: {dados['tem_arquivos_gridfs']}")
            
            if dados['exemplo']:
                # Mostra apenas campos principais
                exemplo = dados['exemplo']
                campos = list(exemplo.keys())[:5]
                print(f"   📋 Campos: {', '.join(campos)}")
        
        # GridFS
        if '_gridfs' in mongo_data:
            print(f"\n🗃️ GRIDFS: {mongo_data['_gridfs'].get('total_arquivos', 0)} arquivos")
            for arq in mongo_data['_gridfs'].get('primeiros_10', []):
                print(f"   📄 {arq['filename']} ({arq['length']} bytes)")
    
    # 6. Resumo
    print("\n\n📊 6. RESUMO")
    print("-" * 50)
    print(f"📁 Pastas: {len([d for d in os.listdir('.') if os.path.isdir(d) and not d.startswith('.')])}")
    print(f"📄 Arquivos Python: {len([f for f in os.listdir('.') if f.endswith('.py')])}")
    print(f"🎨 Templates HTML: {sum(len(v) for v in templates.values())}")
    print(f"🍃 Coleções MongoDB: {len([c for c in mongo_data if not c.startswith('_')])}")
    
    print("\n" + "=" * 80)
    print("✅ MAPEAMENTO CONCLUÍDO!")
    print("=" * 80)


if __name__ == "__main__":
    main()