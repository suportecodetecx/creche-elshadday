# services/termo_service.py
from services.pdf_service import PDFService
from services.aluno_service import AlunoService
from services.unidades_config import get_unidade_info
from datetime import datetime
import os
from flask import url_for

class TermoService:
    def __init__(self):
        self.pdf_service = PDFService()
        self.aluno_service = AlunoService()
    
    def get_aluno_completo(self, num_inscricao):
        """
        Busca todos os dados de um aluno pelo número de inscrição
        Esta função complementa o get_aluno_by_inscricao existente
        """
        aluno = self.aluno_service.get_aluno_by_inscricao(num_inscricao)
        if not aluno:
            return None
        
        # Garantir que todos os campos necessários existam
        if 'dados_pessoais' not in aluno:
            aluno['dados_pessoais'] = {}
        if 'endereco' not in aluno:
            aluno['endereco'] = {}
        if 'turma' not in aluno:
            aluno['turma'] = {}
        if 'saude' not in aluno:
            aluno['saude'] = {}
        if 'responsaveis' not in aluno:
            aluno['responsaveis'] = []
        if 'arquivos' not in aluno:
            aluno['arquivos'] = []
        if 'terceiros' not in aluno:
            aluno['terceiros'] = []
        if 'transporte' not in aluno:
            aluno['transporte'] = None
        
        return aluno
    
    def preparar_foto_url(self, aluno, request=None):
        """
        Prepara as URLs completas das fotos para exibição no HTML
        Corrigido para gerar URLs corretas sem duplicação de caminhos
        """
        if aluno and 'arquivos' in aluno and aluno['arquivos']:
            for arquivo in aluno['arquivos']:
                # Para qualquer arquivo que tenha caminho, gerar URL completa
                if arquivo.get('caminho'):
                    # Extrair apenas o nome do arquivo (remover qualquer caminho)
                    caminho_original = arquivo['caminho']
                    
                    # Se o caminho começa com /uploads/, extrair só o nome do arquivo
                    if '/uploads/' in caminho_original:
                        # Pega tudo depois de /uploads/
                        nome_arquivo = caminho_original.split('/uploads/')[-1]
                    else:
                        nome_arquivo = caminho_original
                    
                    # Se tiver request, gerar URL absoluta usando a rota de uploads
                    if request:
                        # Usar url_for para gerar URL correta - ajuste o nome da blueprint se necessário
                        try:
                            arquivo['caminho_completo'] = url_for('uploads.serve_upload', 
                                                                  filename=nome_arquivo, 
                                                                  _external=True)
                        except:
                            # Fallback: construir URL manualmente
                            base_url = request.host_url.rstrip('/')
                            arquivo['caminho_completo'] = f"{base_url}/uploads/{nome_arquivo}"
                    else:
                        # URL relativa para uso interno
                        arquivo['caminho_completo'] = f"/uploads/{nome_arquivo}"
                    
                    # Também manter o caminho original para compatibilidade
                    arquivo['caminho_original'] = caminho_original
                    
        return aluno
    
    def gerar_termo_matricula(self, num_inscricao):
        """Gera termo de matrícula para um aluno"""
        aluno = self.aluno_service.get_aluno_by_inscricao(num_inscricao)
        if not aluno:
            raise Exception("Aluno não encontrado")
        
        return self.pdf_service.gerar_termo_matricula(aluno)
    
    def gerar_autorizacao_imagem(self, num_inscricao):
        """Gera autorização de uso de imagem"""
        aluno = self.aluno_service.get_aluno_by_inscricao(num_inscricao)
        if not aluno:
            raise Exception("Aluno não encontrado")
        
        return self.pdf_service.gerar_autorizacao_imagem(aluno)
    
    def gerar_termo_transporte(self, num_inscricao):
        """Gera termo de transporte escolar"""
        aluno = self.aluno_service.get_aluno_by_inscricao(num_inscricao)
        if not aluno:
            raise Exception("Aluno não encontrado")
        
        if not aluno.get('transporte'):
            raise Exception("Aluno não possui transporte cadastrado")
        
        return self.pdf_service.gerar_termo_transporte(aluno)
    
    def gerar_termo_terceiro(self, num_inscricao):
        """Gera termo de autorização para terceiros"""
        aluno = self.aluno_service.get_aluno_by_inscricao(num_inscricao)
        if not aluno:
            raise Exception("Aluno não encontrado")
        
        if not aluno.get('terceiros') or len(aluno.get('terceiros', [])) == 0:
            raise Exception("Aluno não possui terceiros cadastrados")
        
        return self.pdf_service.gerar_termo_terceiro(aluno)
    
    def gerar_regulamento_interno(self, num_inscricao):
        """Gera termo de ciência do regulamento interno"""
        aluno = self.aluno_service.get_aluno_by_inscricao(num_inscricao)
        if not aluno:
            raise Exception("Aluno não encontrado")
        
        return self.pdf_service.gerar_regulamento_interno(aluno)
    
    # ===== NOVO: TERMO DE SAÚDE =====
    def gerar_termo_saude(self, num_inscricao):
        """Gera termo de saúde da criança"""
        aluno = self.aluno_service.get_aluno_by_inscricao(num_inscricao)
        if not aluno:
            raise Exception("Aluno não encontrado")
        
        # Verifica se há informações de saúde (não é obrigatório ter todas)
        # O termo pode ser gerado mesmo com dados parciais
        
        return self.pdf_service.gerar_termo_saude(aluno)
    
    def gerar_ficha_cadastral_html(self, num_inscricao, request=None):
        """
        Prepara os dados para a ficha cadastral em HTML
        Esta função não gera PDF, apenas prepara os dados para o template
        """
        aluno = self.get_aluno_completo(num_inscricao)
        if not aluno:
            raise Exception("Aluno não encontrado")
        
        # Preparar URLs das fotos
        aluno = self.preparar_foto_url(aluno, request)
        
        # Buscar informações da unidade
        unidade_nome = aluno.get('turma', {}).get('unidade', 'CEIC El Shadday')
        unidade = get_unidade_info(unidade_nome)
        
        # Dados adicionais para a ficha
        dados_ficha = {
            'aluno': aluno,
            'unidade': unidade,
            'data_atual': datetime.now().strftime('%d/%m/%Y'),
            'data_hora': datetime.now().strftime('%d/%m/%Y %H:%M'),
            'ano_letivo': aluno.get('turma', {}).get('ano_letivo', datetime.now().year),
            'request': request  # Passar request para o template se necessário
        }
        
        return dados_ficha
    
    def gerar_termo_especifico(self, num_inscricao, tipo_termo):
        """Gera um termo específico baseado no tipo"""
        mapa_termos = {
            'matricula': self.gerar_termo_matricula,
            'imagem': self.gerar_autorizacao_imagem,
            'transporte': self.gerar_termo_transporte,
            'terceiro': self.gerar_termo_terceiro,
            'regulamento': self.gerar_regulamento_interno,
            'saude': self.gerar_termo_saude  # NOVO: adicionado ao mapa
        }
        
        if tipo_termo not in mapa_termos:
            raise Exception(f"Tipo de termo inválido: {tipo_termo}")
        
        return mapa_termos[tipo_termo](num_inscricao)
    
    def gerar_todos_termos(self, num_inscricao):
        """Gera todos os termos para um aluno (pacote completo)"""
        aluno = self.aluno_service.get_aluno_by_inscricao(num_inscricao)
        if not aluno:
            raise Exception("Aluno não encontrado")
        
        termos_gerados = []
        erros = []
        
        # Função auxiliar para tentar gerar termo
        def tentar_gerar_termo(nome_termo, funcao_termo):
            try:
                arquivo = funcao_termo(aluno['num_inscricao'])
                termos_gerados.append({
                    'nome': nome_termo,
                    'arquivo': arquivo,
                    'sucesso': True
                })
                return True
            except Exception as e:
                erros.append({
                    'termo': nome_termo,
                    'erro': str(e)
                })
                return False
        
        # Sempre tenta gerar esses termos
        tentar_gerar_termo('Termo de Matrícula', self.gerar_termo_matricula)
        tentar_gerar_termo('Autorização de Imagem', self.gerar_autorizacao_imagem)
        tentar_gerar_termo('Regulamento Interno', self.gerar_regulamento_interno)
        tentar_gerar_termo('Termo de Saúde', self.gerar_termo_saude)  # NOVO: sempre tenta gerar termo de saúde
        
        # Tenta gerar termo de transporte se houver
        if aluno.get('transporte'):
            tentar_gerar_termo('Termo de Transporte', self.gerar_termo_transporte)
        
        # Tenta gerar termo de terceiros se houver
        if aluno.get('terceiros') and len(aluno.get('terceiros', [])) > 0:
            tentar_gerar_termo('Termo de Terceiros', self.gerar_termo_terceiro)
        
        return {
            'termos': termos_gerados,
            'erros': erros,
            'total_gerados': len(termos_gerados),
            'total_erros': len(erros)
        }
    
    def get_info_termos(self, num_inscricao):
        """Retorna informações sobre quais termos estão disponíveis para o aluno"""
        aluno = self.aluno_service.get_aluno_by_inscricao(num_inscricao)
        if not aluno:
            raise Exception("Aluno não encontrado")
        
        # Conta quantos termos estão disponíveis
        termos_base = 4  # matrícula, imagem, regulamento, SAÚDE (agora são 4)
        termos_opcionais = 0
        
        if aluno.get('transporte'):
            termos_opcionais += 1
        
        if aluno.get('terceiros') and len(aluno.get('terceiros', [])) > 0:
            termos_opcionais += 1
        
        return {
            'aluno': {
                'nome': aluno.get('dados_pessoais', {}).get('nome', 'N/A'),
                'num_inscricao': aluno.get('num_inscricao', 'N/A'),
                'turma': aluno.get('turma', {}).get('turma', 'N/A'),
                'unidade': aluno.get('turma', {}).get('unidade', 'N/A')
            },
            'termos': {
                'matricula': {'disponivel': True, 'gerado': False},
                'imagem': {'disponivel': True, 'gerado': False},
                'regulamento': {'disponivel': True, 'gerado': False},
                'saude': {'disponivel': True, 'gerado': False},  # NOVO: termo de saúde sempre disponível
                'transporte': {
                    'disponivel': aluno.get('transporte') is not None,
                    'gerado': False,
                    'dados': aluno.get('transporte')
                },
                'terceiros': {
                    'disponivel': aluno.get('terceiros') and len(aluno.get('terceiros', [])) > 0,
                    'gerado': False,
                    'quantidade': len(aluno.get('terceiros', []))
                }
            },
            'resumo': {
                'total_disponiveis': termos_base + termos_opcionais,
                'termos_base': termos_base,
                'termos_opcionais': termos_opcionais
            }
        }
    
    def verificar_arquivos_termos(self):
        """Verifica se todos os arquivos de template dos termos existem"""
        import os
        from pathlib import Path
        
        templates_path = Path('templates') / 'componentes'
        termos_necessarios = [
            'termo_matricula.html',
            'autorizacao_imagem.html',
            'termo_transporte.html',
            'termo_terceiro.html',
            'regulamento.html',
            'termo_saude.html'  # NOVO: adicionado à lista
        ]
        
        resultado = {
            'existem': [],
            'faltam': []
        }
        
        for termo in termos_necessarios:
            arquivo = templates_path / termo
            if arquivo.exists():
                resultado['existem'].append(termo)
            else:
                resultado['faltam'].append(termo)
        
        return resultado