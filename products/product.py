# --- CLASSES PARA MELHOR ORGANIZAÇÃO ---
class Produto:
    def __init__(self, descricao, dimensao=None, valor=None):
        self.descricao = descricao
        self.dimensao = dimensao
        self.valor = valor
    
    def to_dict(self):
        return {
            'descricao': self.descricao,
            'dimensao': self.dimensao,
            'valor': self.valor
        }
    
    def formatar_valor(self):
        if isinstance(self.valor, (int, float)):
            return f"R$ {self.valor:.2f}"
        return f"R$ {self.valor}" if self.valor else "Valor não informado"



