from flask import Flask, request, jsonify, send_file, render_template, send_from_directory
from flask_cors import CORS
from zai import ZhipuAiClient  # Supondo que este seja o import correto para o seu cliente
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
import io
import os
import json
import re
from datetime import datetime
import uuid
from dotenv import load_dotenv

# --- CONFIGURAÇÃO ---
load_dotenv()
app = Flask(__name__)
application = app
CORS(app)
EXCEL_FILE = 'orca.xlsx'
GLM_API_KEY = os.getenv("GLM_API_KEY")


# Inicializar cliente Zhipu AI
try:
    client = ZhipuAiClient(api_key=GLM_API_KEY)
    print(" Cliente Zhipu AI inicializado com sucesso!")
except Exception as e:
    print(f" Erro ao inicializar cliente Zhipu AI: {e}")
    client = None

# --- ESTADOS DA CONVERSA (ATUALIZADOS) ---
ESTADOS = {
    'INICIO': 'INICIO',
    'TIPO_SELECIONADO': 'TIPO_SELECIONADO', # Após escolher superior/inferior
    'MULTIPLAS_OPCOES': 'MULTIPLAS_OPCOES', # Esperando escolher entre modelos
    'PRODUTO_SELECIONADO': 'PRODUTO_SELECIONADO', # Balcão escolhido, esperando personalização
    'ORCAMENTO_FINALIZADO': 'ORCAMENTO_FINALIZADO'
}

# --- NOVAS CLASSES DE DADOS ---
class Balcao:
    def __init__(self, id, nome, tipo, preco_base, descricao):
        self.id = id
        self.nome = nome
        self.tipo = tipo
        self.preco_base = preco_base
        self.descricao = descricao
        self.componentes = []
    
    def adicionar_componente(self, componente):
        self.componentes.append(componente)
    
    def calcular_preco_total(self):
        total = float(self.preco_base)
        for comp in self.componentes:
            total += comp.calcular_subtotal()
        return total
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'tipo': self.tipo,
            'preco_base': float(self.preco_base),
            'descricao': self.descricao,
            'componentes': [c.to_dict() for c in self.componentes],
            'preco_total': self.calcular_preco_total()
        }

class Componente:
    def __init__(self, nome, categoria, quantidade, marca_padrao, cor_padrao, fornecedor_padrao, preco_unitario):
        self.nome = nome
        self.categoria = categoria
        self.quantidade = quantidade
        self.marca_padrao = marca_padrao
        self.cor_padrao = cor_padrao
        self.fornecedor_padrao = fornecedor_padrao
        self.preco_unitario = preco_unitario
        self.alternativas = []
    
    def adicionar_alternativa(self, alternativa):
        self.alternativas.append(alternativa)
    
    def calcular_subtotal(self):
        return float(self.preco_unitario) * int(self.quantidade)
    
    def to_dict(self):
        return {
            'nome': self.nome,
            'categoria': self.categoria,
            'quantidade': int(self.quantidade),
            'marca_padrao': self.marca_padrao,
            'cor_padrao': self.cor_padrao,
            'fornecedor_padrao': self.fornecedor_padrao,
            'preco_unitario': float(self.preco_unitario),
            'subtotal': self.calcular_subtotal(),
            'alternativas': [a.to_dict() for a in self.alternativas]
        }

class Alternativa:
    def __init__(self, marca_alternativa, cor_alternativa, fornecedor_alternativo, preco_diferenca):
        self.marca_alternativa = marca_alternativa
        self.cor_alternativa = cor_alternativa
        self.fornecedor_alternativo = fornecedor_alternativo
        self.preco_diferenca = preco_diferenca
    
    def to_dict(self):
        return {
            'marca': self.marca_alternativa,
            'cor': self.cor_alternativa,
            'fornecedor': self.fornecedor_alternativo,
            'preco_adicional': float(self.preco_diferenca)
        }

