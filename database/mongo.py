# database/mongo.py
from pymongo import MongoClient
from gridfs import GridFS
from bson import ObjectId
import os
from dotenv import load_dotenv
import bcrypt
from datetime import datetime

load_dotenv()

class MongoDB:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            
            # Conexão com MongoDB Atlas
            mongo_uri = os.getenv('MONGO_URI', 'mongodb+srv://cadastro_db_user:0Vvl27ZcrYqaD8Kj@cluster0.6mtltjd.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
            db_name = os.getenv('DB_NAME', 'creche_el_shadday')
            
            # Configurações de conexão
            cls._instance.client = MongoClient(
                mongo_uri,
                tls=True,
                tlsAllowInvalidCertificates=True,
                connectTimeoutMS=30000,
                socketTimeoutMS=30000
            )
            
            # Seleciona o banco de dados
            cls._instance.db = cls._instance.client[db_name]
            
            # Inicializa GridFS
            cls._instance._fs = None
            
            # Testar conexão
            try:
                # Tenta um comando simples para testar a conexão
                cls._instance.client.admin.command('ping')
                print("✅ Conectado ao MongoDB Atlas com sucesso!")
                print(f"📦 Banco de dados: {db_name}")
                
                # Lista as coleções existentes
                collections = cls._instance.db.list_collection_names()
                print(f"📚 Coleções existentes: {collections}")
                
                # Criar índices para as coleções
                cls._instance._criar_indices()
                
                # CRIAR USUÁRIOS PADRÃO
                cls._instance._criar_usuarios_padrao()
                
            except Exception as e:
                print(f"❌ Erro ao conectar ao MongoDB: {e}")
                
        return cls._instance
    
    def _criar_indices(self):
        """Cria índices para otimizar buscas e evitar duplicidade"""
        try:
            # Índice para funcionários (RGM único)
            if 'funcionarios' in self.db.list_collection_names():
                self.db.funcionarios.create_index('rgm', unique=True)
                print("✅ Índice 'rgm' criado na coleção 'funcionarios'")
            
            # Índice para alunos (número de inscrição único)
            if 'alunos' in self.db.list_collection_names():
                self.db.alunos.create_index('num_inscricao', unique=True)
                print("✅ Índice 'num_inscricao' criado na coleção 'alunos'")
                
                # ===== NOVOS ÍNDICES PARA EVITAR DUPLICIDADE =====
                # Índice para RA (único - opcional, mas recomendado)
                self.db.alunos.create_index('dados_pessoais.ra', unique=True, sparse=True)
                print("✅ Índice 'dados_pessoais.ra' criado (único)")
                
                # Índice para busca de nome case-insensitive
                self.db.alunos.create_index([('dados_pessoais.nome', 'text')])
                print("✅ Índice de texto para 'dados_pessoais.nome' criado")
            
            # Índice para usuários (usuário único)
            if 'usuarios' in self.db.list_collection_names():
                self.db.usuarios.create_index('usuario', unique=True)
                print("✅ Índice 'usuario' criado na coleção 'usuarios'")
            
            # ===== ÍNDICES PARA DOCUMENTOS =====
            if 'documentos' in self.db.list_collection_names():
                # Índice para buscas por tipo (prestacao/atestado)
                self.db.documentos.create_index('tipo')
                print("✅ Índice 'tipo' criado na coleção 'documentos'")
                
                # Índice composto para buscas por mês e ano
                self.db.documentos.create_index([('mes', 1), ('ano', 1)])
                print("✅ Índice composto 'mes+ano' criado na coleção 'documentos'")
                
                # Índice para buscas por nome (case insensitive)
                self.db.documentos.create_index('nome_lower')
                print("✅ Índice 'nome_lower' criado na coleção 'documentos'")
                
                # Índice para ordenação por data de upload
                self.db.documentos.create_index('data_upload')
                print("✅ Índice 'data_upload' criado na coleção 'documentos'")
            
        except Exception as e:
            print(f"⚠️ Erro ao criar índices: {e}")
    
    def _criar_usuarios_padrao(self):
        """Cria usuários padrão se não existirem"""
        try:
            # Garantir que a coleção usuarios existe
            if 'usuarios' not in self.db.list_collection_names():
                self.db.create_collection('usuarios')
                print("✅ Coleção 'usuarios' criada")
            
            # Lista de usuários padrão
            usuarios_padrao = [
                {
                    'usuario': 'master',
                    'email': 'master@creche.com',
                    'senha_plana': 'code@@',
                    'nome': 'Administrador Master',
                    'perfil': 'master',
                    'unidade': 'Todas as Unidades',
                    'status': 'ativo',
                    'ativo': True
                },
                {
                    'usuario': 'admin',
                    'email': 'admin@creche.com',
                    'senha_plana': 'admin123',
                    'nome': 'Administração',
                    'perfil': 'admin',
                    'unidade': 'Todas as Unidades',
                    'status': 'ativo',
                    'ativo': True
                },
                {
                    'usuario': 'pedagogico',
                    'email': 'pedagogico@creche.com',
                    'senha_plana': 'pedagogo123',
                    'nome': 'Usuário Pedagógico',
                    'perfil': 'pedagogico',
                    'unidade': '',
                    'status': 'ativo',
                    'ativo': True
                },
                {
                    'usuario': 'pedagogaceic',
                    'email': 'pedagogaceic@creche.com',
                    'senha_plana': '1234@@',
                    'nome': 'Usuário Pedagógico CEIC',
                    'perfil': 'pedagogico',
                    'unidade': 'CEIC El Shadday',
                    'status': 'ativo',
                    'ativo': True
                },
                {
                    'usuario': 'pedagogaceim',
                    'email': 'pedagogaceim@creche.com',
                    'senha_plana': '1234@@',
                    'nome': 'Usuário Pedagógico CEIM',
                    'perfil': 'pedagogico',
                    'unidade': 'CEIM Prof. Egberto Malta Moreira',
                    'status': 'ativo',
                    'ativo': True
                }
            ]
            
            for user_data in usuarios_padrao:
                # Verificar se usuário já existe
                existing = self.db.usuarios.find_one({'usuario': user_data['usuario']})
                
                # Gerar hash da senha
                senha_hash = bcrypt.hashpw(user_data['senha_plana'].encode('utf-8'), bcrypt.gensalt())
                
                dados_usuario = {
                    'email': user_data['email'],
                    'senha': senha_hash,
                    'nome': user_data['nome'],
                    'perfil': user_data['perfil'],
                    'unidade': user_data['unidade'],
                    'status': user_data['status'],
                    'ativo': user_data['ativo'],
                    'data_atualizacao': datetime.now()
                }
                
                if existing:
                    # Atualizar usuário existente
                    self.db.usuarios.update_one(
                        {'usuario': user_data['usuario']},
                        {'$set': dados_usuario}
                    )
                    print(f"✅ Usuário {user_data['usuario']} ATUALIZADO")
                else:
                    # Criar novo usuário
                    dados_usuario['usuario'] = user_data['usuario']
                    dados_usuario['data_criacao'] = datetime.now()
                    self.db.usuarios.insert_one(dados_usuario)
                    print(f"✅ Usuário {user_data['usuario']} CRIADO")
            
            print("\n🔑 CREDENCIAIS DOS USUÁRIOS:")
            print("-" * 40)
            print("👑 master / code@@ (Administrador Master - TODOS os cards)")
            print("👨‍💼 admin / admin123 (Administrador - 2 cards)")
            print("👩‍🏫 pedagogico / pedagogo123 (Pedagógico - 3 cards)")
            print("👩‍🏫 pedagogaceic / 1234@@ (CEIC El Shadday - 3 cards)")
            print("👩‍🏫 pedagogaceim / 1234@@ (CEIM - 3 cards)")
            print("=" * 40)
            
        except Exception as e:
            print(f"⚠️ Erro ao criar usuários padrão: {e}")
    
    def get_collection(self, name):
        """Retorna uma coleção do banco de dados"""
        return self.db[name]
    
    def list_collection_names(self):
        """Lista os nomes das coleções"""
        try:
            return self.db.list_collection_names()
        except Exception as e:
            print(f"Erro ao listar coleções: {e}")
            return []
    
    def get_gridfs(self):
        """Retorna uma instância do GridFS para armazenar arquivos grandes"""
        if self._fs is None:
            self._fs = GridFS(self.db)
        return self._fs
    
    def __getattr__(self, name):
        """Permite acesso direto às coleções (ex: db.usuarios)"""
        return self.db[name]

# Instância global
db = MongoDB()


# ==================== FUNÇÕES AUXILIARES PARA ACESSO AO BANCO ====================

def get_db():
    """Retorna a instância do banco de dados"""
    return db


def get_collection(collection_name):
    """Retorna uma coleção específica"""
    return db.get_collection(collection_name)


def get_gridfs():
    """Retorna a instância do GridFS"""
    return db.get_gridfs()


# ==================== FUNÇÕES PARA GRIDFS (ARQUIVOS GRANDES) ====================

def salvar_arquivo_gridfs(file, nome_original, campo):
    """Salva arquivo no GridFS e retorna o ID"""
    try:
        fs = get_gridfs()
        
        # Ler o arquivo
        file_data = file.read()
        
        # Salvar no GridFS
        file_id = fs.put(
            file_data,
            filename=nome_original,
            metadata={
                'campo': campo,
                'original_name': nome_original,
                'content_type': file.content_type,
                'upload_date': datetime.now()
            }
        )
        
        print(f"   ✅ Arquivo salvo no GridFS: {nome_original} (ID: {file_id})")
        
        return str(file_id)
        
    except Exception as e:
        print(f"   ❌ Erro ao salvar no GridFS: {e}")
        return None


def get_arquivo_gridfs(file_id):
    """Recupera arquivo do GridFS pelo ID"""
    try:
        fs = get_gridfs()
        return fs.get(ObjectId(file_id))
    except Exception as e:
        print(f"❌ Erro ao recuperar arquivo: {e}")
        return None


def excluir_arquivo_gridfs(file_id):
    """Exclui arquivo do GridFS pelo ID"""
    try:
        fs = get_gridfs()
        fs.delete(ObjectId(file_id))
        print(f"✅ Arquivo excluído do GridFS: {file_id}")
        return True
    except Exception as e:
        print(f"❌ Erro ao excluir arquivo: {e}")
        return False


# ==================== FUNÇÕES PARA VERIFICAÇÃO DE DUPLICIDADE ====================

def verificar_duplicidade_aluno(nome=None, ra=None, num_inscricao_ignore=None):
    """
    Verifica se já existe aluno com o mesmo nome ou RA
    
    Args:
        nome: Nome do aluno (opcional)
        ra: RA do aluno (opcional)
        num_inscricao_ignore: Número de inscrição para ignorar (útil na edição)
    
    Returns:
        dict: {'existe': bool, 'mensagem': str, 'duplicado_por': str}
    """
    try:
        # Verificar por RA (mais preciso)
        if ra and ra.strip():
            query = {'dados_pessoais.ra': ra.strip()}
            if num_inscricao_ignore:
                query['num_inscricao'] = {'$ne': num_inscricao_ignore}
            
            aluno_ra = db.alunos.find_one(query)
            if aluno_ra:
                return {
                    'existe': True,
                    'mensagem': f'Já existe um aluno cadastrado com o RA: {ra} (Aluno: {aluno_ra["dados_pessoais"]["nome"]})',
                    'duplicado_por': 'ra'
                }
        
        # Verificar por nome (case-insensitive)
        if nome and nome.strip():
            import re
            query = {
                'dados_pessoais.nome': {'$regex': f'^{re.escape(nome.strip())}$', '$options': 'i'}
            }
            if num_inscricao_ignore:
                query['num_inscricao'] = {'$ne': num_inscricao_ignore}
            
            aluno_nome = db.alunos.find_one(query)
            if aluno_nome:
                return {
                    'existe': True,
                    'mensagem': f'Já existe um aluno cadastrado com o nome: {nome} (RA: {aluno_nome["dados_pessoais"].get("ra", "N/A")})',
                    'duplicado_por': 'nome'
                }
        
        return {'existe': False, 'mensagem': '', 'duplicado_por': None}
        
    except Exception as e:
        print(f"❌ Erro ao verificar duplicidade: {e}")
        return {'existe': False, 'mensagem': 'Erro ao verificar', 'duplicado_por': None, 'erro': str(e)}


# ==================== FUNÇÕES PARA USUÁRIOS ====================

def get_usuario_by_username(usuario):
    """Busca usuário pelo nome de usuário"""
    try:
        return db.usuarios.find_one({'usuario': usuario}, {'_id': 0})
    except Exception as e:
        print(f"Erro ao buscar usuário: {e}")
        return None


def listar_usuarios():
    """Lista todos os usuários (sem senha)"""
    try:
        return list(db.usuarios.find({}, {'_id': 0, 'senha': 0}))
    except Exception as e:
        print(f"Erro ao listar usuários: {e}")
        return []


# ==================== FUNÇÕES PARA FUNCIONÁRIOS ====================

def get_funcionario_by_rgm(rgm):
    """Busca funcionário pelo RGM"""
    try:
        return db.funcionarios.find_one({'rgm': rgm}, {'_id': 0})
    except Exception as e:
        print(f"Erro ao buscar funcionário: {e}")
        return None


def listar_funcionarios(unidade=None):
    """Lista todos os funcionários, opcionalmente filtrando por unidade"""
    try:
        filtro = {}
        if unidade:
            filtro['unidade'] = unidade
        return list(db.funcionarios.find(filtro, {'_id': 0}).sort('nome', 1))
    except Exception as e:
        print(f"Erro ao listar funcionários: {e}")
        return []


def cadastrar_funcionario(dados):
    """Cadastra um novo funcionário"""
    try:
        from datetime import datetime
        
        # Verificar campos obrigatórios
        nome = dados.get('nome', '').strip()
        rgm = dados.get('rgm', '').strip()
        telefone = dados.get('telefone', '').strip()
        unidade = dados.get('unidade', '')
        funcao = dados.get('funcao', '')
        
        if not nome or not rgm or not unidade or not funcao or not telefone:
            return {'sucesso': False, 'erro': 'Todos os campos são obrigatórios'}
        
        funcionario = {
            'nome': nome,
            'rgm': rgm,
            'telefone': telefone,
            'unidade': unidade,
            'funcao': funcao,
            'data_cadastro': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Verificar se já existe
        if db.funcionarios.find_one({'rgm': funcionario['rgm']}):
            return {'sucesso': False, 'erro': 'RGM já cadastrado'}
        
        db.funcionarios.insert_one(funcionario)
        return {'sucesso': True, 'mensagem': 'Funcionário cadastrado com sucesso'}
        
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}


def atualizar_funcionario(rgm, dados):
    """Atualiza um funcionário existente"""
    try:
        from datetime import datetime
        
        # Verificar campos obrigatórios
        nome = dados.get('nome', '').strip()
        telefone = dados.get('telefone', '').strip()
        unidade = dados.get('unidade', '')
        funcao = dados.get('funcao', '')
        
        if not nome or not unidade or not funcao or not telefone:
            return {'sucesso': False, 'erro': 'Todos os campos são obrigatórios'}
        
        dados_atualizacao = {
            'nome': nome,
            'telefone': telefone,
            'unidade': unidade,
            'funcao': funcao,
            'data_atualizacao': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        resultado = db.funcionarios.update_one(
            {'rgm': rgm},
            {'$set': dados_atualizacao}
        )
        
        if resultado.matched_count == 0:
            return {'sucesso': False, 'erro': 'Funcionário não encontrado'}
        
        return {'sucesso': True, 'mensagem': 'Funcionário atualizado com sucesso'}
        
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}


def excluir_funcionario(rgm):
    """Exclui um funcionário pelo RGM"""
    try:
        resultado = db.funcionarios.delete_one({'rgm': rgm})
        if resultado.deleted_count == 0:
            return {'sucesso': False, 'erro': 'Funcionário não encontrado'}
        return {'sucesso': True, 'mensagem': 'Funcionário excluído com sucesso'}
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}


