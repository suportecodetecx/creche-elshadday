from flask import Blueprint, send_file, jsonify, request, render_template, url_for
from services.termo_service import TermoService
from services.unidades_config import get_unidade_info
import os
import zipfile
from io import BytesIO
from datetime import datetime

termos_bp = Blueprint('termos', __name__)
termo_service = TermoService()

# ===== ROTA PARA A FICHA CADASTRAL =====
@termos_bp.route('/ficha/<num_inscricao>', methods=['GET'])
def gerar_ficha_cadastral(num_inscricao):
    """Gera a ficha cadastral do aluno em HTML para impressão"""
    try:
        # Buscar dados do aluno usando o serviço existente
        aluno = termo_service.buscar_aluno_por_inscricao(num_inscricao)
        
        if not aluno:
            return jsonify({'erro': 'Aluno não encontrado'}), 404
        
        # Processar as fotos para gerar URLs completas
        if aluno and 'arquivos' in aluno and aluno['arquivos']:
            for arquivo in aluno['arquivos']:
                if arquivo['campo'] == 'foto_aluno':
                    # Gerar URL completa da foto
                    arquivo['caminho_completo'] = url_for('static', 
                                                          filename='uploads/' + arquivo['caminho'], 
                                                          _external=True)
        
        # Buscar informações da unidade
        unidade_nome = aluno.get('turma', {}).get('unidade', 'CEIC El Shadday')
        unidade = get_unidade_info(unidade_nome)
        
        # Renderizar o template
        return render_template('ficha_cadastro.html',
                             aluno=aluno,
                             unidade=unidade,
                             data_hora=datetime.now().strftime('%d/%m/%Y %H:%M'))
        
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

# ===== TERMO DE MATRÍCULA (PDF) =====
@termos_bp.route('/api/termos/matricula/<num_inscricao>', methods=['GET'])
def gerar_termo_matricula(num_inscricao):
    """Gera e retorna o termo de matrícula em PDF"""
    try:
        pdf_path = termo_service.gerar_termo_matricula(num_inscricao)
        return send_file(pdf_path, as_attachment=True, download_name=f"termo_matricula_{num_inscricao}.pdf")
        
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

# ===== TERMO DE AUTORIZAÇÃO DE IMAGEM (PDF) =====
@termos_bp.route('/api/termos/imagem/<num_inscricao>', methods=['GET'])
def gerar_autorizacao_imagem(num_inscricao):
    """Gera autorização de uso de imagem"""
    try:
        pdf_path = termo_service.gerar_autorizacao_imagem(num_inscricao)
        return send_file(pdf_path, as_attachment=True, download_name=f"autorizacao_imagem_{num_inscricao}.pdf")
        
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

# ===== TERMO DE TRANSPORTE (PDF) =====
@termos_bp.route('/api/termos/transporte/<num_inscricao>', methods=['GET'])
def gerar_termo_transporte(num_inscricao):
    """Gera termo de transporte"""
    try:
        pdf_path = termo_service.gerar_termo_transporte(num_inscricao)
        return send_file(pdf_path, as_attachment=True, download_name=f"termo_transporte_{num_inscricao}.pdf")
        
    except Exception as e:
        return jsonify({'erro': str(e)}), 400 if 'não possui' in str(e) else 500

# ===== TERMO DE TERCEIROS (PDF) =====
@termos_bp.route('/api/termos/terceiro/<num_inscricao>', methods=['GET'])
def gerar_termo_terceiro(num_inscricao):
    """Gera termo de autorização para terceiros"""
    try:
        pdf_path = termo_service.gerar_termo_terceiro(num_inscricao)
        return send_file(pdf_path, as_attachment=True, download_name=f"termo_terceiro_{num_inscricao}.pdf")
        
    except Exception as e:
        return jsonify({'erro': str(e)}), 400 if 'não possui' in str(e) else 500

# ===== TERMO DE REGULAMENTO INTERNO (PDF) =====
@termos_bp.route('/api/termos/regulamento/<num_inscricao>', methods=['GET'])
def gerar_regulamento_interno(num_inscricao):
    """Gera termo de ciência do regulamento interno"""
    try:
        pdf_path = termo_service.gerar_regulamento_interno(num_inscricao)
        return send_file(pdf_path, as_attachment=True, download_name=f"regulamento_{num_inscricao}.pdf")
        
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

