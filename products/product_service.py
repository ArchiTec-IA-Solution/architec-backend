
import os
import re
import pandas as pd
from pdfs.tables.table_service import TableService
from products.product import Produto

class ProdutoService:
    def buscar_produtos_por_nome(nome_produto):
        """Busca produtos pelo nome no Excel com busca mais flexível"""
        try:
            df = TableService.carregar_excel()
            if df.empty:
                return []
            
            colunas = TableService.identificar_colunas(df)
            if 'descricao' not in colunas:
                return []
            
            print(f" Buscando: '{nome_produto}'")
            
            resultados = []
            termos_busca = [t for t in nome_produto.lower().split() if len(t) > 2]
            
            for idx, produto in df.iterrows():
                descricao_completa = str(produto[colunas['descricao']]).lower()
                
                # Verificar se todos os termos estão na descrição
                if all(termo in descricao_completa for termo in termos_busca):
                    resultados.append(Produto(
                        descricao=produto[colunas['descricao']],
                        dimensao=produto.get(colunas.get('dimensao', ''), None),
                        valor=produto.get(colunas['valor'], None)
                    ))
            
            # tenta busca parcial
            if not resultados and len(termos_busca) > 1:
                for termo in termos_busca:
                    mask_parcial = df[colunas['descricao']].astype(str).str.lower().str.contains(termo, na=False)
                    if mask_parcial.any():
                        for idx, produto in df[mask_parcial].iterrows():
                            if not any(p.descricao == produto[colunas['descricao']] for p in resultados):
                                resultados.append(Produto(
                                    descricao=produto[colunas['descricao']],
                                    dimensao=produto.get(colunas.get('dimensao', ''), None),
                                    valor=produto.get(colunas['valor'], None)
                                ))
            
            print(f" {len(resultados)} produto(s) encontrado(s)")
            return resultados
            
        except Exception as e:
            print(f" Erro ao buscar produto: {e}")
            return []


    def analisar_falha_busca(termo_busca):
        """Analisa por que a busca falhou e sugere alternativas"""
        try:
            df = TableService.carregar_excel()
            if df.empty:
                return "Arquivo de produtos não encontrado"
            
            colunas = TableService.identificar_colunas(df)
            if 'descricao' not in colunas:
                return "Coluna de descrição não identificada"
            
            produtos = df[colunas['descricao']].dropna().astype(str).tolist()
            
            # Buscar produtos que contenham partes do termo
            termos = termo_busca.lower().split()
            sugestoes = []
            
            for produto in produtos:
                produto_lower = produto.lower()
                for termo in termos:
                    if termo in produto_lower and len(termo) > 2:
                        sugestoes.append(produto)
                        break
            
            if sugestoes:
                return f"Produtos similares encontrados: {', '.join(sugestoes[:5])}"
            else:
                # Buscar por palavras individuais
                palavras_chave = []
                for termo in termos:
                    if len(termo) > 2:
                        for produto in produtos:
                            if termo in produto.lower():
                                palavras_chave.append(termo)
                                break
                
                if palavras_chave:
                    return f"Tente pesquisar por: {' ou '.join(palavras_chave[:3])}"
                else:
                    return "Nenhum produto similar encontrado. Verifique a ortografia."
        
        except Exception as e:
            return f"Erro na análise: {e}"

    def extrair_produtos_manualmente(mensagem):
        """Extração manual de múltiplos produtos como fallback"""
        produtos_extraidos = []
        
        print(f" Iniciando extração manual de: '{mensagem}'")
        
        # Divide a mensagem em partes usando múltiplos separadores
        separadores = [
            r',\s*',  # Vírgula seguida de espaços
            r'\s+e\s+',  # " e " entre palavras
            r'\s+e mais\s+',
            r'\s+também\s+',
            r'\s+além de\s+',
            r'\s+e\s+',  # Segundo "e" para garantir
        ]
        
        partes = [mensagem]
        
        for sep in separadores:
            novas_partes = []
            for parte in partes:
                dividido = re.split(sep, parte, flags=re.IGNORECASE)
                novas_partes.extend(dividido)
            partes = [p.strip() for p in novas_partes if p.strip()]
        
        print(f" Partes detectadas: {partes}")
        
        # Padrões para identificar produtos e quantidades
        padroes_produto = [
            # Padrão: quantidade + produto
            r'^(\d+)\s+(.+)$',
            # Padrão: produto + quantidade
            r'^(.+?)\s+(\d+)$',
            # Padrão: "quero/preciso" + quantidade + produto
            r'^(?:quero|preciso|gostaria|precisaria)\s+(\d+)\s+(.+)$',
            # Padrão: "quero/preciso" + produto + quantidade
            r'^(?:quero|preciso|gostaria|precisaria)\s+(.+?)\s+(\d+)$',
        ]
        
        for parte in partes:
            print(f" Analisando parte: '{parte}'")
            
            produto_encontrado = None
            quantidade_encontrada = 1
            
            # Tenta cada padrão
            for padrao in padroes_produto:
                match = re.match(padrao, parte.strip(), re.IGNORECASE)
                if match:
                    grupos = match.groups()
                    
                    if len(grupos) == 2:
                        # Determina qual grupo é quantidade e qual é produto
                        if grupos[0].isdigit():
                            quantidade_encontrada = int(grupos[0])
                            produto_encontrado = grupos[1].strip()
                        else:
                            produto_encontrado = grupos[0].strip()
                            quantidade_encontrada = int(grupos[1])
                        
                        print(f" Padrão encontrado: '{produto_encontrado}' - Qtd: {quantidade_encontrada}")
                        break
            
            # Se não encontrou padrão, assume que é o produto sem quantidade
            if not produto_encontrado:
                produto_encontrado = parte.strip()
                quantidade_encontrada = 1
                print(f" Sem padrão, assumindo: '{produto_encontrado}' - Qtd: {quantidade_encontrada}")
            
            # Limpa o nome do produto
            if produto_encontrado:
                # Remove palavras desnecessárias
                produto_limpo = re.sub(
                    r'\b(quero|preciso|gostaria|precisaria|de|das|dos|unidades|pcs|peças|itens|unidade|pc|peça|item)\b',
                    '',
                    produto_encontrado,
                    flags=re.IGNORECASE
                ).strip()
                
                # Remove números no início ou fim
                produto_limpo = re.sub(r'^\d+\s+|\s+\d+$', '', produto_limpo).strip()
                
                if produto_limpo:
                    print(f" Buscando produto: '{produto_limpo}'")
                    
                    # Busca o produto no Excel
                    produtos_encontrados = ProdutoService.buscar_produtos_por_nome(produto_limpo)
                    
                    if produtos_encontrados:
                        produto = produtos_encontrados[0]  # Pega o primeiro encontrado
                        
                        # Verifica se já não foi adicionado
                        ja_existe = False
                        for p in produtos_extraidos:
                            if p['name'].lower() == produto.descricao.lower():
                                # Atualiza quantidade se já existe
                                p['quantity'] += quantidade_encontrada
                                ja_existe = True
                                print(f" Produto atualizado: {produto.descricao} - Nova Qtd: {p['quantity']}")
                                break
                        
                        if not ja_existe:
                            produtos_extraidos.append({
                                'name': produto.descricao,
                                'quantity': quantidade_encontrada,
                                'price': float(produto.valor) if produto.valor else 0,
                                'dimensions': produto.dimensao
                            })
                            print(f" Produto adicionado: {produto.descricao} - Qtd: {quantidade_encontrada}")
                    else:
                        print(f" Produto não encontrado: '{produto_limpo}'")
        
        print(f" Total de produtos extraídos: {len(produtos_extraidos)}")
        return produtos_extraidos

    def gerar_resposta_multiplas_opcoes(produtos):
        """Gera resposta para quando múltiplos produtos são encontrados"""
        resposta = "🔍 *Encontrei múltiplos produtos correspondentes. Por favor, escolha uma opção:*\n\n"
        
        for i, produto in enumerate(produtos, 1):
            resposta += f"*{i}.* {produto.descricao}\n"
            if produto.dimensao:
                resposta += f"   📏 Dimensão: {produto.dimensao}\n"
            if produto.valor:
                resposta += f"   💰 Valor: {produto.formatar_valor()}\n"
            resposta += "\n"
        
        resposta += " *Digite o número da opção desejada para continuar.*"
        return resposta
