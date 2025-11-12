
import os
from flask import Blueprint, jsonify, render_template, request, send_file, send_from_directory

from chat.chat_service import ConversaService
from config import EXCEL_FILE
from ia.glm_service import GlmService
from pdfs.tables.table_service import TableService
from products.product_service import ProdutoService


products_bp = Blueprint("products", __name__, url_prefix="/products")

@products_bp.route('/')
def index():
    """Serve the main chat interface"""
    return render_template('index.html')

@products_bp.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files"""
    return send_from_directory('static', filename)


@products_bp.route('/download/pdf/<session_id>')
def download_pdf(session_id):
    pdf_path = f"orcamento_temp_{session_id}.pdf"
    if os.path.exists(pdf_path):
        return send_file(pdf_path, as_attachment=True, download_name=f"orcamento_{session_id}.pdf")
    return jsonify({"error": "PDF não encontrado"}), 404


#necessário logica de seguraça
@products_bp.route('/admin/verificar-excel', methods=['GET'])
def verificar_excel():
    """Endpoint para verificar o arquivo Excel"""
    try:
        df = TableService.carregar_excel()
        
        info = {
            "arquivo_existe": os.path.exists(EXCEL_FILE),
            "total_registros": len(df) if not df.empty else 0,
            "colunas": list(df.columns) if not df.empty else []
        }
        
        if not df.empty:
            colunas = TableService.identificar_colunas(df)
            info.update(colunas)
            
            if 'descricao' in colunas:
                info["produtos_exemplo"] = df[colunas['descricao']].head(5).tolist()
            
            if 'valor' in colunas:
                info["valores_exemplo"] = df[colunas['valor']].head(5).tolist()
        
        return jsonify(info)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@products_bp.route('/testar-busca/<nome_produto>', methods=['GET'])
def testar_busca(nome_produto):
    """Endpoint para testar a busca de produtos"""
    try:
        produtos = ProdutoService.buscar_produtos_por_nome(nome_produto)
        produtos_dict = [p.to_dict() for p in produtos]
        return jsonify({
            "produto_buscado": nome_produto,
            "resultados": produtos_dict
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@products_bp.route('/debug/busca', methods=['POST'])
def debug_busca():
    """Endpoint para debug da busca de produtos"""
    data = request.get_json()
    termo = data.get('termo', '')
    
    if not termo:
        return jsonify({"error": "Termo de busca não fornecido"}), 400
    
    try:
        # Buscar produtos
        produtos = ProdutoService.buscar_produtos_por_nome(termo)
        produtos_dict = [p.to_dict() for p in produtos]
        
        # Analisar falha se não encontrou
        analise = None
        if not produtos:
            analise = ProdutoService.analisar_falha_busca(termo)
        
        # Tentar processar com GLM
        glm_result = GlmService.processar_intencao_com_glm(termo)
        
        return jsonify({
            "termo_busca": termo,
            "produtos_encontrados": produtos_dict,
            "analise_falha": analise,
            "glm_result": glm_result
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@products_bp.route('/testar-quantidade', methods=['POST'])
def testar_quantidade():
    """Endpoint para testar extração de quantidade"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Dados JSON inválidos"}), 400
    
    message = data.get('message', '')
    
    if not message:
        return jsonify({"error": "Mensagem não pode ser vazia"}), 400
    
    try:
        resultado = GlmService.processar_intencao_com_glm(message)
        return jsonify({
            "mensagem_original": message,
            "resultado": resultado
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@products_bp.route('/testar-multiplicacao', methods=['POST'])
def testar_multiplicacao():
    """Endpoint para testar multiplicação"""
    data = request.get_json()
    message = data.get('message', '')
    
    # Testa extração
    quantidade = ConversaService.extrair_quantidade_da_mensagem(message)
    intent_data = GlmService.processar_intencao_com_glm(message)
    
    # Testa busca
    produtos = ProdutoService.buscar_produtos_por_nome(intent_data.get('produto', message))
    
    if produtos:
        produto = produtos[0]
        valor_unitario = float(produto.valor) if produto.valor else 0
        valor_total = valor_unitario * intent_data.get('quantidade', 1)
        
        return jsonify({
            "mensagem": message,
            "quantidade_extraida": quantidade,
            "intent_data": intent_data,
            "produto_encontrado": produto.descricao,
            "valor_unitario": valor_unitario,
            "valor_total": valor_total,
            "calculo": f"{intent_data.get('quantidade', 1)} × {valor_unitario} = {valor_total}"
        })
    else:
        return jsonify({"error": "Produto não encontrado"})

@products_bp.route('/extract-products', methods=['POST'])
def extract_products():
    """Endpoint para extrair múltiplos produtos de uma mensagem"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Dados JSON inválidos"}), 400
    
    message = data.get('message', '')
    session_id = data.get('session_id', 'default')
    
    if not message:
        return jsonify({"error": "Mensagem não pode ser vazia"}), 400
    
    try:
        produtos = GlmService.extrair_produtos_da_mensagem(message)
        return jsonify({"products": produtos})
    except Exception as e:
        print(f" Erro no endpoint /extract-products: {e}")
        return jsonify({"error": "Ocorreu um erro interno"}), 500

