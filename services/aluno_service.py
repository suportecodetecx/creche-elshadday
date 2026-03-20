from database.mongo import db
from datetime import datetime
from bson.objectid import ObjectId
import os
import traceback

class AlunoService:
    def __init__(self):
        self.collection = db.get_collection('alunos')
        self.contador_collection = db.get_collection('contadores')
    
    def get_proximo_numero_inscricao(self):
        """Gera o próximo número de inscrição sequencial - VERSÃO SIMPLIFICADA"""
        try:
            print("🔍 Buscando último aluno...")
            ano = datetime.now().year
            
            # Busca todos os alunos do ano atual
            alunos_ano = list(self.collection.find(
                {'num_inscricao': {'$regex': f'-{ano}$'}}
            ))
            
            print(f"📊 Encontrados {len(alunos_ano)} alunos no ano {ano}")
            
            if alunos_ano:
                # Extrai os números e pega o maior
                numeros = []
                for aluno in alunos_ano:
                    try:
                        num = int(aluno['num_inscricao'].split('-')[0])
                        numeros.append(num)
                        print(f"   Número encontrado: {num}")
                    except Exception as e:
                        print(f"   Erro ao processar {aluno.get('num_inscricao')}: {e}")
                        continue
                
                if numeros:
                    valor = max(numeros) + 1
                    print(f"📌 Último número: {max(numeros)}, próximo: {valor}")
                else:
                    valor = 1
                    print("📌 Nenhum número válido, começando do 1")
            else:
                valor = 1
                print("📌 Nenhum aluno encontrado, começando do 1")
            
            numero = f"{str(valor).zfill(3)}-{ano}"
            print(f"🎯 Número gerado: {numero}")
            return numero
            
        except Exception as e:
            print(f"❌ Erro ao gerar número: {e}")
            traceback.print_exc()
            # Fallback simples
            from datetime import datetime
            return f"001-{datetime.now().year}"
    
    def salvar_aluno(self, dados_form, arquivos):
        """Salva os dados do aluno no banco"""
        
        # Gera número de inscrição
        num_inscricao = self.get_proximo_numero_inscricao()
        print(f"📌 Novo número de inscrição gerado: {num_inscricao}")
        
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
            'arquivos': arquivos
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
        
        # Adiciona responsáveis adicionais
        for i in range(2, 5):
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
        
        # Adiciona terceiros
        for i in range(1, 4):
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
        
        return {
            'id': str(result.inserted_id),
            'num_inscricao': num_inscricao
        }
    
    def atualizar_aluno(self, num_inscricao_original, dados_form, novos_arquivos):
        """Atualiza os dados de um aluno existente com substituição de fotos"""
        try:
            print(f"📝 Atualizando aluno: {num_inscricao_original}")
            
            # Busca o aluno original
            aluno_original = self.get_aluno_by_inscricao(num_inscricao_original)
            if not aluno_original:
                raise Exception("Aluno não encontrado")
            
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
            
            # Adiciona responsáveis adicionais
            for i in range(2, 5):
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
            
            # Adiciona terceiros
            for i in range(1, 4):
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
            
            # Processar substituição de arquivos
            # Arquivos antigos que serão mantidos
            arquivos_manter = []
            
            # Identifica quais arquivos antigos NÃO foram substituídos
            for arquivo_antigo in aluno_original.get('arquivos', []):
                campo = arquivo_antigo['campo']
                if campo not in [na['campo'] for na in novos_arquivos]:
                    arquivos_manter.append(arquivo_antigo)
            
            # Lista final de arquivos
            arquivos_finais = arquivos_manter + novos_arquivos
            aluno_atualizado['arquivos'] = arquivos_finais
            
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
            traceback.print_exc()
            raise e
    
    def excluir_aluno(self, num_inscricao):
        """Exclui um aluno do banco de dados"""
        try:
            print(f"🗑️ Excluindo aluno do banco: {num_inscricao}")
            
            aluno = self.get_aluno_by_inscricao(num_inscricao)
            if not aluno:
                raise Exception("Aluno não encontrado")
            
            result = self.collection.delete_one({'num_inscricao': num_inscricao})
            
            if result.deleted_count > 0:
                print(f"✅ Aluno excluído do banco: {num_inscricao}")
                return {'sucesso': True, 'num_inscricao': num_inscricao}
            else:
                raise Exception("Erro ao excluir aluno do banco")
                
        except Exception as e:
            print(f"❌ Erro ao excluir aluno: {str(e)}")
            traceback.print_exc()
            raise e
    
    def buscar_alunos(self, filtro=None):
        """Busca alunos no banco"""
        query = filtro if filtro else {}
        
        try:
            alunos = list(self.collection.find(query).sort('data_cadastro', -1))
            for aluno in alunos:
                aluno['_id'] = str(aluno['_id'])
            return alunos
        except Exception as e:
            print(f"Erro ao buscar alunos: {e}")
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
            return aluno
        except Exception as e:
            print(f"Erro ao buscar aluno por inscrição: {e}")
            return None