# ==================== FUNÇÕES PARA ALUNOS ====================

def get_aluno_by_num_inscricao(num_inscricao):
    """Busca aluno pelo número de inscrição"""
    try:
        return db.alunos.find_one({'num_inscricao': num_inscricao}, {'_id': 0})
    except Exception as e:
        print(f"Erro ao buscar aluno: {e}")
        return None


def listar_alunos(filtro=None):
    """Lista todos os alunos"""
    try:
        if filtro is None:
            filtro = {}
        return list(db.alunos.find(filtro, {'_id': 0}).sort('dados_pessoais.nome', 1))
    except Exception as e:
        print(f"Erro ao listar alunos: {e}")
        return []


def cadastrar_aluno(dados):
    """Cadastra um novo aluno com verificação de duplicidade"""
    try:
        from datetime import datetime
        
        nome = dados.get('dados_pessoais', {}).get('nome', '').strip()
        ra = dados.get('dados_pessoais', {}).get('ra', '').strip()
        
        # Verificar duplicidade antes de cadastrar
        verificacao = verificar_duplicidade_aluno(nome=nome, ra=ra)
        if verificacao['existe']:
            return {'sucesso': False, 'erro': verificacao['mensagem']}
        
        # Gerar número de inscrição se não tiver
        if not dados.get('num_inscricao'):
            ano = datetime.now().year
            ultimo = db.alunos.find_one({'num_inscricao': {'$regex': f'^[0-9]+-{ano}$'}}, sort=[('num_inscricao', -1)])
            if ultimo:
                numero = int(ultimo['num_inscricao'].split('-')[0]) + 1
            else:
                numero = 1
            dados['num_inscricao'] = f"{numero:03d}-{ano}"
        
        dados['data_cadastro'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        db.alunos.insert_one(dados)
        return {'sucesso': True, 'num_inscricao': dados['num_inscricao']}
        
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}


