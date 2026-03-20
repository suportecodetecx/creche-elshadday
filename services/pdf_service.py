# services/pdf_service.py
from weasyprint import HTML
from jinja2 import Environment, FileSystemLoader
import os
from datetime import datetime
from services.unidades_config import get_unidade_info

class PDFService:
    def __init__(self):
        # CORRIGIDO: apontando para templates/componentes
        self.template_dir = os.path.join('templates', 'componentes')
        self.env = Environment(loader=FileSystemLoader(self.template_dir))
        self.output_dir = 'generated_terms'
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Configurar filtros personalizados para o Jinja2
        self._configurar_filtros()
    
    def _configurar_filtros(self):
        """Configura filtros personalizados para o Jinja2"""
        
        # Filtro para formatar CPF
        def format_cpf(cpf):
            if not cpf:
                return ''
            cpf = ''.join(filter(str.isdigit, str(cpf)))
            if len(cpf) == 11:
                return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
            return cpf
        
        # Filtro para formatar RG (VERSÃO SIMPLIFICADA)
        def format_rg(rg):
            if not rg:
                return '____________________'
            return str(rg)
        
        # Filtro para formatar CEP
        def format_cep(cep):
            if not cep:
                return ''
            cep = ''.join(filter(str.isdigit, str(cep)))
            if len(cep) == 8:
                return f"{cep[:5]}-{cep[5:]}"
            return cep
        
        # Filtro para formatar telefone
        def format_telefone(telefone):
            if not telefone:
                return ''
            telefone = ''.join(filter(str.isdigit, str(telefone)))
            if len(telefone) == 11:
                return f"({telefone[:2]}) {telefone[2:7]}-{telefone[7:]}"
            elif len(telefone) == 10:
                return f"({telefone[:2]}) {telefone[2:6]}-{telefone[6:]}"
            return telefone
        
        # Registrar filtros - VERIFICAÇÃO EXPLÍCITA
        try:
            self.env.filters['format_cpf'] = format_cpf
            print("✅ Filtro format_cpf registrado")
        except Exception as e:
            print(f"❌ Erro ao registrar format_cpf: {e}")
        
        try:
            self.env.filters['format_rg'] = format_rg
            print("✅ Filtro format_rg registrado")
        except Exception as e:
            print(f"❌ Erro ao registrar format_rg: {e}")
        
        try:
            self.env.filters['format_cep'] = format_cep
            print("✅ Filtro format_cep registrado")
        except Exception as e:
            print(f"❌ Erro ao registrar format_cep: {e}")
        
        try:
            self.env.filters['format_telefone'] = format_telefone
            print("✅ Filtro format_telefone registrado")
        except Exception as e:
            print(f"❌ Erro ao registrar format_telefone: {e}")
    
    def _get_unidade_dados(self, aluno):
        """Busca dados da unidade baseado na turma do aluno"""
        nome_unidade = aluno.get('turma', {}).get('unidade', 'CEIC El Shadday')
        unidade = get_unidade_info(nome_unidade)
        
        # Adicionar email se não existir (para compatibilidade)
        if 'email' not in unidade:
            if nome_unidade == 'CEIC El Shadday':
                unidade['email'] = 'ceic.elshadday@se-pmmc.com.br'
            elif nome_unidade == 'CEIM Prof. Egberto Malta Moreira':
                unidade['email'] = 'ceim.egberto@se-pmmc.com.br'
            else:
                unidade['email'] = 'contato@crecheelshadday.com.br'
        
        # Adicionar tipo de unidade
        if 'tipo' not in unidade:
            if 'CEIC' in nome_unidade:
                unidade['tipo'] = 'Centro de Educação Infantil Comunitário'
            elif 'CEIM' in nome_unidade:
                unidade['tipo'] = 'Centro de Educação Infantil Municipal'
            else:
                unidade['tipo'] = 'Centro de Educação Infantil'
        
        return unidade
    
    def _get_responsavel_principal(self, aluno_data):
        """Retorna o responsável principal do aluno"""
        responsaveis = aluno_data.get('responsaveis', [])
        
        # Primeiro tenta encontrar o responsável principal
        for resp in responsaveis:
            if resp.get('tipo') == 'principal' or resp.get('principal'):
                return resp
        
        # Se não encontrar, retorna o primeiro ou um dicionário vazio
        return responsaveis[0] if responsaveis else {}
    
    def gerar_autorizacao_imagem(self, aluno_data):
        """Gera autorização de uso de imagem"""
        try:
            print("🔍 Iniciando geração de autorização de imagem...")
            print(f"📂 Diretório de templates: {self.template_dir}")
            
            # Verificar se o template existe
            template_path = os.path.join(self.template_dir, 'autorizacao_imagem.html')
            if not os.path.exists(template_path):
                raise Exception(f"Template não encontrado: {template_path}")
            print(f"✅ Template encontrado: {template_path}")
            
            template = self.env.get_template('autorizacao_imagem.html')
            unidade = self._get_unidade_dados(aluno_data)
            responsavel = self._get_responsavel_principal(aluno_data)
            
            # Preparar dados sem usar filtros (já formatados)
            cpf_formatado = self._format_cpf_direct(responsavel.get('cpf', ''))
            rg_formatado = self._format_rg_direct(responsavel.get('rg', ''))
            
            dados = {
                'aluno': aluno_data,
                'responsavel': responsavel,
                'unidade': unidade,
                'data_atual': datetime.now().strftime('%d/%m/%Y'),
                'numero_termo': f"AUT-{aluno_data.get('num_inscricao', '0000')}-{datetime.now().strftime('%Y%m')}",
                'cpf_formatado': cpf_formatado,
                'rg_formatado': rg_formatado
            }
            
            print("✅ Dados preparados")
            html_content = template.render(dados)
            
            filename = f"autorizacao_imagem_{aluno_data.get('num_inscricao', '0000')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            filepath = os.path.join(self.output_dir, filename)
            
            HTML(string=html_content, base_url=os.path.dirname(os.path.abspath(__file__))).write_pdf(filepath)
            print(f"✅ PDF gerado: {filepath}")
            
            return filepath
            
        except Exception as e:
            print(f"❌ Erro ao gerar autorização de imagem: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _format_cpf_direct(self, cpf):
        """Formata CPF diretamente sem usar filtro"""
        if not cpf:
            return '____________________'
        cpf = ''.join(filter(str.isdigit, str(cpf)))
        if len(cpf) == 11:
            return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
        return str(cpf)
    
    def _format_rg_direct(self, rg):
        """Formata RG diretamente sem usar filtro"""
        if not rg:
            return '____________________'
        return str(rg)
    
    # ... (resto dos métodos mantidos iguais, mas com as mesmas melhorias)