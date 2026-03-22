# routes/justificativa_routes.py
from flask import Blueprint, request, jsonify, send_file
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
import io
from datetime import datetime

justificativa_bp = Blueprint('justificativa', __name__)

@justificativa_bp.route('/api/gerar-pdf-justificativa', methods=['POST'])
def gerar_pdf_justificativa():
    """Gera PDF da justificativa de saída"""
    try:
        dados = request.get_json()
        
        # Extrair dados do JSON
        data = dados.get('data', '___/___/_____')
        colaborador = dados.get('colaborador', '_________________________')
        rgm = dados.get('rgm', '___________')
        cargo = dados.get('cargo', '___________')
        unidade = dados.get('unidade', '___________')
        apontamento = dados.get('apontamento', '___:___ às ___:___')
        motivo = dados.get('motivo', '_________________________')
        observacoes = dados.get('observacoes', '_________________________')
        unidade_nome = dados.get('unidade_nome', 'CEIC El Shadday')
        unidade_cnpj = dados.get('unidade_cnpj', '03.067.526/0001-87')
        unidade_endereco = dados.get('unidade_endereco', 'Rua Francisco Vilani Bicudo, 470 - Vila Nova Aparecida')
        unidade_telefone = dados.get('unidade_telefone', '(11) 4739-3549')
        numero_justificativa = dados.get('numero_justificativa', '001/2026')
        data_emissao = dados.get('data_emissao', datetime.now().strftime('%d/%m/%Y %H:%M'))
        
        # Criar buffer para PDF
        buffer = io.BytesIO()
        
        # Criar documento PDF
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                rightMargin=15*mm, leftMargin=15*mm,
                                topMargin=20*mm, bottomMargin=15*mm)
        
        # Estilos
        styles = getSampleStyleSheet()
        style_normal = styles['Normal']
        style_center = ParagraphStyle(
            'Center',
            parent=styles['Normal'],
            alignment=1,
            fontSize=10
        )
        style_title = ParagraphStyle(
            'Title',
            parent=styles['Normal'],
            fontSize=14,
            alignment=1,
            spaceAfter=10,
            fontName='Helvetica-Bold'
        )
        style_header = ParagraphStyle(
            'Header',
            parent=styles['Normal'],
            fontSize=12,
            alignment=1,
            fontName='Helvetica-Bold'
        )
        style_right = ParagraphStyle(
            'Right',
            parent=styles['Normal'],
            alignment=2,
            fontSize=10
        )
        
        # Lista de elementos
        elements = []
        
        # CABEÇALHO
        elements.append(Paragraph("CRECHE EL SHADDAY", style_header))
        elements.append(Paragraph(unidade_nome, style_center))
        elements.append(Paragraph(f"CNPJ: {unidade_cnpj} - Mogi das Cruzes/SP", style_center))
        elements.append(Spacer(1, 5*mm))
        
        # Linha
        elements.append(Paragraph("_" * 80, style_normal))
        elements.append(Spacer(1, 3*mm))
        
        # Número da justificativa
        elements.append(Paragraph(f"JUSTIFICATIVA Nº {numero_justificativa} - {data_emissao.split(' ')[0]}", style_right))
        elements.append(Spacer(1, 5*mm))
        
        # Título
        elements.append(Paragraph("JUSTIFICATIVA DE SAÍDA - VIA EMPRESA", style_title))
        elements.append(Spacer(1, 5*mm))
        
        # DADOS
        dados_linhas = [
            ("Data:", data),
            ("Colaborador:", colaborador),
            ("RGM:", rgm),
            ("Cargo:", cargo),
            ("Unidade:", unidade),
            ("Apontamento:", apontamento),
        ]
        
        for label, valor in dados_linhas:
            elements.append(Paragraph(f"<b>{label}</b> {valor}", style_normal))
            elements.append(Spacer(1, 3*mm))
        
        # MOTIVO
        elements.append(Spacer(1, 5*mm))
        elements.append(Paragraph("<b>MOTIVO DA SAÍDA</b>", style_normal))
        elements.append(Paragraph(f"Motivo: {motivo}", style_normal))
        if observacoes and observacoes != '_________________________':
            elements.append(Paragraph(f"Observações: {observacoes}", style_normal))
        
        elements.append(Spacer(1, 15*mm))
        
        # ASSINATURAS
        elements.append(Paragraph("_" * 40, style_center))
        elements.append(Paragraph("Assinatura do Colaborador", style_center))
        elements.append(Spacer(1, 5*mm))
        elements.append(Paragraph("_" * 40, style_center))
        elements.append(Paragraph("Assinatura do Responsável", style_center))
        
        elements.append(Spacer(1, 10*mm))
        
        # RODAPÉ
        elements.append(Paragraph("_" * 80, style_normal))
        elements.append(Paragraph(unidade_nome, style_center))
        elements.append(Paragraph(unidade_endereco, style_center))
        elements.append(Paragraph(f"📞 {unidade_telefone}", style_center))
        
        elements.append(Spacer(1, 10*mm))
        
        # LINHA DE CORTE
        elements.append(Paragraph("-" * 60, style_center))
        elements.append(Paragraph("✂️ RECORTE AQUI ✂️", style_center))
        elements.append(Paragraph("-" * 60, style_center))
        elements.append(Spacer(1, 10*mm))
        
        # VIA COLABORADOR
        elements.append(Paragraph("JUSTIFICATIVA DE SAÍDA - VIA COLABORADOR", style_title))
        elements.append(Spacer(1, 5*mm))
        
        # DADOS VIA COLABORADOR
        for label, valor in dados_linhas:
            elements.append(Paragraph(f"<b>{label}</b> {valor}", style_normal))
            elements.append(Spacer(1, 3*mm))
        
        # MOTIVO VIA COLABORADOR
        elements.append(Spacer(1, 5*mm))
        elements.append(Paragraph("<b>MOTIVO DA SAÍDA</b>", style_normal))
        elements.append(Paragraph(f"Motivo: {motivo}", style_normal))
        if observacoes and observacoes != '_________________________':
            elements.append(Paragraph(f"Observações: {observacoes}", style_normal))
        
        elements.append(Spacer(1, 15*mm))
        
        # ASSINATURAS VIA COLABORADOR
        elements.append(Paragraph("_" * 40, style_center))
        elements.append(Paragraph("Assinatura do Colaborador", style_center))
        elements.append(Spacer(1, 5*mm))
        elements.append(Paragraph("_" * 40, style_center))
        elements.append(Paragraph("Assinatura do Responsável", style_center))
        
        elements.append(Spacer(1, 10*mm))
        
        # RODAPÉ VIA COLABORADOR
        elements.append(Paragraph("_" * 80, style_normal))
        elements.append(Paragraph(unidade_nome, style_center))
        elements.append(Paragraph(unidade_endereco, style_center))
        elements.append(Paragraph(f"📞 {unidade_telefone}", style_center))
        
        elements.append(Spacer(1, 5*mm))
        elements.append(Paragraph(f"Emitido em: {data_emissao}", style_center))
        
        # Gerar PDF
        doc.build(elements)
        
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"justificativa_{colaborador.replace(' ', '_')}_{numero_justificativa}.pdf",
            mimetype='application/pdf'
        )
        
    except Exception as e:
        print(f"Erro ao gerar PDF: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'erro': str(e)}), 500