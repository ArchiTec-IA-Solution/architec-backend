

from flask import Flask, request, jsonify, send_file, render_template, send_from_directory

import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black, white, Color
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io
import os
import json
import re
from datetime import datetime
import uuid

from pdfs.pdf_generator import PDFGenerator
from pdfs.tables.table_service import TableService

class PDFGeneratorService:
    """Centraliza a lógica de criação e formatação do PDF."""
    
    def build_final_footer(self, valor_total_geral):
        """Cria os Flowables (elementos de conteúdo) para o rodapé final - Aparece APENAS na última página."""
        story = []
        
        story.append(Spacer(1, 0.5 * inch))
        
        total_data = [
            [
                Paragraph("Total final:", self.styles['Normal']), 
                Paragraph(f"R$ {valor_total_geral:.2f}", self.styles['Bold']) 
            ]
        ]
        
        total_table_style = TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'RIGHT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LINEBELOW', (0, 0), (-1, 0), 1, black),
        ])
        
        total_table = Table(total_data, colWidths=[5.5 * inch, 1.5 * inch])
        total_table.setStyle(total_table_style)
        story.append(total_table)
        
        story.append(Spacer(1, 0.2 * inch))

        rodape_promob = [
            [
                Paragraph(f"TABELA DE PREÇOS: BOA VISTA - TABELA LOJAS OFICIAL {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", self.styles['Small']), 
            ],
            [
                Paragraph("Razão social: Boa Vista | Endereço: | Telefone: (85) 9-9615-0458", self.styles['Normal']),
            ],
            [
                Paragraph("©Boa Vista. Todos os direitos reservados.", self.styles['Small']),
            ]
        ]
        
        rodape_table_style = TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ])
        
        rodape_table = Table(rodape_promob, colWidths=[7 * inch])
        rodape_table.setStyle(rodape_table_style)
        story.append(rodape_table)
        
        return story

    def build_story(self, produtos_info):
        """Cria o conteúdo (Story) do PDF que flui pelas páginas."""
        story = []
        
        story.append(Spacer(1, 1.2 * inch)) 
        
        story.append(Paragraph("PROJETO - COZINHA - COZINHA - ACESSÓRIOS", self.styles['Bold']))
        story.append(Spacer(1, 0.1 * inch))

        data = [
            [
                Paragraph("Qtd", self.styles['TabelaHeader']),
                Paragraph("Produto", self.styles['TabelaHeader']),
                Paragraph("Dimensões", self.styles['TabelaHeader']),
                Paragraph("Vl. Unit.", self.styles['TabelaHeader']),
                Paragraph("Vl. Total", self.styles['TabelaHeader'])
            ]
        ]
        
        valor_total_geral = 0
        
        for produto, quantidade in produtos_info:
            try:
                valor_unitario = float(produto.valor) if produto.valor else 0
            except ValueError:
                valor_unitario = 0
            
            valor_total = valor_unitario * int(quantidade)
            valor_total_geral += valor_total
            
            descricao = str(produto.descricao)
            if len(descricao) > 40:
                descricao = descricao[:37] + "..."
                
            data.append([
                Paragraph(str(quantidade), self.styles['TabelaContent']),
                Paragraph(descricao, self.styles['TabelaContent']),
                Paragraph(produto.dimensao if produto.dimensao else "N/A", self.styles['TabelaContent']),
                Paragraph(f"R$ {valor_unitario:.2f}", self.styles['TabelaContent']),
                Paragraph(f"R$ {valor_total:.2f}", self.styles['TabelaContent'])
            ])

        col_widths = [0.5 * inch, 2.5 * inch, 1.5 * inch, 1 * inch, 1 * inch]
        
        t = Table(data, colWidths=col_widths)
        t.setStyle(self.get_table_style(len(data) - 1))
        story.append(t)
        
        final_footer = self.build_final_footer(valor_total_geral)
        story.extend(final_footer)
        
        return story

    def on_each_page(self, canvas, doc):
        TableService.draw_page_elements(canvas, doc, self.nome_cliente) 

    def generate(self, produtos_info):
        """Gera o buffer do PDF."""
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=letter,
            topMargin=inch * 1.5,
            bottomMargin=inch * 1.5,
        )
        
        story = self.build_story(produtos_info)
        
            
        doc.build(story, onFirstPage=PDFGeneratorService.on_each_page, onLaterPages=PDFGeneratorService.on_each_page)
        
        buffer.seek(0)
        return buffer
    
    def gerar_pdf(produtos, nome_cliente="Orçamento", quantidade=1):
        """Gera um PDF profissional para um único produto (Wrapper)"""
        try:
            produtos_info = [(produtos[0], quantidade)] if produtos else []
            pdf_generator = PDFGenerator(nome_cliente=nome_cliente)
            return pdf_generator.generate(produtos_info)
        except Exception as e:
            print(f" Erro ao gerar PDF (single): {e}") 
            return None


    def gerar_pdf_multiplos(produtos_quantidades, nome_cliente="Orçamento"):
        """Gera PDF para múltiplos produtos (Wrapper)"""
        try:
            pdf_generator = PDFGenerator(nome_cliente=nome_cliente)
            return pdf_generator.generate(produtos_quantidades)
        except Exception as e:
            print(f" Erro ao gerar PDF (múltiplo): {e}")
            return None