#!/usr/bin/env python3
from database.mongo import db
from datetime import datetime, timedelta
import sys

def gerenciar_licenca():
    if len(sys.argv) < 2:
        print("""
╔══════════════════════════════════════════════════════════╗
║          GERENCIADOR DE LICENÇA - CRECHE EL SHADDAY      ║
╚══════════════════════════════════════════════════════════╝

📋 COMANDOS:

  status              - Ver status atual da licença
  reset <dias>        - Resetar licença por X dias (padrão 30)
  expirar             - Forçar expiração imediata (modo teste)
  renovar <dias>      - Renovar por X dias
  set <YYYY-MM-DD>    - Definir data específica

📝 EXEMPLOS:
  python gerenciar_licenca.py status
  python gerenciar_licenca.py reset 60
  python gerenciar_licenca.py renovar 90
  python gerenciar_licenca.py set 2027-12-31
""")
        return
    
    comando = sys.argv[1]
    licenca_col = db.get_collection('licenca')
    
    if comando == 'status':
        config = licenca_col.find_one({'_id': 'config'})
        if config and config.get('data_expiracao'):
            exp = config['data_expiracao']
            hoje = datetime.now()
            dias = (exp - hoje).days
            print(f"""
╔════════════════════════════════════════════╗
║           STATUS DA LICENÇA                ║
╠════════════════════════════════════════════╣
║ Status:     {'✅ ATIVA' if dias > 0 else '❌ EXPIRADA'}
║ Dias rest:  {dias}
║ Expira em:  {exp.strftime('%d/%m/%Y')}
╚════════════════════════════════════════════╝
""")
        else:
            print("❌ Nenhuma licença configurada")
    
    elif comando == 'reset':
        dias = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        nova_data = datetime.now() + timedelta(days=dias)
        licenca_col.update_one(
            {'_id': 'config'},
            {'$set': {'data_expiracao': nova_data}},
            upsert=True
        )
        print(f"✅ Licença resetada! Expira em: {nova_data.strftime('%d/%m/%Y')} (+{dias} dias)")
    
    elif comando == 'expirar':
        data_passada = datetime.now() - timedelta(days=1)
        licenca_col.update_one(
            {'_id': 'config'},
            {'$set': {'data_expiracao': data_passada}},
            upsert=True
        )
        print(f"⚠️ Licença expirada em: {data_passada.strftime('%d/%m/%Y')}")
    
    elif comando == 'renovar':
        if len(sys.argv) < 3:
            print("❌ Informe os dias: python gerenciar_licenca.py renovar <dias>")
            return
        dias = int(sys.argv[2])
        config = licenca_col.find_one({'_id': 'config'})
        if config and config.get('data_expiracao'):
            nova_data = max(config['data_expiracao'], datetime.now()) + timedelta(days=dias)
        else:
            nova_data = datetime.now() + timedelta(days=dias)
        licenca_col.update_one(
            {'_id': 'config'},
            {'$set': {'data_expiracao': nova_data}},
            upsert=True
        )
        print(f"✅ Licença renovada! Expira em: {nova_data.strftime('%d/%m/%Y')} (+{dias} dias)")
    
    elif comando == 'set':
        if len(sys.argv) < 3:
            print("❌ Informe a data: python gerenciar_licenca.py set 2027-12-31")
            return
        data_str = sys.argv[2]
        try:
            nova_data = datetime.strptime(data_str, '%Y-%m-%d')
            licenca_col.update_one(
                {'_id': 'config'},
                {'$set': {'data_expiracao': nova_data}},
                upsert=True
            )
            print(f"✅ Data definida: {nova_data.strftime('%d/%m/%Y')}")
        except:
            print("❌ Formato inválido. Use YYYY-MM-DD (ex: 2027-12-31)")
    
    else:
        print(f"❌ Comando desconhecido: {comando}")

if __name__ == '__main__':
    gerenciar_licenca()