# ===== TERMO DE SAÚDE (PDF) =====
@termos_bp.route('/api/termos/saude/<num_inscricao>', methods=['GET'])
def gerar_termo_saude(num_inscricao):
    """Gera termo de saúde da criança"""
    try:
        pdf_path = termo_service.gerar_termo_saude(num_inscricao)
        return send_file(pdf_path, as_attachment=True, download_name=f"termo_saude_{num_inscricao}.pdf")
        
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

# ===== NOVAS ROTAS: VISUALIZAR TERMOS EM HTML (PARA IMPRESSÃO DIRETA) =====

@termos_bp.route('/visualizar/termo/saude/<num_inscricao>', methods=['GET'])
def visualizar_termo_saude(num_inscricao):
    """Exibe o termo de saúde em HTML para impressão direta"""
    try:
        # Buscar dados do aluno completo
        aluno = termo_service.get_aluno_completo(num_inscricao)
        
        if not aluno:
            return "Aluno não encontrado", 404
        
        # Buscar responsável principal
        resp_principal = None
        if aluno.get('responsaveis') and len(aluno.get('responsaveis', [])) > 0:
            resp_principal = next((r for r in aluno['responsaveis'] if r.get('tipo') == 'principal'), aluno['responsaveis'][0])
        
        # Buscar informações da unidade
        unidade_nome = aluno.get('turma', {}).get('unidade', 'CEIC El Shadday')
        unidade = get_unidade_info(unidade_nome)
        
        # Dados para o template
        dados = {
            'aluno': aluno,
            'responsavel': resp_principal,
            'unidade': unidade,
            'data_atual': datetime.now().strftime('%d/%m/%Y'),
            'numero_termo': f"SAUDE-{num_inscricao}"
        }
        
        # Renderiza o template HTML
        return render_template('componentes/termo_saude.html', **dados)
        
    except Exception as e:
        return str(e), 500

@termos_bp.route('/visualizar/termo/matricula/<num_inscricao>', methods=['GET'])
def visualizar_termo_matricula(num_inscricao):
    """Exibe o termo de matrícula em HTML para impressão direta"""
    try:
        aluno = termo_service.get_aluno_completo(num_inscricao)
        if not aluno:
            return "Aluno não encontrado", 404
        
        unidade_nome = aluno.get('turma', {}).get('unidade', 'CEIC El Shadday')
        unidade = get_unidade_info(unidade_nome)
        
        dados = {
            'aluno': aluno,
            'unidade': unidade,
            'data_atual': datetime.now().strftime('%d/%m/%Y'),
            'numero_termo': f"TERMO-{num_inscricao}"
        }
        
        return render_template('componentes/termo_matricula.html', **dados)
        
    except Exception as e:
        return str(e), 500

@termos_bp.route('/visualizar/termo/imagem/<num_inscricao>', methods=['GET'])
def visualizar_termo_imagem(num_inscricao):
    """Exibe a autorização de uso de imagem em HTML para impressão direta"""
    try:
        aluno = termo_service.get_aluno_completo(num_inscricao)
        if not aluno:
            return "Aluno não encontrado", 404
        
        # Buscar responsável principal
        resp_principal = None
        if aluno.get('responsaveis') and len(aluno.get('responsaveis', [])) > 0:
            resp_principal = next((r for r in aluno['responsaveis'] if r.get('tipo') == 'principal'), aluno['responsaveis'][0])
        
        unidade_nome = aluno.get('turma', {}).get('unidade', 'CEIC El Shadday')
        unidade = get_unidade_info(unidade_nome)
        
        dados = {
            'aluno': aluno,
            'responsavel': resp_principal,
            'unidade': unidade,
            'data_atual': datetime.now().strftime('%d/%m/%Y'),
            'numero_termo': f"AUT-{num_inscricao}"
        }
        
        return render_template('componentes/autorizacao_imagem.html', **dados)
        
    except Exception as e:
        return str(e), 500

@termos_bp.route('/visualizar/termo/regulamento/<num_inscricao>', methods=['GET'])
def visualizar_termo_regulamento(num_inscricao):
    """Exibe o regulamento interno em HTML para impressão direta"""
    try:
        aluno = termo_service.get_aluno_completo(num_inscricao)
        if not aluno:
            return "Aluno não encontrado", 404
        
        unidade_nome = aluno.get('turma', {}).get('unidade', 'CEIC El Shadday')
        unidade = get_unidade_info(unidade_nome)
        
        dados = {
            'aluno': aluno,
            'unidade': unidade,
            'data_atual': datetime.now().strftime('%d/%m/%Y'),
            'numero_termo': f"REG-{num_inscricao}"
        }
        
        return render_template('componentes/regulamento.html', **dados)
        
    except Exception as e:
        return str(e), 500

