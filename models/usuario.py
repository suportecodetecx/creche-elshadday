# models/usuario.py
from database.mongo import db
from datetime import datetime
from bson.objectid import ObjectId
import bcrypt

class Usuario:
    PERFIS = {
        'admin': {'nome': 'Administrador', 'descricao': 'Acesso total ao sistema', 'cor': '#E50914'},
        'pedagogico': {'nome': 'Pedagógico', 'descricao': 'Acesso a alunos, cadastros e documentos', 'cor': '#0080FF'},
        'secretaria': {'nome': 'Secretaria', 'descricao': 'Cadastro e documentos', 'cor': '#4ECDC4'},
        'colaborador': {'nome': 'Colaborador', 'descricao': 'Visualização apenas', 'cor': '#A06CD5'}
    }
    
    def __init__(self):
        self.collection = db.get_collection('usuarios')
    
    def criar_usuario(self, email, senha, perfil, nome):
        """
        Cria um novo usuário no sistema
        """
        # Verifica se já existe
        if self.collection.find_one({'email': email}):
            raise Exception('E-mail já cadastrado')
        
        # Verifica se o perfil é válido
        if perfil not in self.PERFIS:
            raise Exception('Perfil inválido')
        
        # Criptografa a senha
        salt = bcrypt.gensalt()
        senha_hash = bcrypt.hashpw(senha.encode('utf-8'), salt)
        
        usuario = {
            'email': email,
            'senha': senha_hash,
            'perfil': perfil,
            'nome': nome,
            'data_cadastro': datetime.now(),
            'data_atualizacao': datetime.now(),
            'status': 'ativo',
            'permissoes': self._get_permissoes_por_perfil(perfil)
        }
        
        result = self.collection.insert_one(usuario)
        print(f"✅ Usuário criado: {email} - Perfil: {perfil}")
        return result
    
    def autenticar(self, email, senha):
        """
        Autentica um usuário com email e senha
        Retorna o usuário se autenticado, None caso contrário
        """
        usuario = self.collection.find_one({'email': email, 'status': 'ativo'})
        if usuario:
            try:
                if bcrypt.checkpw(senha.encode('utf-8'), usuario['senha']):
                    print(f"✅ Usuário autenticado: {email}")
                    return usuario
                else:
                    print(f"❌ Senha incorreta para: {email}")
            except Exception as e:
                print(f"❌ Erro na autenticação: {e}")
                return None
        else:
            print(f"❌ Usuário não encontrado: {email}")
        return None
    
    def _get_permissoes_por_perfil(self, perfil):
        """
        Retorna as permissões baseadas no perfil do usuário
        """
        permissoes = {
            'admin': ['*'],
            'pedagogico': ['ver_alunos', 'editar_alunos', 'ver_documentos', 'gerar_termos'],
            'colaborador': ['ver_alunos', 'ver_documentos'],
            'secretaria': ['ver_alunos', 'editar_alunos', 'ver_documentos', 'gerar_termos']
        }
        return permissoes.get(perfil, [])
    
    def verificar_permissao(self, usuario, permissao):
        """
        Verifica se um usuário tem determinada permissão
        """
        if '*' in usuario.get('permissoes', []):
            return True
        return permissao in usuario.get('permissoes', [])
    
    def listar_usuarios(self, filtro=None):
        """
        Lista todos os usuários (exceto a senha)
        """
        query = filtro if filtro else {}
        usuarios = list(self.collection.find(query))
        for usuario in usuarios:
            usuario['_id'] = str(usuario['_id'])
            usuario.pop('senha', None)  # Remove a senha
            # Adiciona informações do perfil
            if usuario.get('perfil') in self.PERFIS:
                usuario['perfil_info'] = self.PERFIS[usuario['perfil']]
        return usuarios
    
    def atualizar_usuario(self, user_id, dados):
        """
        Atualiza os dados de um usuário
        """
        dados['data_atualizacao'] = datetime.now()
        
        # Se tiver senha, criptografa
        if 'senha' in dados and dados['senha']:
            salt = bcrypt.gensalt()
            dados['senha'] = bcrypt.hashpw(dados['senha'].encode('utf-8'), salt)
        else:
            dados.pop('senha', None)
        
        # Remove campos que não podem ser atualizados
        dados.pop('_id', None)
        dados.pop('data_cadastro', None)
        
        result = self.collection.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': dados}
        )
        return result
    
    def desativar_usuario(self, user_id):
        """
        Desativa um usuário (soft delete)
        """
        result = self.collection.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'status': 'inativo', 'data_atualizacao': datetime.now()}}
        )
        return result
    
    def reativar_usuario(self, user_id):
        """
        Reativa um usuário
        """
        result = self.collection.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'status': 'ativo', 'data_atualizacao': datetime.now()}}
        )
        return result
    
    def get_usuario_by_id(self, user_id):
        """
        Busca um usuário pelo ID
        """
        usuario = self.collection.find_one({'_id': ObjectId(user_id)})
        if usuario:
            usuario['_id'] = str(usuario['_id'])
            usuario.pop('senha', None)
        return usuario
    
    def get_usuario_by_email(self, email):
        """
        Busca um usuário pelo email
        """
        usuario = self.collection.find_one({'email': email})
        if usuario:
            usuario['_id'] = str(usuario['_id'])
            usuario.pop('senha', None)
        return usuario
    
    def contar_usuarios(self):
        """
        Conta o total de usuários ativos
        """
        return self.collection.count_documents({'status': 'ativo'})
    
    def contar_por_perfil(self):
        """
        Conta usuários por perfil
        """
        result = {}
        for perfil in self.PERFIS.keys():
            result[perfil] = self.collection.count_documents({'perfil': perfil, 'status': 'ativo'})
        return result