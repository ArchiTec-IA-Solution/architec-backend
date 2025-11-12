
from datetime import datetime
import os
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.colors import HexColor, black, white, Color
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch

from pdfs.tables.cores import COR_CINZA_CLARO, COR_SEGUNDARIA, COR_TEXTO
from config import EXCEL_FILE, LOGO_PATH

# --- CONSTANTES --
COLUNAS_ESPERADAS = {
    'descricao': ['descrição', 'descricao', 'produto', 'item', 'nome', 'description', 'product'],
    'dimensao': ['dimensão', 'dimensao', 'tamanho', 'medida', 'size', 'dimension'],
    'valor': ['valor final', 'valor', 'preço', 'preco', 'custo', 'price', 'cost']
}

# Estados da conversa
ESTADOS = {
    'INICIO': 'INICIO',
    'MULTIPLAS_OPCOES': 'MULTIPLAS_OPCOES',
    'PRODUTO_SELECIONADO': 'PRODUTO_SELECIONADO',
    'DIMENSAO_SOLICITADA': 'DIMENSAO_SOLICITADA',
    'ORCAMENTO_FINALIZADO': 'ORCAMENTO_FINALIZADO'
}

class  TableService:
    
    def gerar_tabela_resumo(conversa):
        """Gera uma tabela formatada com o resumo do orçamento"""
        if not conversa.produto_selecionado:
            return ""
        
        produto = conversa.produto_selecionado
        quantidade = conversa.quantidade
        
        # Debug forçado
        print(f" DEBUG - gerar_tabela_resumo:")
        print(f"   Produto: {produto.descricao}")
        print(f"   Quantidade (conversa): {quantidade} (tipo: {type(quantidade)})")
        print(f"   Valor (produto): {produto.valor} (tipo: {type(produto.valor)})")
        
        # Garante que quantidade seja inteiro
        try:
            quantidade = int(quantidade)
        except (ValueError, TypeError):
            quantidade = 1
            print(f" Quantidade inválida, usando 1")
        
        # Garante que valor seja float
        try:
            valor_unitario = float(produto.valor) if produto.valor else 0
        except (ValueError, TypeError):
            valor_unitario = 0
            print(f" Valor inválido, usando 0")
        
        # Cálculo do valor total
        valor_total = valor_unitario * quantidade
        
        print(f"   Valor unitário (convertido): {valor_unitario}")
        print(f"   Quantidade (convertida): {quantidade}")
        print(f"   Valor total calculado: {valor_total}")
        
        # Formatação
        valor_unitario_str = f"R$ {valor_unitario:.2f}"
        valor_total_str = f"R$ {valor_total:.2f}"
        
        # Tabela detalhada
        tabela = f""" *Resumo do Orçamento:*

    | Qtd | Produto | Vl. Unitário | Vl. Total |
    |-----|---------|--------------|-----------|
    | {quantidade} | {produto.descricao[:40] + '...' if len(produto.descricao) > 40 else produto.descricao} | {valor_unitario_str} | {valor_total_str} |

    💰 *Valor Total: {valor_total_str}*
    🧮 *Cálculo: {quantidade} × {valor_unitario_str} = {valor_total_str}*

    📄 PDF disponível para download abaixo"""
        
        return tabela


    def gerar_tabela_multiplos_produtos(produtos_quantidades):
        """Gera tabela formatada para múltiplos produtos"""
        tabela = " *Resumo do Orçamento:*\n\n"
        tabela += "| Qtd | Produto | Dimensões | Vl. Unitário | Vl. Total |\n"
        tabela += "|-----|---------|-----------|--------------|-----------|\n"
        
        valor_total_geral = 0
        
        for produto, quantidade in produtos_quantidades:
            valor_unitario = float(produto.valor) if produto.valor else 0
            valor_total = valor_unitario * quantidade
            valor_total_geral += valor_total
            
            nome = produto.descricao[:30] + "..." if len(produto.descricao) > 30 else produto.descricao
            dimensoes = produto.dimensao if produto.dimensao else "N/A"
            
            tabela += f"| {quantidade} | {nome} | {dimensoes} | R$ {valor_unitario:.2f} | R$ {valor_total:.2f} |\n"
        
        tabela += f"\n💰 *Valor Total do Orçamento: R$ {valor_total_geral:.2f}*\n\n"
        tabela += "📄 PDF disponível para download abaixo"
        
        return tabela



    def draw_page_elements(canvas, doc, nome_cliente):
        """Desenha elementos fixos (cabeçalho e número da página) em cada página."""
        canvas.saveState()
        width, height = letter
        
        global COR_CINZA_CLARO, COR_TEXTO, LOGO_PATH
        
        canvas.setFillColor(COR_CINZA_CLARO)
        canvas.rect(0, height - 60, width, 60, fill=True, stroke=False)
        
        try:
            canvas.drawImage(LOGO_PATH, inch, height - 50, width=1.5 * inch, height=0.5 * inch, mask='auto')
        except Exception as e:
            canvas.setFillColor(black)
            canvas.setFont("Helvetica-Bold", 16)
            canvas.drawString(inch, height - 35, "BOA VISTA")

        canvas.setFillColor(black)
        canvas.setFont("Helvetica", 10)
        canvas.drawString(width - inch - 150, height - 35, "Orçamento") 
        canvas.drawString(width - inch - 150, height - 50, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}") 

        canvas.setStrokeColor(black)
        canvas.setLineWidth(0.5)
        canvas.line(inch, height - 70, width - inch, height - 70) 

        canvas.setFillColor(COR_TEXTO)
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(inch, height - 85, "Dados do cliente:")
        canvas.setFont("Helvetica", 10)
        canvas.drawString(inch, height - 100, f"Nome: {nome_cliente}")
        canvas.drawString(inch, height - 115, "E-mail: boavista@gmail.com (Exemplo)") 

        canvas.setFillColor(black)
        canvas.setFont("Helvetica", 9)
        page_number_text = f"Página {canvas.getPageNumber()}"
        canvas.drawString(width - inch - canvas.stringWidth(page_number_text, "Helvetica", 9), 30, page_number_text) 

        canvas.restoreState()


            
    def get_table_style(self, total_rows):
            """Define o estilo da tabela principal."""
            return TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), COR_SEGUNDARIA),
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 1), (-1, total_rows), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, total_rows), 9),
                ('GRID', (0, 0), (-1, -1), 0.25, black),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
            ])

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
    
    def carregar_excel():
        """Carrega os dados do arquivo Excel"""
        try:
            if not os.path.exists(EXCEL_FILE):
                print(f" Arquivo {EXCEL_FILE} não encontrado!")
                return pd.DataFrame()
            
            if EXCEL_FILE.endswith('.xlsx'):
                df = pd.read_excel(EXCEL_FILE, engine='openpyxl')
            elif EXCEL_FILE.endswith('.xls'):
                df = pd.read_excel(EXCEL_FILE, engine='xlrd')
            elif EXCEL_FILE.endswith('.csv'):
                df = pd.read_csv(EXCEL_FILE, encoding='utf-8', delimiter=';')
            else:
                print(f" Formato não suportado: {EXCEL_FILE}")
                return pd.DataFrame()
            
            print(f" Excel carregado: {len(df)} registros")
            return df
            
        except Exception as e:
            print(f" Erro ao carregar Excel: {e}")
            return pd.DataFrame()

    def identificar_colunas(df):
        """Identifica as colunas importantes no DF"""
        colunas_identificadas = {}
        
        for tipo, possiveis_nomes in COLUNAS_ESPERADAS.items():
            for col in df.columns:
                col_lower = str(col).lower()
                for nome in possiveis_nomes:
                    if nome in col_lower:
                        colunas_identificadas[tipo] = col
                        print(f"🎯 Coluna de {tipo} encontrada: '{col}'")
                        break
                if tipo in colunas_identificadas:
                    break
        
        for tipo in ['descricao', 'valor']:
            if tipo not in colunas_identificadas:
                print(f" Coluna de {tipo} não encontrada. Colunas disponíveis: {list(df.columns)}")
        
        return colunas_identificadas