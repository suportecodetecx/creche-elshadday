# services/pdf_service.py
import sys
import os
from datetime import datetime
from services.unidades_config import get_unidade_info

# Verifica se está no Vercel ou ambiente serverless
IS_VERCEL = os.environ.get('VERCEL') == '1' or os.environ.get('NOW') is not None

# Tenta importar WeasyPrint apenas se não for Vercel
if not IS_VERCEL:
    try:
        from weasyprint import HTML
        from jinja2 import Environment, FileSystemLoader
        WEASYPRINT_AVAILABLE = True
        print("✅ WeasyPrint carregado com sucesso")
    except ImportError:
        WEASYPRINT_AVAILABLE = False
        print("⚠️ WeasyPrint não disponível (modo limitado)")
else:
    WEASYPRINT_AVAILABLE = False
    print("⚠️ Modo Vercel - WeasyPrint desabilitado")

class PDFService:
    def __init__(self):
        self.template_dir = os.path.join('templates', 'componentes')
        self.output_dir = 'generated_terms'
        
        # Tenta criar a pasta de saída (ignora erro no Vercel)
        try:
            os.makedirs(self.output_dir, exist_ok=True)
        except Exception:
            pass
        
        # Configurar Jinja2 apenas se disponível
        if WEASYPRINT_AVAILABLE:
            self.env = Environment(loader=FileSystemLoader(self.template_dir))
            self._configurar_filtros()
        else:
            self.env = None
    
    def _configurar_filtros(self):
        """Configura filtros personalizados para o Jinja2"""
        if not WEASYPRINT_AVAILABLE:
            return
            
        # Filtro para formatar CPF
        def format_cpf(cpf):
            if not cpf:
                return ''
            cpf = ''.join(filter(str.isdigit, str(cpf)))
            if len(cpf) == 11:
                return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
            return cpf
        
        # Filtro para formatar RG
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
        
        # Registrar filtros
        try:
            self.env.filters['format_cpf'] = format_cpf
            self.env.filters['format_rg'] = format_rg
            self.env.filters['format_cep'] = format_cep
            self.env.filters['format_telefone'] = format_telefone
        except Exception as e:
            print(f"Erro ao registrar filtros: {e}")
    
    def _get_unidade_dados(self, aluno):
        """Busca dados da unidade baseado na turma do aluno"""
        nome_unidade = aluno.get('turma', {}).get('unidade', 'CEIC El Shadday')
        unidade = get_unidade_info(nome_unidade)
        
        if 'email' not in unidade:
            if nome_unidade == 'CEIC El Shadday':
                unidade['email'] = 'ceic.elshadday@se-pmmc.com.br'
            elif nome_unidade == 'CEIM Prof. Egberto Malta Moreira':
                unidade['email'] = 'ceim.egberto@se-pmmc.com.br'
            else:
                unidade['email'] = 'contato@crecheelshadday.com.br'
        
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
        for resp in responsaveis:
            if resp.get('tipo') == 'principal' or resp.get('principal'):
                return resp
        return responsaveis[0] if responsaveis else {}
    
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
    
    def _render_html(self, template_name, dados):
        """Renderiza HTML a partir do template"""
        if not WEASYPRINT_AVAILABLE:
            raise Exception("Geração de PDF não disponível neste ambiente (Vercel)")
        
        template = self.env.get_template(template_name)
        return template.render(dados)
    
    def _generate_pdf(self, html_content, filename_prefix, num_inscricao):
        """Gera PDF a partir do HTML"""
        if not WEASYPRINT_AVAILABLE:
            raise Exception("Geração de PDF não disponível neste ambiente (Vercel)")
        
        filename = f"{filename_prefix}_{num_inscricao}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        
        HTML(string=html_content, base_url=os.path.dirname(os.path.abspath(__file__))).write_pdf(filepath)
        return filepath
    
    def gerar_autorizacao_imagem(self, aluno_data):
        """Gera autorização de uso de imagem"""
        try:
            if not WEASYPRINT_AVAILABLE:
                raise Exception("Geração de PDF não disponível no ambiente Vercel")
            
            unidade = self._get_unidade_dados(aluno_data)
            responsavel = self._get_responsavel_principal(aluno_data)
            
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
            
            html_content = self._render_html('autorizacao_imagem.html', dados)
            return self._generate_pdf(html_content, 'autorizacao_imagem', aluno_data.get('num_inscricao', '0000'))
            
        except Exception as e:
            print(f"❌ Erro ao gerar autorização de imagem: {e}")
            raise
    
    def gerar_termo_matricula(self, aluno_data):
        """Gera termo de matrícula"""
        try:
            if not WEASYPRINT_AVAILABLE:
                raise Exception("Geração de PDF não disponível no ambiente Vercel")
            
            unidade = self._get_unidade_dados(aluno_data)
            responsavel = self._get_responsavel_principal(aluno_data)
            
            dados = {
                'aluno': aluno_data,
                'responsavel': responsavel,
                'unidade': unidade,
                'data_atual': datetime.now().strftime('%d/%m/%Y'),
                'numero_termo': f"MAT-{aluno_data.get('num_inscricao', '0000')}-{datetime.now().strftime('%Y%m')}"
            }
            
            html_content = self._render_html('termo_matricula.html', dados)
            return self._generate_pdf(html_content, 'termo_matricula', aluno_data.get('num_inscricao', '0000'))
            
        except Exception as e:
            print(f"❌ Erro ao gerar termo de matrícula: {e}")
            raise
    
    def gerar_regulamento_interno(self, aluno_data):
        """Gera termo de ciência do regulamento interno"""
        try:
            if not WEASYPRINT_AVAILABLE:
                raise Exception("Geração de PDF não disponível no ambiente Vercel")
            
            unidade = self._get_unidade_dados(aluno_data)
            responsavel = self._get_responsavel_principal(aluno_data)
            
            dados = {
                'aluno': aluno_data,
                'responsavel': responsavel,
                'unidade': unidade,
                'data_atual': datetime.now().strftime('%d/%m/%Y'),
                'numero_termo': f"REG-{aluno_data.get('num_inscricao', '0000')}-{datetime.now().strftime('%Y%m')}"
            }
            
            html_content = self._render_html('regulamento.html', dados)
            return self._generate_pdf(html_content, 'regulamento', aluno_data.get('num_inscricao', '0000'))
            
        except Exception as e:
            print(f"❌ Erro ao gerar regulamento interno: {e}")
            raise
    
    def gerar_termo_saude(self, aluno_data):
        """Gera termo de saúde da criança"""
        try:
            if not WEASYPRINT_AVAILABLE:
                raise Exception("Geração de PDF não disponível no ambiente Vercel")
            
            unidade = self._get_unidade_dados(aluno_data)
            responsavel = self._get_responsavel_principal(aluno_data)
            
            dados = {
                'aluno': aluno_data,
                'responsavel': responsavel,
                'unidade': unidade,
                'data_atual': datetime.now().strftime('%d/%m/%Y'),
                'numero_termo': f"SAUDE-{aluno_data.get('num_inscricao', '0000')}-{datetime.now().strftime('%Y%m')}"
            }
            
            html_content = self._render_html('termo_saude.html', dados)
            return self._generate_pdf(html_content, 'termo_saude', aluno_data.get('num_inscricao', '0000'))
            
        except Exception as e:
            print(f"❌ Erro ao gerar termo de saúde: {e}")
            raise
    
    def gerar_termo_transporte(self, aluno_data):
        """Gera termo de transporte"""
        try:
            if not WEASYPRINT_AVAILABLE:
                raise Exception("Geração de PDF não disponível no ambiente Vercel")
            
            if not aluno_data.get('transporte'):
                raise Exception("Aluno não possui transporte cadastrado")
            
            unidade = self._get_unidade_dados(aluno_data)
            responsavel = self._get_responsavel_principal(aluno_data)
            
            dados = {
                'aluno': aluno_data,
                'transporte': aluno_data['transporte'],
                'responsavel': responsavel,
                'unidade': unidade,
                'data_atual': datetime.now().strftime('%d/%m/%Y'),
                'numero_termo': f"TRANS-{aluno_data.get('num_inscricao', '0000')}-{datetime.now().strftime('%Y%m')}"
            }
            
            html_content = self._render_html('termo_transporte.html', dados)
            return self._generate_pdf(html_content, 'termo_transporte', aluno_data.get('num_inscricao', '0000'))
            
        except Exception as e:
            print(f"❌ Erro ao gerar termo de transporte: {e}")
            raise
    
    def gerar_termo_terceiro(self, aluno_data):
        """Gera termo de autorização para terceiros"""
        try:
            if not WEASYPRINT_AVAILABLE:
                raise Exception("Geração de PDF não disponível no ambiente Vercel")
            
            if not aluno_data.get('terceiros') or len(aluno_data.get('terceiros', [])) == 0:
                raise Exception("Aluno não possui terceiros cadastrados")
            
            unidade = self._get_unidade_dados(aluno_data)
            responsavel = self._get_responsavel_principal(aluno_data)
            
            dados = {
                'aluno': aluno_data,
                'terceiros': aluno_data['terceiros'],
                'responsavel': responsavel,
                'unidade': unidade,
                'data_atual': datetime.now().strftime('%d/%m/%Y'),
                'numero_termo': f"TERC-{aluno_data.get('num_inscricao', '0000')}-{datetime.now().strftime('%Y%m')}"
            }
            
            html_content = self._render_html('termo_terceiro.html', dados)
            return self._generate_pdf(html_content, 'termo_terceiro', aluno_data.get('num_inscricao', '0000'))
            
        except Exception as e:
            print(f"❌ Erro ao gerar termo de terceiros: {e}")
            raise