# --- SISTEMA DE CARREGAMENTO DE DADOS ---
class SistemaBalcoes:
    def __init__(self):
        self.balcoes = {}
        self.carregar_dados()
    
    def carregar_dados(self):
        """Carrega todas as planilhas e cria a estrutura de objetos"""
        try:
            # Carregar planilha de balcões
            df_balcoes = pd.read_excel(EXCEL_FILE, sheet_name='balcoes', engine='openpyxl')
            
            for _, row in df_balcoes.iterrows():
                balcao = Balcao(
                    id=int(row['id']),
                    nome=str(row['nome']),
                    tipo=str(row['tipo']),
                    preco_base=float(row['preco_base']),
                    descricao=str(row.get('descricao', ''))
                )
                self.balcoes[balcao.id] = balcao
            
            print(f"✓ Carregados {len(self.balcoes)} balcões")
            
            # Carregar planilha de componentes
            df_componentes = pd.read_excel(EXCEL_FILE, sheet_name='componentes', engine='openpyxl')
            
            for _, row in df_componentes.iterrows():
                balcao_id = int(row['balcao_id'])
                if balcao_id in self.balcoes:
                    componente = Componente(
                        nome=str(row['componente']),
                        categoria=str(row['categoria']),
                        quantidade=int(row['quantidade']),
                        marca_padrao=str(row['marca_padrao']),
                        cor_padrao=str(row['cor_padrao']),
                        fornecedor_padrao=str(row['fornecedor_padrao']),
                        preco_unitario=float(row['preco_unitario'])
                    )
                    self.balcoes[balcao_id].adicionar_componente(componente)
            
            print(f"✓ Carregados componentes para todos os balcões")
            
            # Carregar planilha de personalizações
            df_personalizacoes = pd.read_excel(EXCEL_FILE, sheet_name='personalizacoes', engine='openpyxl')
            
            for _, row in df_personalizacoes.iterrows():
                componente_nome = str(row['componente'])
                
                # Para cada balcão, adicionar alternativa ao componente correspondente
                for balcao in self.balcoes.values():
                    for componente in balcao.componentes:
                        if componente.nome == componente_nome:
                            alternativa = Alternativa(
                                marca_alternativa=str(row['marca_alternativa']),
                                cor_alternativa=str(row['cor_alternativa']),
                                fornecedor_alternativo=str(row['fornecedor_alternativo']),
                                preco_diferenca=float(row['preco_diferenca'])
                            )
                            componente.adicionar_alternativa(alternativa)
            
            print(f"✓ Carregadas opções de personalização")
            
        except Exception as e:
            print(f"✗ Erro ao carregar dados: {e}")
            # Considerar levantar uma exceção aqui para parar a execução se os dados forem críticos
            # raise
    
    def buscar_balcoes_por_tipo(self, tipo):
        """Busca balcões por tipo (superior/inferior)"""
        return [balcao for balcao in self.balcoes.values() if balcao.tipo.lower() == tipo.lower()]
    
    def buscar_balcao_por_nome(self, nome):
        """Busca balcão pelo nome (busca parcial)"""
        for balcao in self.balcoes.values():
            if nome.lower() in balcao.nome.lower():
                return balcao
        return None
    
    def listar_todos_balcoes(self):
        """Lista todos os balcões disponíveis"""
        return list(self.balcoes.values())

# --- ATUALIZAÇÃO DA CLASSE CONVERSA ---
class ConversaBalcao:
    def __init__(self):
        self.estado = ESTADOS['INICIO']
        self.balcao_selecionado = None
        self.tipo_selecionado = None  # 'superior' ou 'inferior'
        self.personalizacoes = []  # Lista de alterações feitas no formato {'componente_nome': 'alternativa_escolhida'}
        self.orcamento_final = None
    
    def reiniciar(self):
        self.estado = ESTADOS['INICIO']
        self.balcao_selecionado = None
        self.tipo_selecionado = None
        self.personalizacoes = []
        self.orcamento_final = None
    
    def aplicar_personalizacao(self, componente_nome, alternativa_obj):
        """Aplica uma personalização ao balcão"""
        if not self.balcao_selecionado:
            return False
        
        for componente in self.balcao_selecionado.componentes:
            if componente.nome == componente_nome:
                # Verificar se a alternativa existe para este componente
                for alt in componente.alternativas:
                    if alt.marca_alternativa == alternativa_obj.marca_alternativa and alt.cor_alternativa == alternativa_obj.cor_alternativa:
                        # Se já existe uma personalização para este componente, remove a antiga
                        self.personalizacoes = [p for p in self.personalizacoes if p['componente'] != componente_nome]
                        
                        # Adiciona a nova
                        self.personalizacoes.append({
                            'componente': componente_nome,
                            'alternativa': alternativa_obj,
                            'preco_adicional_total': alternativa_obj.preco_diferenca * componente.quantidade
                        })
                        return True
        return False
    
    def calcular_orcamento_final(self):
        """Calcula o orçamento final com todas as personalizações"""
        if not self.balcao_selecionado:
            return 0
        
        total = self.balcao_selecionado.calcular_preco_total()
        for personalizacao in self.personalizacoes:
            total += personalizacao['preco_adicional_total']
        
        self.orcamento_final = total
        return total