@termos_bp.route('/visualizar/termo/transporte/<num_inscricao>', methods=['GET'])
def visualizar_termo_transporte(num_inscricao):
    """Exibe o termo de transporte em HTML para impressão direta"""
    try:
        aluno = termo_service.get_aluno_completo(num_inscricao)
        if not aluno:
            return "Aluno não encontrado", 404
        
        if not aluno.get('transporte'):
            return "Aluno não possui transporte cadastrado", 400
        
        unidade_nome = aluno.get('turma', {}).get('unidade', 'CEIC El Shadday')
        unidade = get_unidade_info(unidade_nome)
        
        dados = {
            'aluno': aluno,
            'transporte': aluno['transporte'],
            'unidade': unidade,
            'data_atual': datetime.now().strftime('%d/%m/%Y'),
            'numero_termo': f"TRANS-{num_inscricao}"
        }
        
        return render_template('componentes/termo_transporte.html', **dados)
        
    except Exception as e:
        return str(e), 500

@termos_bp.route('/visualizar/termo/terceiro/<num_inscricao>', methods=['GET'])
def visualizar_termo_terceiro(num_inscricao):
    """Exibe o termo de terceiros em HTML para impressão direta"""
    try:
        aluno = termo_service.get_aluno_completo(num_inscricao)
        if not aluno:
            return "Aluno não encontrado", 404
        
        if not aluno.get('terceiros') or len(aluno.get('terceiros', [])) == 0:
            return "Aluno não possui terceiros cadastrados", 400
        
        unidade_nome = aluno.get('turma', {}).get('unidade', 'CEIC El Shadday')
        unidade = get_unidade_info(unidade_nome)
        
        dados = {
            'aluno': aluno,
            'unidade': unidade,
            'data_atual': datetime.now().strftime('%d/%m/%Y'),
            'numero_termo': f"TERC-{num_inscricao}"
        }
        
        return render_template('componentes/termo_terceiro.html', **dados)
        
    except Exception as e:
        return str(e), 500

# ===== TODOS OS TERMOS EM ZIP =====
@termos_bp.route('/api/termos/todos/<num_inscricao>', methods=['GET'])
def gerar_todos_termos(num_inscricao):
    """Gera todos os termos em um arquivo ZIP"""
    try:
        resultado = termo_service.gerar_todos_termos(num_inscricao)
        
        if not resultado['termos']:
            return jsonify({'erro': 'Nenhum termo foi gerado', 'detalhes': resultado['erros']}), 404
        
        # Cria um arquivo ZIP em memória
        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w') as zf:
            for termo in resultado['termos']:
                if 'arquivo' in termo and os.path.exists(termo['arquivo']):
                    zf.write(termo['arquivo'], arcname=os.path.basename(termo['arquivo']))
        
        memory_file.seek(0)
        
        return send_file(
            memory_file,
            download_name=f"termos_completos_{num_inscricao}.zip",
            as_attachment=True
        )
        
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

# ===== INFORMAÇÕES SOBRE TERMOS =====
@termos_bp.route('/api/termos/info/<num_inscricao>', methods=['GET'])
def info_termos(num_inscricao):
    """Retorna informações sobre os termos disponíveis"""
    try:
        info = termo_service.get_info_termos(num_inscricao)
        return jsonify({'sucesso': True, 'dados': info})
        
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

# ===== VERIFICAR ARQUIVOS DE TEMPLATE =====
@termos_bp.route('/api/termos/verificar', methods=['GET'])
def verificar_termos():
    """Endpoint para verificar se os arquivos de template existem"""
    try:
        resultado = termo_service.verificar_arquivos_termos()
        return jsonify({
            'sucesso': True,
            'templates': resultado
        })
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

# ===== GERAR TERMO ESPECÍFICO =====
@termos_bp.route('/api/termos/especifico', methods=['POST'])
def gerar_termo_especifico():
    """Gera um termo específico baseado nos parâmetros"""
    try:
        dados = request.get_json()
        num_inscricao = dados.get('num_inscricao')
        tipo_termo = dados.get('tipo_termo')
        
        if not num_inscricao or not tipo_termo:
            return jsonify({'erro': 'Número de inscrição e tipo do termo são obrigatórios'}), 400
        
        pdf_path = termo_service.gerar_termo_especifico(num_inscricao, tipo_termo)
        
        return send_file(
            pdf_path, 
            as_attachment=True, 
            download_name=f"{tipo_termo}_{num_inscricao}.pdf"
        )
        
    except Exception as e:
        return jsonify({'erro': str(e)}), 500