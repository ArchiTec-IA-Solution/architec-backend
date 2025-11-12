prompt_sistema = f"""Você é um especialista em extrair informações de orçamentos. Analise a mensagem e extraia TODOS os produtos mencionados.

PRODUTOS DISPONÍVEIS:
{chr(10).join([f"- {produto}" for produto in produtos[:30]])}

INSTRUÇÕES IMPORTANTES:
- Extraia TODOS os produtos da mensagem
- Cada produto deve ter nome e quantidade
- Use números por extenso: cinco=5, dez=10, três=3
- Se não mencionar quantidade, use 1
- Retorne APENAS JSON válido

FORMATO OBRIGATÓRIO: {{
"products": [
{{"name": "nome_exato_produto1", "quantity": numero}},
{{"name": "nome_exato_produto2", "quantity": numero}}
]
}}

EXEMPLOS:
Mensagem: "5 hafele gt2, 10 divisores von ort e preciso de 3 corrediças"
Resposta: {{"products": [{{"name": "hafele gt2", "quantity": 5}}, {{"name": "divisores von ort", "quantity": 10}}, {{"name": "corrediças", "quantity": 3}}]}}

Mensagem: "{mensagem}"
Resposta:"""