# --- FUNÇÕES DE PROMPT E GERAÇÃO DE RESPOSTA ---
def gerar_resumo_balcao(balcao, personalizacoes_ativas=[]):
    """Gera uma string formatada com o resumo do balcão e seus componentes"""
    if not balcao:
        return "Nenhum balcão selecionado."

    resposta = f" *Orçamento para: {balcao.nome}*\n\n"
    resposta += f" *Preço Base da Estrutura:* R$ {balcao.preco_base:.2f}\n\n"
    resposta += " *Componentes Incluídos (Configuração Padrão):*\n"

    for comp in balcao.componentes:
        # Verifica se há uma personalização ativa para este componente
        personalizacao_ativa = next((p for p in personalizacoes_ativas if p['componente'] == comp.nome), None)
        
        if personalizacao_ativa:
            alt = personalizacao_ativa['alternativa']
            preco_unitario = comp.preco_unitario + alt.preco_diferenca
            descricao_alt = f" (Personalizado: {alt.marca_alternativa} - {alt.cor_alternativa})"
        else:
            preco_unitario = comp.preco_unitario
            descricao_alt = ""

        subtotal = preco_unitario * comp.quantidade
        
        resposta += f"  • *{comp.nome}* (x{comp.quantidade}) - {comp.marca_padrao} ({comp.cor_padrao}){descricao_alt}\n"
        resposta += f"    💵 Unitário: R$ {preco_unitario:.2f} | Subtotal: R$ {subtotal:.2f}\n"

        # Sugestões de personalização (só mostra se não houver personalização ativa)
        if not personalizacao_ativa and comp.alternativas:
            resposta += "    ✨ *Opções de personalização disponíveis:*\n"
            for alt in comp.alternativas:
                novo_preco = comp.preco_unitario + alt.preco_diferenca
                resposta += f"      - Trocar para {alt.marca_alternativa} ({alt.cor_alternativa}) "
                resposta += f"por R$ {novo_preco:.2f}/unid (dif. +R$ {alt.preco_diferenca:.2f})\n"
        resposta += "\n"
    
    total_final = balcao.calcular_preco_total() + sum(p['preco_adicional_total'] for p in personalizacoes_ativas)
    resposta += f"💰 *VALOR TOTAL DO ORÇAMENTO:* R$ {total_final:.2f}\n\n"
    
    if not personalizacoes_ativas:
        resposta += "🤔 *Deseja personalizar algum componente? Me diga qual e para qual opção!*\n"
        resposta += "Ex: 'Trocar a dobradiça para Hafele' ou 'Mudar a cor da frente para Madeira'.\n"
    else:
        resposta += "✅ *Personalização aplicada! Deseja alterar mais algo ou finalizar o orçamento?*\n"
        resposta += "Digite 'finalizar' para concluir e gerar o PDF."

    return resposta

