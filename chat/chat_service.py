
import re
# Armazenamento de conversas** criar o banco um dia né
conversas = {}

class ConversaService:
    def extrair_quantidade_da_mensagem(mensagem):
        """Extrai quantidade da mensagem usando múltiplos métodos"""
        
        # Método 1: Números explícitos
        numeros = re.findall(r'\b(\d+)\b', mensagem)
        if numeros:
            try:
                return int(numeros[0])
            except ValueError:
                pass
        
        # Método 2: Números por extenso
        numeros_por_extenso = {
            'zero': 0, 'um': 1, 'uma': 1, 'dois': 2, 'duas': 2, 'três': 3, 'tres': 3,
            'quatro': 4, 'cinco': 5, 'seis': 6, 'sete': 7, 'oito': 8, 'nove': 9, 'dez': 10,
            'onze': 11, 'doze': 12, 'treze': 13, 'quatorze': 14, 'catorze': 14, 'quinze': 15,
            'dezesseis': 16, 'dezessete': 17, 'dezoito': 18, 'dezenove': 19, 'vinte': 20
        }
        
        mensagem_lower = mensagem.lower()
        for palavra, numero in numeros_por_extenso.items():
            if f' {palavra} ' in f' {mensagem_lower} ' or mensagem_lower.startswith(palavra + ' ') or mensagem_lower.endswith(' ' + palavra):
                return numero
        
        # Método 3:
        padroes = [
            r'(\d+)\s+(?:unidades?|pcs?|peças?|itens?)',
            r'(?:quero|preciso|gostaria|precisaria)\s+(\d+)',
            r'(\d+)\s+(?:hafele|divisor|corrediça|dobradiça)',
        ]
        
        for padrao in padroes:
            match = re.search(padrao, mensagem_lower)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    pass
        
        return 1  