def atualizar_aluno(num_inscricao, dados):
    """Atualiza um aluno existente com verificação de duplicidade"""
    try:
        from datetime import datetime
        
        nome = dados.get('dados_pessoais', {}).get('nome', '').strip()
        ra = dados.get('dados_pessoais', {}).get('ra', '').strip()
        
        # Verificar duplicidade ignorando o próprio aluno
        verificacao = verificar_duplicidade_aluno(nome=nome, ra=ra, num_inscricao_ignore=num_inscricao)
        if verificacao['existe']:
            return {'sucesso': False, 'erro': verificacao['mensagem']}
        
        dados['data_atualizacao'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        resultado = db.alunos.update_one(
            {'num_inscricao': num_inscricao},
            {'$set': dados}
        )
        
        if resultado.modified_count == 0:
            return {'sucesso': False, 'erro': 'Aluno não encontrado ou nenhuma alteração'}
        return {'sucesso': True, 'mensagem': 'Aluno atualizado com sucesso'}
        
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}


def excluir_aluno(num_inscricao):
    """Exclui um aluno pelo número de inscrição"""
    try:
        resultado = db.alunos.delete_one({'num_inscricao': num_inscricao})
        if resultado.deleted_count == 0:
            return {'sucesso': False, 'erro': 'Aluno não encontrado'}
        return {'sucesso': True, 'mensagem': 'Aluno excluído com sucesso'}
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}


