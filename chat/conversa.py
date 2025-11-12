from pdfs.tables.table_service import ESTADOS

class Conversa:
    def __init__(self):
        self.estado = ESTADOS['INICIO']
        self.produtos_encontrados = []  # Lista de produtos encontrados na busca
        self.produto_selecionado = None  # Produto escolhido pelo usuário
        self.quantidade = 1  # Quantidade desejada
        self.dimensao_selecionada = None
    
    def reiniciar(self):
        self.estado = ESTADOS['INICIO']
        self.produtos_encontrados = []
        self.produto_selecionado = None
        self.quantidade = 1
        self.dimensao_selecionada = None