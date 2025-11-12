from reportlab.lib.colors import black, white
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from pdfs.tables.cores import COR_TEXTO

class PDFGenerator:
    """Centraliza a lógica de criação e formatação do PDF."""
    
    def __init__(self, nome_cliente="Orçamento"):
        self.nome_cliente = nome_cliente
        
        self.styles = getSampleStyleSheet()
        
        normal_style = self.styles.get('Normal', ParagraphStyle(name='Normal'))
        
        
        self.styles.add(ParagraphStyle(name='Bold', 
                                       parent=normal_style, 
                                       fontName='Helvetica-Bold', 
                                       fontSize=12))
                                       
        self.styles.add(ParagraphStyle(name='TabelaHeader', 
                                       parent=normal_style,
                                       fontName='Helvetica-Bold', 
                                       fontSize=10, 
                                       textColor=white))
                                       
        self.styles.add(ParagraphStyle(name='TabelaContent', 
                                       parent=normal_style,
                                       fontName='Helvetica', 
                                       fontSize=9, 
                                       textColor=COR_TEXTO))
                                       
        self.styles.add(ParagraphStyle(name='Small', 
                                       parent=normal_style,
                                       fontName='Helvetica', 
                                       fontSize=8, 
                                       textColor=black))