# ==================== FUNÇÕES PARA ARQUIVOS (LEGADO - DEPRECATED) ====================

def salvar_arquivo(num_inscricao, campo, data_url, nome_arquivo=None):
    """Salva referência de um arquivo no banco de dados (LEGADO - Use GridFS para arquivos grandes)"""
    try:
        from datetime import datetime
        
        arquivo = {
            'num_inscricao': num_inscricao,
            'campo': campo,
            'data_url': data_url,
            'nome_arquivo': nome_arquivo,
            'data_upload': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Remover arquivo anterior se existir
        db.arquivos.delete_many({'num_inscricao': num_inscricao, 'campo': campo})
        
        # Inserir novo arquivo
        db.arquivos.insert_one(arquivo)
        return {'sucesso': True}
        
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}


def get_arquivo(num_inscricao, campo):
    """Recupera um arquivo do banco de dados (LEGADO - Use GridFS para arquivos grandes)"""
    try:
        return db.arquivos.find_one(
            {'num_inscricao': num_inscricao, 'campo': campo},
            {'_id': 0}
        )
    except Exception as e:
        print(f"Erro ao buscar arquivo: {e}")
        return None


def listar_arquivos_aluno(num_inscricao):
    """Lista todos os arquivos de um aluno (LEGADO - Use GridFS para arquivos grandes)"""
    try:
        return list(db.arquivos.find(
            {'num_inscricao': num_inscricao},
            {'_id': 0}
        ))
    except Exception as e:
        print(f"Erro ao listar arquivos: {e}")
        return []