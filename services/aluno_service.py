from database.mongo import db
from datetime import datetime
from bson.objectid import ObjectId
import os
import base64
import re

class AlunoService:
    def __init__(self):
        self.collection = db.get_collection('alunos')
        self.contador_collection = db.get_collection('contadores')
    
    def _converter_data_url_para_base64(self, data_url):
        """Converte uma data URL para dados Base64 puros"""
        if not data_url or not data_url.startswith('data:'):
            return None
        
        try:
            # Extrai o tipo e os dados
            match = re.match(r'data:([^;]+);base64,(.+)', data_url)
            if match:
                mime_type = match.group(1)
                dados_base64 = match.group(2)
                
                # Extrai a extensão do tipo MIME
                if 'image/jpeg' in mime_type or 'image/jpg' in mime_type:
                    tipo = 'jpg'
                elif 'image/png' in mime_type:
                    tipo = 'png'
                elif 'image/gif' in mime_type:
                    tipo = 'gif'
                else:
                    tipo = 'jpg'
                
                return {
                    'dados': dados_base64,
                    'tipo': tipo,
                    'mime_type': mime_type
                }
        except Exception as e:
            print(f"❌ Erro ao converter data_url: {e}")
        
        return None
    
    def _processar_arquivos_frontend(self, request_files, request_form):
        """Processa arquivos vindos do frontend (apenas fotos)"""
        arquivos_processados = []
        
        # Mapeamento dos campos de foto
        campos_foto = [
            'foto_aluno',
            'foto_responsavel1', 'foto_responsavel2', 'foto_responsavel3',
            'foto_responsavel4', 'foto_responsavel5',
            'foto_terceiro1', 'foto_terceiro2', 'foto_terceiro3',
            'foto_terceiro4', 'foto_terceiro5', 'foto_terceiro6',
            'foto_terceiro7', 'foto_terceiro8', 'foto_terceiro9', 'foto_terceiro10',
            'foto_transporte'
        ]
        
        # Primeiro, processa arquivos reais (enviados como File)
        for campo in campos_foto:
            if campo in request_files:
                file = request_files[campo]
                if file and file.filename:
                    # 🔥 VALIDAÇÃO: SÓ ACEITA IMAGENS
                    if not file.content_type.startswith('image/'):
                        print(f"   ⚠️ Arquivo ignorado (não é imagem): {campo} - {file.content_type}")
                        continue
                    
                    try:
                        file_data = file.read()
                        base64_data = base64.b64encode(file_data).decode('utf-8')
                        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'jpg'
                        
                        # Verifica tamanho (máx 5MB)
                        if len(file_data) > 5 * 1024 * 1024:
                            print(f"   ⚠️ Arquivo ignorado (muito grande): {campo} - {len(file_data)} bytes")
                            continue
                        
                        arquivos_processados.append({
                            'campo': campo,
                            'nome': f"{campo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}",
                            'dados': base64_data,
                            'tipo': ext,
                            'tamanho': len(file_data)
                        })
                        print(f"   ✅ Foto processada: {campo}")
                    except Exception as e:
                        print(f"   ❌ Erro ao processar foto {campo}: {e}")
        
        # Depois, processa data_urls que podem vir do formulário
        for campo in campos_foto:
            data_url_key = f"{campo}_data_url"
            if data_url_key in request_form and request_form[data_url_key]:
                data_url = request_form[data_url_key]
                converted = self._converter_data_url_para_base64(data_url)
                if converted:
                    arquivos_processados.append({
                        'campo': campo,
                        'nome': f"{campo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{converted['tipo']}",
                        'dados': converted['dados'],
                        'tipo': converted['tipo'],
                        'tamanho': len(converted['dados'])
                    })
                    print(f"   ✅ Data URL processada: {campo}")
        
        # 🔥 REMOVIDOS: Campos de documentos (certidão, RG, vacinação, laudos, etc)
        # Agora apenas fotos são processadas
        
        return arquivos_processados
    
    def get_proximo_numero_inscricao(self):
        """Gera o próximo número de inscrição sequencial"""
        contador = self.contador_collection.find_one_and_update(
            {'nome': 'num_inscricao'},
            {'$inc': {'valor': 1}},
            upsert=True,
            return_document=True
        )
        
        if not contador:
            self.contador_collection.insert_one({'nome': 'num_inscricao', 'valor': 1})
            valor = 1
        else:
            valor = contador['valor']
        
        ano = datetime.now().year
        return f"{str(valor).zfill(3)}-{ano}"
    
    def salvar_aluno(self, dados_form, arquivos):
        """Salva os dados do aluno no banco (apenas fotos)"""
        
        # Gera número de inscrição
        num_inscricao = self.get_proximo_numero_inscricao()
        print(f"📌 Novo número de inscrição gerado: {num_inscricao}")
        
        # Processa arquivos - APENAS FOTOS
        arquivos_processados = []
        if arquivos:
            print(f"📁 Processando {len(arquivos)} fotos...")
            for idx, arq in enumerate(arquivos):
                # VERIFICAÇÃO CRÍTICA: Garantir que tem o campo 'campo'
                if not arq.get('campo'):
                    print(f"   ❌ Foto #{idx+1} NÃO TEM CAMPO! Conteúdo: {arq}")
                    continue
                
                # Verifica se é imagem
                if arq.get('tipo') not in ['jpg', 'jpeg', 'png', 'gif']:
                    print(f"   ⚠️ Foto ignorada (formato não suportado): {arq.get('campo')} - {arq.get('tipo')}")
                    continue
                
                # Se já tem dados em Base64, mantém
                if arq.get('dados'):
                    arquivos_processados.append(arq)
                    print(f"   ✅ Foto em Base64: {arq['campo']} - {arq.get('nome', 'sem_nome')}")
        
        # Prepara o documento do aluno
        aluno = {
            'num_inscricao': num_inscricao,
            'data_cadastro': datetime.now(),
            'status': 'ativo',
            
            'dados_pessoais': {
                'nome': dados_form.get('nome'),
                'data_nasc': dados_form.get('data_nasc'),
                'sexo': dados_form.get('sexo'),
                'raca': dados_form.get('raca'),
                'naturalidade': dados_form.get('naturalidade'),
                'nacionalidade': dados_form.get('nacionalidade', 'Brasileira'),
                'ra': dados_form.get('ra')
            },
            
            'endereco': {
                'cep': dados_form.get('cep'),
                'logradouro': dados_form.get('endereco'),
                'numero': dados_form.get('numero'),
                'complemento': dados_form.get('complemento'),
                'bairro': dados_form.get('bairro'),
                'cidade': dados_form.get('cidade'),
                'uf': dados_form.get('uf')
            },
            
            'turma': {
                'unidade': dados_form.get('unidade'),
                'turma': dados_form.get('turma'),
                'periodo': dados_form.get('periodo'),
                'ano_letivo': dados_form.get('ano_letivo', '2026')
            },
            
            'saude': {
                'tipo_sanguineo': dados_form.get('tipo_sanguineo'),
                'plano_saude': dados_form.get('plano_saude'),
                'alergias': dados_form.get('alergias'),
                'medicamentos': dados_form.get('medicamentos'),
                'restricoes': dados_form.get('restricoes'),
                'pediatra': dados_form.get('pediatra'),
                'contato_pediatra': dados_form.get('contato_pediatra'),
                'deficiencia': dados_form.get('deficiencia') == 'sim',
                'deficiencia_desc': dados_form.get('deficiencia_desc')
            },
            
            'responsaveis': [],
            'terceiros': [],
            'transporte': None,
            'fotos': arquivos_processados,  # 🔥 RENOMEADO: 'arquivos' -> 'fotos'
            'usando_gridfs': False  # Mantém compatibilidade
        }
        
        # Adiciona responsável principal
        if dados_form.get('responsavel1_nome'):
            aluno['responsaveis'].append({
                'tipo': 'principal',
                'nome': dados_form.get('responsavel1_nome'),
                'parentesco': dados_form.get('responsavel1_parentesco'),
                'telefone': dados_form.get('responsavel1_telefone'),
                'telefone_contato': dados_form.get('responsavel1_telefone_contato'),
                'cpf': dados_form.get('responsavel1_cpf'),
                'rg': dados_form.get('responsavel1_rg'),
                'email': dados_form.get('responsavel1_email')
            })
        
        # Adiciona responsáveis adicionais (até 5)
        for i in range(2, 6):
            if dados_form.get(f'responsavel{i}_nome'):
                aluno['responsaveis'].append({
                    'tipo': 'adicional',
                    'nome': dados_form.get(f'responsavel{i}_nome'),
                    'parentesco': dados_form.get(f'responsavel{i}_parentesco'),
                    'telefone': dados_form.get(f'responsavel{i}_telefone'),
                    'telefone_contato': dados_form.get(f'responsavel{i}_telefone_contato'),
                    'cpf': dados_form.get(f'responsavel{i}_cpf'),
                    'rg': dados_form.get(f'responsavel{i}_rg'),
                    'email': dados_form.get(f'responsavel{i}_email')
                })
        
        # Adiciona terceiros (até 10)
        for i in range(1, 11):
            if dados_form.get(f'terceiro{i}_nome'):
                aluno['terceiros'].append({
                    'nome': dados_form.get(f'terceiro{i}_nome'),
                    'telefone': dados_form.get(f'terceiro{i}_telefone'),
                    'cpf': dados_form.get(f'terceiro{i}_cpf'),
                    'rg': dados_form.get(f'terceiro{i}_rg'),
                    'email': dados_form.get(f'terceiro{i}_email')
                })
        
        # Adiciona transporte se existir
        if dados_form.get('utiliza_transporte') == '1':
            aluno['transporte'] = {
                'nome': dados_form.get('transporte_nome'),
                'cnpj': dados_form.get('transporte_cnpj'),
                'cpf': dados_form.get('transporte_cpf'),
                'rg': dados_form.get('transporte_rg'),
                'telefone': dados_form.get('transporte_telefone'),
                'email': dados_form.get('transporte_email')
            }
        
        # Insere no banco
        result = self.collection.insert_one(aluno)
        print(f"✅ Aluno salvo com ID: {result.inserted_id}")
        print(f"📷 Fotos salvas: {len(arquivos_processados)}")
        
        return {
            'id': str(result.inserted_id),
            'num_inscricao': num_inscricao
        }
    
    def atualizar_aluno(self, num_inscricao_original, dados_form, novos_arquivos):
        """Atualiza os dados de um aluno existente (apenas fotos)"""
        try:
            print(f"📝 Atualizando aluno: {num_inscricao_original}")
            
            # Busca o aluno original
            aluno_original = self.get_aluno_by_inscricao(num_inscricao_original)
            if not aluno_original:
                raise Exception("Aluno não encontrado")
            
            # Processa novas fotos
            novos_arquivos_processados = []
            if novos_arquivos:
                for idx, arq in enumerate(novos_arquivos):
                    if not arq.get('campo'):
                        print(f"   ❌ Nova foto #{idx+1} NÃO TEM CAMPO! Conteúdo: {arq}")
                        continue
                    
                    # Verifica se é imagem
                    if arq.get('tipo') not in ['jpg', 'jpeg', 'png', 'gif']:
                        print(f"   ⚠️ Foto ignorada (formato não suportado): {arq.get('campo')}")
                        continue
                    
                    if arq.get('dados'):
                        novos_arquivos_processados.append(arq)
                        print(f"   ✅ Nova foto: {arq['campo']} - {arq.get('nome', 'sem_nome')}")
            
            # Prepara os dados atualizados
            aluno_atualizado = {
                'num_inscricao': num_inscricao_original,
                'data_cadastro': aluno_original.get('data_cadastro', datetime.now()),
                'data_atualizacao': datetime.now(),
                'status': 'ativo',
                
                'dados_pessoais': {
                    'nome': dados_form.get('nome'),
                    'data_nasc': dados_form.get('data_nasc'),
                    'sexo': dados_form.get('sexo'),
                    'raca': dados_form.get('raca'),
                    'naturalidade': dados_form.get('naturalidade'),
                    'nacionalidade': dados_form.get('nacionalidade', 'Brasileira'),
                    'ra': dados_form.get('ra')
                },
                
                'endereco': {
                    'cep': dados_form.get('cep'),
                    'logradouro': dados_form.get('endereco'),
                    'numero': dados_form.get('numero'),
                    'complemento': dados_form.get('complemento'),
                    'bairro': dados_form.get('bairro'),
                    'cidade': dados_form.get('cidade'),
                    'uf': dados_form.get('uf')
                },
                
                'turma': {
                    'unidade': dados_form.get('unidade'),
                    'turma': dados_form.get('turma'),
                    'periodo': dados_form.get('periodo'),
                    'ano_letivo': dados_form.get('ano_letivo', '2026')
                },
                
                'saude': {
                    'tipo_sanguineo': dados_form.get('tipo_sanguineo'),
                    'plano_saude': dados_form.get('plano_saude'),
                    'alergias': dados_form.get('alergias'),
                    'medicamentos': dados_form.get('medicamentos'),
                    'restricoes': dados_form.get('restricoes'),
                    'pediatra': dados_form.get('pediatra'),
                    'contato_pediatra': dados_form.get('contato_pediatra'),
                    'deficiencia': dados_form.get('deficiencia') == 'sim',
                    'deficiencia_desc': dados_form.get('deficiencia_desc')
                },
                
                'responsaveis': [],
                'terceiros': [],
                'transporte': None
            }
            
            # Adiciona responsável principal
            if dados_form.get('responsavel1_nome'):
                aluno_atualizado['responsaveis'].append({
                    'tipo': 'principal',
                    'nome': dados_form.get('responsavel1_nome'),
                    'parentesco': dados_form.get('responsavel1_parentesco'),
                    'telefone': dados_form.get('responsavel1_telefone'),
                    'telefone_contato': dados_form.get('responsavel1_telefone_contato'),
                    'cpf': dados_form.get('responsavel1_cpf'),
                    'rg': dados_form.get('responsavel1_rg'),
                    'email': dados_form.get('responsavel1_email')
                })
            
            # Adiciona responsáveis adicionais (até 5)
            for i in range(2, 6):
                if dados_form.get(f'responsavel{i}_nome'):
                    aluno_atualizado['responsaveis'].append({
                        'tipo': 'adicional',
                        'nome': dados_form.get(f'responsavel{i}_nome'),
                        'parentesco': dados_form.get(f'responsavel{i}_parentesco'),
                        'telefone': dados_form.get(f'responsavel{i}_telefone'),
                        'telefone_contato': dados_form.get(f'responsavel{i}_telefone_contato'),
                        'cpf': dados_form.get(f'responsavel{i}_cpf'),
                        'rg': dados_form.get(f'responsavel{i}_rg'),
                        'email': dados_form.get(f'responsavel{i}_email')
                    })
            
            # Adiciona terceiros (até 10)
            for i in range(1, 11):
                if dados_form.get(f'terceiro{i}_nome'):
                    aluno_atualizado['terceiros'].append({
                        'nome': dados_form.get(f'terceiro{i}_nome'),
                        'telefone': dados_form.get(f'terceiro{i}_telefone'),
                        'cpf': dados_form.get(f'terceiro{i}_cpf'),
                        'rg': dados_form.get(f'terceiro{i}_rg'),
                        'email': dados_form.get(f'terceiro{i}_email')
                    })
            
            # Adiciona transporte se existir
            if dados_form.get('utiliza_transporte') == '1':
                aluno_atualizado['transporte'] = {
                    'nome': dados_form.get('transporte_nome'),
                    'cnpj': dados_form.get('transporte_cnpj'),
                    'cpf': dados_form.get('transporte_cpf'),
                    'rg': dados_form.get('transporte_rg'),
                    'telefone': dados_form.get('transporte_telefone'),
                    'email': dados_form.get('transporte_email')
                }
            
            # ===== PROCESSAMENTO DE FOTOS NA EDIÇÃO =====
            # Mantém fotos antigas que NÃO foram substituídas
            fotos_manter = []
            campos_substituidos = [arq['campo'] for arq in novos_arquivos_processados]
            
            # Busca fotos antigas (pode estar em 'fotos' ou 'arquivos')
            fotos_antigas = aluno_original.get('fotos', []) or aluno_original.get('arquivos', [])
            
            for foto_antiga in fotos_antigas:
                if not foto_antiga.get('campo'):
                    print(f"   ⚠️ Foto antiga sem campo! Será mantida: {foto_antiga}")
                    fotos_manter.append(foto_antiga)
                elif foto_antiga.get('campo') not in campos_substituidos:
                    fotos_manter.append(foto_antiga)
                    print(f"   ✅ Mantendo foto: {foto_antiga['campo']} - {foto_antiga.get('nome', 'sem_nome')}")
                else:
                    print(f"   🔄 Substituindo foto: {foto_antiga.get('campo')}")
            
            # Lista final de fotos
            fotos_finais = fotos_manter + novos_arquivos_processados
            aluno_atualizado['fotos'] = fotos_finais
            aluno_atualizado['usando_gridfs'] = False
            
            print(f"\n📊 RESUMO DAS FOTOS APÓS ATUALIZAÇÃO:")
            print(f"   📷 Fotos mantidas: {len(fotos_manter)}")
            print(f"   📷 Novas fotos: {len(novos_arquivos_processados)}")
            print(f"   📷 Total: {len(fotos_finais)}")
            
            # Atualiza no banco
            result = self.collection.update_one(
                {'num_inscricao': num_inscricao_original},
                {'$set': aluno_atualizado}
            )
            
            if result.modified_count > 0:
                print(f"✅ Aluno atualizado: {num_inscricao_original}")
            else:
                print(f"⚠️ Nenhuma alteração feita em: {num_inscricao_original}")
            
            return {
                'num_inscricao': num_inscricao_original,
                'id': str(aluno_original['_id'])
            }
            
        except Exception as e:
            print(f"❌ Erro ao atualizar aluno: {str(e)}")
            import traceback
            traceback.print_exc()
            raise e
    
    def excluir_aluno(self, num_inscricao):
        """Exclui um aluno do banco de dados"""
        try:
            print(f"🗑️ Excluindo aluno do banco: {num_inscricao}")
            
            # Busca o aluno antes de excluir
            aluno = self.get_aluno_by_inscricao(num_inscricao)
            if not aluno:
                raise Exception("Aluno não encontrado")
            
            # Exclui do banco
            result = self.collection.delete_one({'num_inscricao': num_inscricao})
            
            if result.deleted_count > 0:
                print(f"✅ Aluno excluído do banco: {num_inscricao}")
                return {'sucesso': True, 'num_inscricao': num_inscricao}
            else:
                raise Exception("Erro ao excluir aluno do banco")
                
        except Exception as e:
            print(f"❌ Erro ao excluir aluno: {str(e)}")
            raise e
    
    def buscar_alunos(self, filtro=None):
        """Busca alunos no banco"""
        query = filtro if filtro else {}
        
        try:
            alunos = list(self.collection.find(query).sort('data_cadastro', -1))
            
            # Converte ObjectId para string
            for aluno in alunos:
                aluno['_id'] = str(aluno['_id'])
            
            return alunos
        except Exception as e:
            print(f"Erro ao buscar alunos: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_aluno_by_id(self, aluno_id):
        """Busca um aluno pelo ID"""
        try:
            aluno = self.collection.find_one({'_id': ObjectId(aluno_id)})
            if aluno:
                aluno['_id'] = str(aluno['_id'])
            return aluno
        except Exception as e:
            print(f"Erro ao buscar aluno por ID: {e}")
            return None
    
    def get_aluno_by_inscricao(self, num_inscricao):
        """Busca um aluno pelo número de inscrição"""
        try:
            aluno = self.collection.find_one({'num_inscricao': num_inscricao})
            if aluno:
                aluno['_id'] = str(aluno['_id'])
                # LOG para debug - mostra quantas fotos tem
                fotos = aluno.get('fotos', []) or aluno.get('arquivos', [])
                if fotos:
                    print(f"📷 Aluno {num_inscricao} tem {len(fotos)} fotos")
                    for foto in fotos:
                        print(f"   - {foto.get('campo')}: dados={bool(foto.get('dados'))}, tipo={foto.get('tipo')}")
            return aluno
        except Exception as e:
            print(f"Erro ao buscar aluno por inscrição: {e}")
            return None