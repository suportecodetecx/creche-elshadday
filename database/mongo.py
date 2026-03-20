from pymongo import MongoClient
import os
from dotenv import load_dotenv

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
            
            # Testar conexão
            try:
                # Tenta um comando simples para testar a conexão
                cls._instance.client.admin.command('ping')
                print("✅ Conectado ao MongoDB Atlas com sucesso!")
                print(f"📦 Banco de dados: {db_name}")
                
                # Lista as coleções existentes
                collections = cls._instance.db.list_collection_names()
                print(f"📚 Coleções existentes: {collections}")
                
            except Exception as e:
                print(f"❌ Erro ao conectar ao MongoDB: {e}")
                
        return cls._instance
    
    def get_collection(self, name):
        return self.db[name]

# Instância global
db = MongoDB()