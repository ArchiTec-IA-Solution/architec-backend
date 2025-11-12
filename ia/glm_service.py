

from http import client
import json
import re

from chat.chat_service import ConversaService, conversas
from pdfs.tables.table_service import TableService, ESTADOS

from products.product_service import ProdutoService

class GlmService:
    def extrair_produtos_da_mensagem(mensagem):
        """Usa GLM para extrair múltiplos produtos e quantidades de uma mensagem"""
        if not client:
            # Fallback sem GLM - extração manual
            print(" GLM não disponível, usando extração manual")
            return ProdutoService.extrair_produtos_manualmente(mensagem)
        
        try:
            df = TableService.carregar_excel()
            if df.empty:
                print(" Excel vazio, usando extração manual")
                return ProdutoService.extrair_produtos_manualmente(mensagem)
            
            colunas = TableService.identificar_colunas(df)
            if 'descricao' not in colunas:
                print(" Coluna descrição não encontrada, usando extração manual")
                return ProdutoService.extrair_produtos_manualmente(mensagem)
            
            produtos = df[colunas['descricao']].dropna().astype(str).tolist()
            
            # Prompt melhorado para múltiplos produtos
            prompt_sistema = prompt_sistema
            response = client.chat.completions.create(
                model="glm-4",
                messages=[
                    {"role": "system", "content": prompt_sistema},
                    {"role": "user", "content": mensagem}
                ],
                max_tokens=400,
                temperature=0.1
            )

            resposta_texto = response.choices[0].message.content.strip()
            print(f" Resposta GLM (múltiplos produtos): {resposta_texto}")
            
            try:
                json_match = re.search(r'\{.*\}', resposta_texto, re.DOTALL)
                if json_match:
                    resultado = json.loads(json_match.group())
                    if 'products' in resultado and resultado['products']:
                        produtos_extraidos = []
                        for item in resultado['products']:
                            # Buscar cada produto no Excel
                            produtos_encontrados = ProdutoService.buscar_produtos_por_nome(item['name'])
                            if produtos_encontrados:
                                produto = produtos_encontrados[0]
                                produtos_extraidos.append({
                                    'name': produto.descricao,
                                    'quantity': max(1, int(item.get('quantity', 1))),
                                    'price': float(produto.valor) if produto.valor else 0,
                                    'dimensions': produto.dimensao
                                })
                                print(f" Produto GLM: {produto.descricao} - Qtd: {item.get('quantity', 1)}")
                            else:
                                print(f" Produto não encontrado: {item['name']}")
                        
                        if produtos_extraidos:
                            return produtos_extraidos
            except json.JSONDecodeError as e:
                print(f" Erro JSON GLM: {e}")
            
            # Fallback para extração manual
            print(" Usando fallback manual para múltiplos produtos")
            return ProdutoService.extrair_produtos_manualmente(mensagem)
            
        except Exception as e:
            print(f" Erro ao extrair múltiplos produtos: {e}")
            return ProdutoService.extrair_produtos_manualmente(mensagem)

    def processar_intencao_com_glm(mensagem, session_id=None):
        """Usa a API GLM para identificar a intenção, produto e quantidade"""
        if not client:
            # Fallback sem GLM
            quantidade = ConversaService.extrair_quantidade_da_mensagem(mensagem)
            return {"intent": "fazer_orcamento", "produto": mensagem, "quantidade": quantidade}
        
        try:
            df = TableService.carregar_excel()
            if df.empty:
                quantidade = ConversaService.extrair_quantidade_da_mensagem(mensagem)
                return {"intent": "fazer_orcamento", "produto": mensagem, "quantidade": quantidade}
            
            colunas = TableService.identificar_colunas(df)
            if 'descricao' not in colunas:
                quantidade = ConversaService.extrair_quantidade_da_mensagem(mensagem)
                return {"intent": "fazer_orcamento", "produto": mensagem, "quantidade": quantidade}
            
            produtos = df[colunas['descricao']].dropna().astype(str).tolist()
            
            if session_id and session_id in conversas:
                conversa = conversas[session_id]
                if conversa.estado == ESTADOS['DIMENSAO_SOLICITADA']:
                    return {"intent": "fornecer_dimensao", "dimensao": mensagem}
            
            # Prompt simplificado mas mais eficaz
            prompt_sistema = f"""Extraia o produto e a quantidade da mensagem.

    PRODUTOS DISPONÍVEIS:
    {chr(10).join([f"- {produto}" for produto in produtos[:20]])}

    RETORNE APENAS JSON:
    {{
    "intent": "fazer_orcamento",
    "produto": "nome_produto",
    "quantidade": numero
    }}

    Mensagem: "{mensagem}"
    JSON:"""
            
            response = client.chat.completions.create(
                model="glm-4",
                messages=[
                    {"role": "system", "content": prompt_sistema},
                    {"role": "user", "content": mensagem}
                ],
                max_tokens=100,
                temperature=0.1
            )

            resposta_texto = response.choices[0].message.content.strip()
            print(f" Resposta GLM bruta: {resposta_texto}")
            
            # Tentativa 1: JSON completo
            try:
                json_match = re.search(r'\{.*\}', resposta_texto, re.DOTALL)
                if json_match:
                    resultado = json.loads(json_match.group())
                    
                    # Processa quantidade
                    if 'quantidade' in resultado:
                        quantidade = resultado['quantidade']
                        if isinstance(quantidade, str):
                            # Extrai números da string
                            nums = re.findall(r'\d+', quantidade)
                            quantidade = int(nums[0]) if nums else 1
                        else:
                            quantidade = int(quantidade)
                        
                        quantidade = max(1, quantidade)  # Garante mínimo 1
                        resultado['quantidade'] = quantidade
                        
                        print(f" GLM funcionou - Produto: {resultado.get('produto')}, Qtd: {quantidade}")
                        return resultado
            except Exception as e:
                print(f" Erro no JSON do GLM: {e}")
            
            # Fallback: extração manual
            print(" Usando fallback de extração manual")
            quantidade_fallback = ConversaService.extrair_quantidade_da_mensagem(mensagem)
            print(f" Quantidade extraída manualmente: {quantidade_fallback}")
            
            return {
                "intent": "fazer_orcamento", 
                "produto": mensagem, 
                "quantidade": quantidade_fallback
            }
            
        except Exception as e:
            print(f" Erro completo no GLM: {e}")
            quantidade = ConversaService.extrair_quantidade_da_mensagem(mensagem)
            return {"intent": "fazer_orcamento", "produto": mensagem, "quantidade": quantidade}



