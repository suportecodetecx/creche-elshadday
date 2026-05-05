from database.mongo import db
from datetime import datetime
from bson.objectid import ObjectId

class Mensagem:
    def __init__(self):
        self.collection = db.get_collection('mensagens')
        self.conversas_collection = db.get_collection('conversas')
        
        # Criar índices
        self.collection.create_index([('conversa_id', 1), ('criado_em', -1)])
        self.collection.create_index([('para_quem', 1), ('lida', 1)])
        self.conversas_collection.create_index([('participantes', 1)])
    
    def enviar_mensagem(self, de_quem, para_quem, mensagem, anexo=None, tipo='texto'):
        """Envia mensagem com ou sem anexo"""
        participantes = sorted([str(de_quem), str(para_quem)])
        conversa = self.conversas_collection.find_one({'participantes': participantes})
        
        if not conversa:
            conversa_id = self.conversas_collection.insert_one({
                'participantes': participantes,
                'ultima_mensagem': mensagem,
                'ultima_atualizacao': datetime.now(),
                'criado_em': datetime.now()
            }).inserted_id
        else:
            conversa_id = conversa['_id']
            self.conversas_collection.update_one(
                {'_id': conversa_id},
                {'$set': {'ultima_mensagem': mensagem, 'ultima_atualizacao': datetime.now()}}
            )
        
        msg = {
            'conversa_id': ObjectId(conversa_id),
            'de_quem': str(de_quem),
            'para_quem': str(para_quem),
            'mensagem': mensagem,
            'tipo': tipo,
            'lida': False,
            'criado_em': datetime.now()
        }
        
        if anexo:
            msg['anexo'] = anexo
        
        self.collection.insert_one(msg)
        return str(conversa_id)
    
    def get_conversas_usuario(self, usuario_id, unidade=None):
        """Retorna conversas do usuário (professor ou pedagoga)"""
        query = {'participantes': str(usuario_id)}
        conversas = self.conversas_collection.find(query).sort('ultima_atualizacao', -1)
        
        resultado = []
        from models.usuario import Usuario
        usuario_model = Usuario()
        
        for conv in conversas:
            outro_id = [p for p in conv['participantes'] if p != str(usuario_id)][0]
            outro = usuario_model.get_usuario_by_id(outro_id)
            
            if outro:
                nao_lidas = self.collection.count_documents({
                    'conversa_id': conv['_id'],
                    'para_quem': str(usuario_id),
                    'lida': False
                })
                
                resultado.append({
                    '_id': str(conv['_id']),
                    'contato': {
                        'id': str(outro['_id']),
                        'nome': outro.get('nome', 'Usuário'),
                        'nome_usuario': outro.get('nome_usuario', ''),
                        'perfil': outro.get('perfil', 'colaborador')
                    },
                    'ultima_mensagem': conv.get('ultima_mensagem', ''),
                    'ultima_atualizacao': conv['ultima_atualizacao'],
                    'nao_lidas': nao_lidas
                })
        
        return resultado
    
    def get_mensagens_conversa(self, conversa_id, usuario_id):
        """Retorna mensagens de uma conversa"""
        msgs = self.collection.find({'conversa_id': ObjectId(conversa_id)}).sort('criado_em', 1)
        
        # Marcar como lidas
        self.collection.update_many(
            {'conversa_id': ObjectId(conversa_id), 'para_quem': str(usuario_id), 'lida': False},
            {'$set': {'lida': True, 'lida_em': datetime.now()}}
        )
        
        resultado = []
        for msg in msgs:
            resultado.append({
                '_id': str(msg['_id']),
                'de': msg['de_quem'],
                'para': msg['para_quem'],
                'mensagem': msg['mensagem'],
                'tipo': msg.get('tipo', 'texto'),
                'anexo': msg.get('anexo'),
                'criado_em': msg['criado_em'].strftime('%d/%m/%Y %H:%M')
            })
        return resultado
    
    def get_pedagoga_por_unidade(self, unidade):
        """Encontra a pedagoga responsável pela unidade"""
        from models.usuario import Usuario
        usuario_model = Usuario()
        
        # Buscar usuário com perfil pedagógico da unidade
        pedagoga = usuario_model.collection.find_one({
            'perfil': {'$in': ['pedagogico', 'admin']},
            'unidade': unidade,
            'status': 'ativo'
        })
        
        if pedagoga:
            return str(pedagoga['_id']), pedagoga.get('nome', 'Pedagoga')
        
        # Se não encontrar, busca admin master
        admin = usuario_model.collection.find_one({
            'perfil': 'admin',
            'status': 'ativo'
        })
        if admin:
            return str(admin['_id']), admin.get('nome', 'Administrador')
        
        return None, None
