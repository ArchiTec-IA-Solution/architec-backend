from flask import Blueprint, jsonify, request
from chat.conversa import Conversa
from chat.chat_service import conversas
from ia.glm_service import GlmService
from pdfs.pdf_generator_service import PDFGeneratorService
from pdfs.tables.table_service import ESTADOS, TableService

from products.product import Produto
from products.product_service import ProdutoService

chat_bp = Blueprint("chat", __name__, url_prefix="/chat")

@chat_bp.route('/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS':
        return '', 200
        
    data = request.get_json()
    if not data:
        return jsonify({"error": "Dados JSON inválidos"}), 400
        
    user_message = data.get('message', '')
    session_id = data.get('session_id', 'default')
    mode = data.get('mode', 'single')
    products_data = data.get('products', [])

    if not user_message and not products_data:
        return jsonify({"error": "Mensagem não pode ser vazia."}), 400

    try:
        print(f" Mensagem recebida: {user_message} (Sessão: {session_id}, Modo: {mode})")
        
        if session_id not in conversas:
            conversas[session_id] = Conversa()
        
        conversa = conversas[session_id]
        
        
        if mode == 'multiple' and user_message == 'generate_multiple_quote' and products_data:
            conversa.reiniciar()
            
            
            produtos_orcamento = []
            for item in products_data:
                produto = Produto(
                    descricao=item['name'],
                    dimensao=item.get('dimensions'),
                    valor=item['price']
                )
                produtos_orcamento.append((produto, item['quantity']))
            
            
            response_text = ProdutoService.gerar_tabela_multiplos_produtos(produtos_orcamento)
            
            # PDF
            pdf_buffer = PDFGeneratorService.gerar_pdf_multiplos(produtos_orcamento, nome_cliente=f"Cliente {session_id}")
            if pdf_buffer:
                pdf_path = f"orcamento_temp_{session_id}.pdf"
                with open(pdf_path, "wb") as f:
                    f.write(pdf_buffer.getvalue())
                
                return jsonify({
                    "response": response_text, 
                    "pdf_url": f"/download/pdf/{session_id}",
                    "session_id": session_id
                })
            else:
                return jsonify({
                    "response": response_text,
                    "pdf_url": None,
                    "session_id": session_id
                })
        
        # Verificar se está esperando escolha de produto
        if conversa.estado == ESTADOS['MULTIPLAS_OPCOES']:
            if user_message.isdigit():
                opcao = int(user_message)
                if 1 <= opcao <= len(conversa.produtos_encontrados):
                    conversa.produto_selecionado = conversa.produtos_encontrados[opcao - 1]
                    conversa.estado = ESTADOS['PRODUTO_SELECIONADO']
                    
                    # Verificar se precisa de dimensões
                    if not conversa.produto_selecionado.dimensao:
                        conversa.estado = ESTADOS['DIMENSAO_SOLICITADA']
                        response_text = f" *Produto selecionado:* {conversa.produto_selecionado.descricao}\n\n🔍 *Por favor, informe as dimensões desejadas:*"
                        return jsonify({"response": response_text, "pdf_url": None, "session_id": session_id})
                    else:
                        # Tem dimensão, pode finalizar
                        conversa.estado = ESTADOS['ORCAMENTO_FINALIZADO']
                        tabela_resumo = TableService.gerar_tabela_resumo(conversa)
                        response_text = f"{tabela_resumo}\n\n PDF disponível para download abaixo"
                        
                        pdf_buffer = PDFGeneratorService.gerar_pdf([conversa.produto_selecionado], nome_cliente=f"Cliente {session_id}", quantidade=conversa.quantidade)
                        if pdf_buffer:
                            pdf_path = f"orcamento_temp_{session_id}.pdf"
                            with open(pdf_path, "wb") as f:
                                f.write(pdf_buffer.getvalue())
                            return jsonify({
                                "response": response_text, 
                                "pdf_url": f"/download/pdf/{session_id}",
                                "session_id": session_id
                            })
                else:
                    response_text = " *Opção inválida.* Por favor, digite um número da lista de opções."
                    return jsonify({"response": response_text, "pdf_url": None, "session_id": session_id})
        
        # Verificar se está esperando dimensões
        if conversa.estado == ESTADOS['DIMENSAO_SOLICITADA']:
            conversa.dimensao_selecionada = user_message
            conversa.produto_selecionado.dimensao = user_message
            conversa.estado = ESTADOS['ORCAMENTO_FINALIZADO']
            
            tabela_resumo = TableService.gerar_tabela_resumo(conversa)
            response_text = f"{tabela_resumo}\n\n PDF disponível para download abaixo"
            
            pdf_buffer = PDFGeneratorService.gerar_pdf([conversa.produto_selecionado], nome_cliente=f"Cliente {session_id}", quantidade=conversa.quantidade)
            if pdf_buffer:
                pdf_path = f"orcamento_temp_{session_id}.pdf"
                with open(pdf_path, "wb") as f:
                    f.write(pdf_buffer.getvalue())
                return jsonify({
                    "response": response_text, 
                    "pdf_url": f"/download/pdf/{session_id}",
                    "session_id": session_id
                })
        
        # Processar nova solicitação
        intent_data = GlmService.processar_intencao_com_glm(user_message, session_id)
        intent = intent_data.get("intent", "fazer_orcamento")
        
       
     

        if intent == "fazer_orcamento":
            conversa.reiniciar()
    
            produto_busca = intent_data.get("produto", user_message)
            quantidade_extraida = intent_data.get("quantidade", 1)
        
            
            print(f" PROCESSANDO ORÇAMENTO:")
            print(f"   Mensagem original: {user_message}")
            print(f"   Produto extraído: {produto_busca}")
            print(f"   Quantidade extraída: {quantidade_extraida} (tipo: {type(quantidade_extraida)})")
            print(f"   Intent data completo: {intent_data}")
            
           
            try:
                conversa.quantidade = int(quantidade_extraida)
            except (ValueError, TypeError):
                conversa.quantidade = 1
                print(f"⚠️ Erro ao converter quantidade, usando 1")
            
            print(f"   Quantidade final na conversa: {conversa.quantidade}")
            
            produtos_encontrados = ProdutoService.buscar_produtos_por_nome(produto_busca)
            
            if not produtos_encontrados:
                response_text = f""" *Produto não encontrado*

        Não consegui encontrar "{produto_busca}" no meu arquivo de preços."""
                return jsonify({"response": response_text, "pdf_url": None, "session_id": session_id})
            
            # Encontrou apenas um produto
            conversa.produto_selecionado = produtos_encontrados[0]
            conversa.estado = ESTADOS['PRODUTO_SELECIONADO']
            
            print(f" Produto encontrado: {conversa.produto_selecionado.descricao}")
            print(f" Valor do produto: {conversa.produto_selecionado.valor}")
            
            # Verificar se precisa de dimensões
            if not conversa.produto_selecionado.dimensao:
                conversa.estado = ESTADOS['DIMENSAO_SOLICITADA']
                response_text = f" *Produto encontrado:* {conversa.produto_selecionado.descricao}\n\n🔍 *Por favor, informe as dimensões desejadas:*"
                return jsonify({"response": response_text, "pdf_url": None, "session_id": session_id})
            else:
                # Tem dimensão, pode finalizar
                conversa.estado = ESTADOS['ORCAMENTO_FINALIZADO']
                
                # Debug antes de gerar tabela
                print(f" Antes de gerar tabela:")
                print(f"   Quantidade na conversa: {conversa.quantidade}")
                print(f"   Valor no produto: {conversa.produto_selecionado.valor}")
                
                tabela_resumo = TableService.gerar_tabela_resumo(conversa)
                response_text = f"{tabela_resumo}\n\n PDF disponível para download abaixo"
        
            pdf_buffer = PDFGeneratorService.gerar_pdf([conversa.produto_selecionado], nome_cliente=f"Cliente {session_id}", quantidade=conversa.quantidade)
            if pdf_buffer:
                pdf_path = f"orcamento_temp_{session_id}.pdf"
                with open(pdf_path, "wb") as f:
                    f.write(pdf_buffer.getvalue())
                return jsonify({
                    "response": response_text, 
                    "pdf_url": f"/download/pdf/{session_id}",
                    "session_id": session_id
                }) 
                # Fallback
                response_text = "Desculpe, não entendi. Você pode informar o nome do produto que deseja orçar?"
                return jsonify({
                    "response": response_text,
                    "pdf_url": None,
                    "session_id": session_id
                })

    except Exception as e:
        print(f" Erro no endpoint /chat: {e}")
        return jsonify({"error": "Ocorreu um erro interno no servidor."}), 500
