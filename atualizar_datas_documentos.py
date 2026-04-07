#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para atualizar documentos antigos que não possuem o campo data_referencia
Executar: python atualizar_datas_documentos.py
"""

from database.mongo import db
from datetime import datetime

def atualizar_documentos_antigos():
    """Atualiza documentos antigos adicionando data_referencia baseada no mês/ano"""
    
    print("=" * 60)
    print("🔄 ATUALIZANDO DOCUMENTOS ANTIGOS")
    print("=" * 60)
    
    # Mapeamento de nomes de meses para números
    meses_nome_para_numero = {
        'Janeiro': '01', 'Fevereiro': '02', 'Março': '03', 'Abril': '04',
        'Maio': '05', 'Junho': '06', 'Julho': '07', 'Agosto': '08',
        'Setembro': '09', 'Outubro': '10', 'Novembro': '11', 'Dezembro': '12'
    }
    
    # Buscar documentos que não têm data_referencia
    colecao = db.db.documentos
    documentos_antigos = list(colecao.find({
        '$or': [
            {'data_referencia': {'$exists': False}},
            {'data_referencia': None},
            {'data_referencia': ''}
        ]
    }))
    
    print(f"\n📄 Encontrados {len(documentos_antigos)} documentos sem data_referencia")
    
    if len(documentos_antigos) == 0:
        print("✅ Nenhum documento precisa ser atualizado!")
        return
    
    atualizados = 0
    erros = 0
    
    for doc in documentos_antigos:
        try:
            doc_id = doc['_id']
            nome_pessoa = doc.get('nome_pessoa', 'Desconhecido')
            mes_nome = doc.get('mes', '')
            ano = doc.get('ano', '')
            
            # Determinar a data de referência
            data_referencia = None
            data_referencia_formatada = None
            
            # Tenta extrair do campo data_referencia se existir (mas vazio)
            if doc.get('data_referencia') and doc['data_referencia'] != '':
                data_referencia = doc['data_referencia']
                try:
                    data_obj = datetime.strptime(data_referencia, '%Y-%m-%d')
                    data_referencia_formatada = data_obj.strftime('%d/%m/%Y')
                except:
                    data_referencia_formatada = data_referencia
            
            # Se não tem data, tenta criar a partir do mês e ano (primeiro dia do mês)
            if not data_referencia and mes_nome and ano:
                mes_numero = meses_nome_para_numero.get(mes_nome)
                if mes_numero:
                    data_referencia = f"{ano}-{mes_numero}-01"
                    try:
                        data_obj = datetime.strptime(data_referencia, '%Y-%m-%d')
                        data_referencia_formatada = data_obj.strftime('%d/%m/%Y')
                    except:
                        data_referencia_formatada = f"01/{mes_numero}/{ano}"
                    print(f"   📅 Criada data a partir do mês/ano: {data_referencia_formatada}")
            
            # Se ainda não tem data, usa a data de upload
            if not data_referencia and doc.get('data_upload'):
                try:
                    if isinstance(doc['data_upload'], datetime):
                        data_referencia = doc['data_upload'].strftime('%Y-%m-%d')
                        data_referencia_formatada = doc['data_upload'].strftime('%d/%m/%Y')
                    else:
                        # Tenta converter string para data
                        data_obj = datetime.strptime(str(doc['data_upload'])[:10], '%Y-%m-%d')
                        data_referencia = data_obj.strftime('%Y-%m-%d')
                        data_referencia_formatada = data_obj.strftime('%d/%m/%Y')
                    print(f"   📅 Usando data de upload: {data_referencia_formatada}")
                except:
                    pass
            
            # Se não conseguiu nenhuma data, usa a data atual
            if not data_referencia:
                hoje = datetime.now()
                data_referencia = hoje.strftime('%Y-%m-%d')
                data_referencia_formatada = hoje.strftime('%d/%m/%Y')
                print(f"   📅 Usando data atual: {data_referencia_formatada}")
            
            # Atualizar o documento
            resultado = colecao.update_one(
                {'_id': doc_id},
                {
                    '$set': {
                        'data_referencia': data_referencia,
                        'data_referencia_formatada': data_referencia_formatada
                    }
                }
            )
            
            if resultado.modified_count > 0:
                atualizados += 1
                print(f"   ✅ {nome_pessoa[:30]} - {mes_nome}/{ano} -> {data_referencia_formatada}")
            else:
                print(f"   ⚠️ {nome_pessoa[:30]} - Nenhuma alteração necessária")
                
        except Exception as e:
            erros += 1
            print(f"   ❌ Erro ao atualizar documento {doc.get('_id')}: {e}")
    
    print("\n" + "=" * 60)
    print("📊 RESUMO DA ATUALIZAÇÃO")
    print("=" * 60)
    print(f"📄 Documentos processados: {len(documentos_antigos)}")
    print(f"✅ Documentos atualizados: {atualizados}")
    print(f"❌ Erros: {erros}")
    print("=" * 60)
    
    # Verificar se ainda há documentos sem data_referencia
    restantes = colecao.count_documents({
        '$or': [
            {'data_referencia': {'$exists': False}},
            {'data_referencia': None},
            {'data_referencia': ''}
        ]
    })
    
    if restantes > 0:
        print(f"\n⚠️ Ainda existem {restantes} documentos sem data_referencia")
        print("   Execute o script novamente ou verifique manualmente")
    else:
        print("\n✅ TODOS os documentos agora têm data_referencia!")


def verificar_documentos():
    """Verifica o status dos documentos"""
    print("\n" + "=" * 60)
    print("📊 VERIFICANDO STATUS DOS DOCUMENTOS")
    print("=" * 60)
    
    colecao = db.db.documentos
    total = colecao.count_documents({})
    com_data = colecao.count_documents({'data_referencia': {'$exists': True, '$ne': None, '$ne': ''}})
    sem_data = total - com_data
    
    print(f"📄 Total de documentos: {total}")
    print(f"✅ Com data_referencia: {com_data}")
    print(f"⚠️ Sem data_referencia: {sem_data}")
    
    if sem_data > 0:
        print("\n📋 Documentos sem data_referencia:")
        docs_sem_data = colecao.find(
            {'$or': [{'data_referencia': {'$exists': False}}, {'data_referencia': None}, {'data_referencia': ''}]},
            {'nome_pessoa': 1, 'mes': 1, 'ano': 1, 'data_upload': 1}
        ).limit(10)
        
        for doc in docs_sem_data:
            print(f"   - {doc.get('nome_pessoa', '?')} ({doc.get('mes', '?')}/{doc.get('ano', '?')})")


if __name__ == "__main__":
    print("\n🚀 INICIANDO SCRIPT DE ATUALIZAÇÃO DE DATAS")
    print("⚠️  Certifique-se de que o MongoDB está conectado!\n")
    
    # Verificar conexão
    try:
        db.client.admin.command('ping')
        print("✅ Conexão com MongoDB OK\n")
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        exit(1)
    
    # Verificar status atual
    verificar_documentos()
    
    # Perguntar se quer continuar
    print("\n" + "=" * 60)
    resposta = input("🔄 Deseja atualizar os documentos antigos? (s/N): ").strip().lower()
    
    if resposta == 's' or resposta == 'sim':
        atualizar_documentos_antigos()
        verificar_documentos()
    else:
        print("❌ Operação cancelada pelo usuário")
    
    print("\n🏁 SCRIPT FINALIZADO!")