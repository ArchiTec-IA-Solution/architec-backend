# main.py
from flask import Flask, jsonify
from flask_cors import CORS
from zhipuai import ZhipuAI

from config import EXCEL_FILE, api_key
from chat.chat_router import chat_bp
from pdfs.tables.table_service import TableService
from products.products_router import products_bp

# --- CONFIGURAÇÃO ---
app = Flask(__name__)
CORS(app)  # se quiser restringir: CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})

# Rota índice (já que você anuncia "/" nos prints)
@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "ok", "message": "API Flask online", "excel": EXCEL_FILE})

# Inicializar cliente Zhipu AI
try:
    if not api_key:
        raise ValueError("ZHIPU_API_KEY ausente no config/.env")
    client = ZhipuAI(api_key=api_key)
    print("✅ Cliente Zhipu AI inicializado com sucesso!")
except Exception as e:
    print(f"❌ Erro ao inicializar cliente Zhipu AI: {e}")
    client = None

# Blueprints
app.register_blueprint(chat_bp)       # certifique-se do url_prefix no chat_bp
app.register_blueprint(products_bp)   # certifique-se do url_prefix no products_bp

def print_rotas(app: Flask):
    print("\n🔎 Rotas registradas de verdade (url_map):")
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        methods = ",".join(sorted(m for m in rule.methods if m not in ("HEAD", "OPTIONS")))
        print(f"  {rule.rule:40s}  [{methods}]  → endpoint: {rule.endpoint}")

if __name__ == '__main__':
    print("🚀 Iniciando servidor Flask...")
    print(f"📄 Lendo do Excel: {EXCEL_FILE}")

    try:
        df = TableService.carregar_excel()
        if df is not None and not df.empty:
            colunas = TableService.identificar_colunas(df)
            print(f"✅ Pronto! {len(df)} produtos carregados")
            print(f"🧭 Colunas identificadas: {colunas}")
        else:
            print("⚠️ Excel vazio ou não carregado.")
    except Exception as e:
        print(f"❌ Problema ao carregar Excel: {e}")

    # Mostra rotas reais
    print_rotas(app)

    # Dica: confira se essas URLs batem com os url_prefix dos blueprints
    # Ex.: se products_bp = Blueprint("products", __name__, url_prefix="/admin"),
    # então /admin/verificar-excel existe, mas /verificar-excel sozinho não.
    print("\n📌 Endpoints esperados (confira com o url_map acima):")
    print("   GET  http://localhost:5001/                     - Interface principal")
    print("   POST http://localhost:5001/extract-products     - Extrair produtos (se for sem prefixo)")
    print("   GET  http://localhost:5001/admin/verificar-excel- Verificar Excel (se url_prefix='/admin')")
    print("   GET  http://localhost:5001/testar-busca/PRODUTO - Testar busca")
    print("   POST http://localhost:5001/debug/busca          - Debug de busca")
    print("   (e o que mais aparecer no url_map acima)")

    app.run(debug=True, port=5001, host='0.0.0.0')
