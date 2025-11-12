from dotenv import load_dotenv
import os

# Carrega o arquivo .env
load_dotenv()

# Lê as variáveis
api_key = os.getenv("ZHIPU_API_KEY")
ambiente = os.getenv("FLASK_ENV")
porta = os.getenv("PORT")

print(api_key, ambiente, porta)


EXCEL_FILE = 'orcamento.xlsx'
LOGO_PATH = 'logoBoa.png'