# --- FUNÇÕES AUXILIARES (PDF, etc.) ---
def gerar_pdf_balcao_final(conversa):
    """Gera PDF com orçamento final do balcão"""
    try:
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        # Cabeçalho
        p.setFillColor(HexColor('#2E86AB'))
        p.rect(0, height - 100, width, 100, fill=True, stroke=False)
        
        p.setFillColorRGB(1, 1, 1)
        p.setFont("Helvetica-Bold", 20)
        p.drawString(inch, height - 1.5 * inch, f"ORÇAMENTO - {conversa.balcao_selecionado.nome}")
        
        p.setFont("Helvetica", 12)
        p.drawString(inch, height - 1.8 * inch, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        p.drawString(inch, height - 2 * inch, f"Tipo: {conversa.balcao_selecionado.tipo.capitalize()}")

        # Componentes
        y = height - 2.5 * inch
        p.setFillColorRGB(0, 0, 0)
        p.setFont("Helvetica-Bold", 12)
        p.drawString(inch, y, "ESTRUTURA E COMPONENTES:")
        y -= 0.3 * inch
        p.setFont("Helvetica", 10)
        
        # Preço base
        p.drawString(inch, y, f"Preço Base da Estrutura: R$ {conversa.balcao_selecionado.preco_base:.2f}")
        y -= 0.25 * inch

        for comp in conversa.balcao_selecionado.componentes:
            p.drawString(inch, y, f"• {comp.nome}:")
            y -= 0.2 * inch
            
            # Verifica se foi personalizado
            personalizacao = next((p for p in conversa.personalizacoes if p['componente'] == comp.nome), None)
            if personalizacao:
                alt = personalizacao['alternativa']
                marca, cor = alt.marca_alternativa, alt.cor_alternativa
                preco = comp.preco_unitario + alt.preco_diferenca
            else:
                marca, cor = comp.marca_padrao, comp.cor_padrao
                preco = comp.preco_unitario
            
            p.drawString(1.5 * inch, y, f"Marca/Cor: {marca} ({cor}) | Qtd: {comp.quantidade} | Unitário: R$ {preco:.2f}")
            y -= 0.2 * inch
            p.drawString(1.5 * inch, y, f"Subtotal: R$ {preco * comp.quantidade:.2f}")
            y -= 0.3 * inch

            if y < 150: # Adiciona nova página se estiver acabando o espaço
                p.showPage()
                y = height - inch

        # Personalizações Aplicadas
        if conversa.personalizacoes:
            y -= 0.2 * inch
            p.setFont("Helvetica-Bold", 12)
            p.drawString(inch, y, "PERSONALIZAÇÕES APLICADAS:")
            y -= 0.3 * inch
            p.setFont("Helvetica", 10)
            
            for p_item in conversa.personalizacoes:
                alt = p_item['alternativa']
                p.drawString(inch, y, f"• {p_item['componente']}: Alterado para {alt.marca_alternativa} ({alt.cor_alternativa})")
                y -= 0.2 * inch
                p.drawString(1.5 * inch, y, f"  Adicional no total: +R$ {p_item['preco_adicional_total']:.2f}")
                y -= 0.3 * inch
        
        # Totais
        y -= 0.2 * inch
        p.setFont("Helvetica-Bold", 12)
        p.drawString(inch, y, "RESUMO FINANCEIRO:")
        y -= 0.3 * inch
        p.setFont("Helvetica", 10)
        
        subtotal_padrao = conversa.balcao_selecionado.calcular_preco_total()
        p.drawString(inch, y, f"Subtotal Padrão: R$ {subtotal_padrao:.2f}")
        y -= 0.2 * inch
        
        if conversa.personalizacoes:
            total_personalizacoes = sum(p['preco_adicional_total'] for p in conversa.personalizacoes)
            p.drawString(inch, y, f"Adicional Personalizações: +R$ {total_personalizacoes:.2f}")
            y -= 0.2 * inch
        
        y -= 0.1 * inch
        p.setFont("Helvetica-Bold", 14)
        total_final = conversa.calcular_orcamento_final()
        p.drawString(inch, y, f"VALOR TOTAL FINAL: R$ {total_final:.2f}")

        p.save()
        buffer.seek(0)
        return buffer
        
    except Exception as e:
        print(f"Erro ao gerar PDF: {e}")
        import traceback
        traceback.print_exc()
        return None

# Armazenamento de conversas (usará a nova classe)
conversas = {}

# Inicializa o sistema de balcões uma vez no início
sistema_balcoes = SistemaBalcoes()

# --- ENDPOINTS DA API ---
@app.route('/')
def index():
    """Serve the main chat interface"""
    return render_template('index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

@app.route('/balcoes', methods=['GET'])
def listar_balcoes():
    """Lista todos os balcões disponíveis"""
    try:
        balcoes = sistema_balcoes.listar_todos_balcoes()
        
        resultado = []
        for balcao in balcoes:
            resultado.append({
                'id': balcao.id,
                'nome': balcao.nome,
                'tipo': balcao.tipo,
                'preco_base': float(balcao.preco_base),
                'descricao': balcao.descricao,
                'preco_total': balcao.calcular_preco_total(),
                'componentes': len(balcao.componentes)
            })
        
        return jsonify({
            "total": len(resultado),
            "balcoes": resultado
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS':
        return '', 200
        
    data = request.get_json()
    if not data:
        return jsonify({"error": "Dados JSON inválidos"}), 400
        
    user_message = data.get('message', '').strip()
    session_id = data.get('session_id', 'default')

    if not user_message:
        return jsonify({"error": "Mensagem não pode ser vazia."}), 400

    try:
        print(f"📨 Mensagem: '{user_message}' (Sessão: {session_id})")
        
        # Verificar se é uma nova sessão
        if session_id not in conversas:
            conversas[session_id] = ConversaBalcao()
        
        conversa = conversas[session_id]
        
        # Lógica de estados
        if conversa.estado == ESTADOS['INICIO']:
            user_lower = user_message.lower()
            
            # Detectar tipo de balcão solicitado
            if any(palavra in user_lower for palavra in ['inferior', 'embaixo', 'baixo', 'gaveta']):
                conversa.tipo_selecionado = 'inferior'
                balcoes_opcao = sistema_balcoes.buscar_balcoes_por_tipo('inferior')
                
                if len(balcoes_opcao) > 1:
                    resposta = "🔍 *Encontrei múltiplas opções de balcão inferior. Por favor, escolha uma:*\n\n"
                    for i, balcao in enumerate(balcoes_opcao, 1):
                        resposta += f"*{i}.* {balcao.nome} - R$ {balcao.calcular_preco_total():.2f}\n"
                        resposta += f"   {balcao.descricao}\n\n"
                    resposta += "Digite o número da opção desejada."
                    conversa.estado = ESTADOS['TIPO_SELECIONADO']
                    return jsonify({"response": resposta, "pdf_url": None, "session_id": session_id})
                elif len(balcoes_opcao) == 1:
                    conversa.balcao_selecionado = balcoes_opcao[0]
                    conversa.estado = ESTADOS['PRODUTO_SELECIONADO']
                    resposta = gerar_resumo_balcao(conversa.balcao_selecionado, conversa.personalizacoes)
                    return jsonify({"response": resposta, "pdf_url": None, "session_id": session_id})
                else:
                    return jsonify({"response": "❌ Nenhum balcão inferior encontrado.", "pdf_url": None, "session_id": session_id})

            elif any(palavra in user_lower for palavra in ['superior', 'em cima', 'alto', 'armário']):
                conversa.tipo_selecionado = 'superior'
                balcoes_opcao = sistema_balcoes.buscar_balcoes_por_tipo('superior')

                if len(balcoes_opcao) > 1:
                    resposta = "🔍 *Encontrei múltiplas opções de balcão superior. Por favor, escolha uma:*\n\n"
                    for i, balcao in enumerate(balcoes_opcao, 1):
                        resposta += f"*{i}.* {balcao.nome} - R$ {balcao.calcular_preco_total():.2f}\n"
                        resposta += f"   {balcao.descricao}\n\n"
                    resposta += "Digite o número da opção desejada."
                    conversa.estado = ESTADOS['TIPO_SELECIONADO']
                    return jsonify({"response": resposta, "pdf_url": None, "session_id": session_id})
                elif len(balcoes_opcao) == 1:
                    conversa.balcao_selecionado = balcoes_opcao[0]
                    conversa.estado = ESTADOS['PRODUTO_SELECIONADO']
                    resposta = gerar_resumo_balcao(conversa.balcao_selecionado, conversa.personalizacoes)
                    return jsonify({"response": resposta, "pdf_url": None, "session_id": session_id})
                else:
                    return jsonify({"response": "❌ Nenhum balcão superior encontrado.", "pdf_url": None, "session_id": session_id})

            else:
                # Buscar por nome específico
                balcao = sistema_balcoes.buscar_balcao_por_nome(user_message)
                if balcao:
                    conversa.balcao_selecionado = balcao
                    conversa.estado = ESTADOS['PRODUTO_SELECIONADO']
                    resposta = gerar_resumo_balcao(conversa.balcao_selecionado, conversa.personalizacoes)
                    return jsonify({"response": resposta, "pdf_url": None, "session_id": session_id})
                else:
                    response_text = "🔍 Não encontrei um balcão com esse nome. Você quer um balcão **superior** ou **inferior**?"
                    return jsonify({"response": response_text, "pdf_url": None, "session_id": session_id})
        
        elif conversa.estado == ESTADOS['TIPO_SELECIONADO']:
            # Usuário escolhendo entre opções de balcão
            if user_message.isdigit():
                opcao = int(user_message)
                balcoes = sistema_balcoes.buscar_balcoes_por_tipo(conversa.tipo_selecionado)
                
                if 1 <= opcao <= len(balcoes):
                    conversa.balcao_selecionado = balcoes[opcao - 1]
                    conversa.estado = ESTADOS['PRODUTO_SELECIONADO']
                    resposta = gerar_resumo_balcao(conversa.balcao_selecionado, conversa.personalizacoes)
                    return jsonify({"response": resposta, "pdf_url": None, "session_id": session_id})
                else:
                    response_text = f"❌ Opção inválida. Digite um número de 1 a {len(balcoes)}."
                    return jsonify({"response": response_text, "pdf_url": None, "session_id": session_id})
            else:
                response_text = "❌ Por favor, digite apenas o número da opção desejada."
                return jsonify({"response": response_text, "pdf_url": None, "session_id": session_id})
        
        elif conversa.estado == ESTADOS['PRODUTO_SELECIONADO']:
            # Processar personalizações ou finalização
            if user_message.lower() in ['finalizar', 'concluir', 'pronto', 'gerar pdf']:
                conversa.estado = ESTADOS['ORCAMENTO_FINALIZADO']
                total_final = conversa.calcular_orcamento_final()
                
                resumo_final = f"✅ *Orçamento Finalizado!*\n\n"
                resumo_final += f"📋 *Produto:* {conversa.balcao_selecionado.nome}\n"
                resumo_final += f"💰 *Valor Total:* R$ {total_final:.2f}\n\n"
                resumo_final += "📄 PDF disponível para download abaixo."
                
                pdf_buffer = gerar_pdf_balcao_final(conversa)
                if pdf_buffer:
                    pdf_path = f"orcamento_balcao_{session_id}.pdf"
                    with open(pdf_path, "wb") as f:
                        f.write(pdf_buffer.getvalue())
                    
                    return jsonify({
                        "response": resumo_final,
                        "pdf_url": f"/download/pdf/{session_id}",
                        "session_id": session_id
                    })
                else:
                    return jsonify({"response": "❌ Erro ao gerar o PDF.", "pdf_url": None, "session_id": session_id})

            # Tentar entender a personalização com IA
            if not client:
                # Fallback simples se a IA não estiver disponível
                return jsonify({"response": "🤖 IA não disponível. Não consigo processar personalizações no momento. Digite 'finalizar' para concluir.", "pdf_url": None, "session_id": session_id})
            
            try:
                # Montar prompt para a IA
                componentes_disponiveis = "\n".join([f"- {c.nome}" for c in conversa.balcao_selecionado.componentes])
                
                prompt_ia = f"""
O cliente quer personalizar o balcão "{conversa.balcao_selecionado.nome}".
Componentes disponíveis: {componentes_disponiveis}

Mensagem do cliente: "{user_message}"

Analise a mensagem e retorne APENAS um JSON com a personalização desejada. Se não entender, retorne {{"acao": "nao_entendido"}}.
O JSON deve ter o seguinte formato:
{{"acao": "personalizar", "componente": "nome_do_componente", "marca_alternativa": "marca", "cor_alternativa": "cor"}}
Exemplo: Mensagem "trocar dobradiça para hafele preto" -> {{"acao": "personalizar", "componente": "dobradiça", "marca_alternativa": "Hafele", "cor_alternativa": "Preto"}}
"""
                response = client.chat.completions.create(
                    model="glm-4",
                    messages=[
                        {"role": "system", "content": "Você é um assistente que entende pedidos de personalização de móveis."},
                        {"role": "user", "content": prompt_ia}
                    ],
                    max_tokens=150,
                    temperature=0.1
                )
                
                resposta_texto = response.choices[0].message.content.strip()
                print(f"Resposta da IA para personalização: {resposta_texto}")
                
                json_match = re.search(r'\{.*\}', resposta_texto, re.DOTALL)
                if json_match:
                    acao_data = json.loads(json_match.group())
                    
                    if acao_data.get("acao") == "personalizar":
                        componente_nome = acao_data.get("componente")
                        marca_alt = acao_data.get("marca_alternativa")
                        cor_alt = acao_data.get("cor_alternativa")
                        
                        # Encontrar o objeto Alternativa correto
                        componente_obj = next((c for c in conversa.balcao_selecionado.componentes if c.nome.lower() == componente_nome.lower()), None)
                        if componente_obj:
                            alternativa_obj = next((a for a in componente_obj.alternativas if a.marca_alternativa.lower() == marca_alt.lower() and a.cor_alternativa.lower() == cor_alt.lower()), None)
                            
                            if alternativa_obj:
                                sucesso = conversa.aplicar_personalizacao(componente_obj.nome, alternativa_obj)
                                if sucesso:
                                    resposta = gerar_resumo_balcao(conversa.balcao_selecionado, conversa.personalizacoes)
                                    return jsonify({"response": resposta, "pdf_url": None, "session_id": session_id})
                                else:
                                    return jsonify({"response": "❌ Erro ao aplicar personalização.", "pdf_url": None, "session_id": session_id})
                            else:
                                return jsonify({"response": f"❌ Não encontrei a alternativa '{marca_alt} ({cor_alt})' para o componente '{componente_nome}'. Verifique as opções disponíveis.", "pdf_url": None, "session_id": session_id})
                        else:
                            return jsonify({"response": f"❌ Componente '{componente_nome}' não encontrado neste balcão.", "pdf_url": None, "session_id": session_id})
                    else:
                        return jsonify({"response": "🤔 Não entendi sua solicitação. Pode reformular? Ex: 'Trocar a dobradiça para Hafele'.", "pdf_url": None, "session_id": session_id})
                else:
                     return jsonify({"response": "🤖 Não consegui processar sua solicitação. Pode tentar de outra forma?", "pdf_url": None, "session_id": session_id})

            except Exception as e:
                print(f"Erro na IA ao processar personalização: {e}")
                return jsonify({"response": "❌ Ocorreu um erro ao processar sua solicitação de personalização.", "pdf_url": None, "session_id": session_id})

        # Fallback geral
        return jsonify({"response": "🤔 Não entendi. Você pode reformular sua mensagem ou digitar 'finalizar' para concluir?", "pdf_url": None, "session_id": session_id})

    except Exception as e:
        print(f" Erro no endpoint /chat: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Ocorreu um erro interno no servidor."}), 500

@app.route('/download/pdf/<session_id>')
def download_pdf(session_id):
    pdf_path = f"orcamento_balcao_{session_id}.pdf"
    if os.path.exists(pdf_path):
        return send_file(pdf_path, as_attachment=True, download_name=f"orcamento_{session_id}.pdf")
    return jsonify({"error": "PDF não encontrado"}), 404

if __name__ == '__main__':
    print("🚀 Iniciando servidor Flask com o novo sistema de orçamentos...")
    print(f"📁 Lendo do Excel: {EXCEL_FILE}")
    
    if not sistema_balcoes.balcoes:
        print("❌ Nenhum balcão carregado. Verifique o arquivo Excel e as abas 'balcoes', 'componentes' e 'personalizacoes'.")
    else:
        print(f"✅ Pronto! {len(sistema_balcoes.balcoes)} balcões carregados com sucesso.")
    
    print("\n🔗 Endpoints disponíveis:")
    print("   http://localhost:5001/ - Interface principal")
    print("   http://localhost:5001/chat - Chat principal")
    print("   http://localhost:5001/balcoes - Listar todos os balcões (API)")
    
    app.run(debug=True, port=5001, host='0.0.0.0')
