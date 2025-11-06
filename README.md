# Sistema de Orçamento Automatizado

Sistema Flask para geração automática de orçamentos a partir de um arquivo Excel, com interface de chat e exportação para PDF.

## 🚀 Funcionalidades

- **Chat Inteligente**: Interface de conversação para solicitação de orçamentos
- **Busca de Produtos**: Sistema flexível de busca em arquivo Excel
- **Extração Múltipla**: Identificação automática de múltiplos produtos e quantidades
- **Geração de PDF**: Criação de orçamentos profissionais em PDF
- **API GLM Integration**: Processamento de linguagem natural para melhor compreensão
- **Modo Single/Multiple**: Suporte a orçamentos individuais e múltiplos produtos

## 🛠️ Tecnologias

- **Backend**: Flask, Python
- **Frontend**: HTML, CSS, JavaScript
- **PDF**: ReportLab
- **AI**: ZhipuAI GLM-4
- **Data**: Pandas (Excel/CSV processing)
- **CORS**: Flask-CORS

## 📋 Pré-requisitos

- Python 3.7+
- Arquivo Excel/CSV com produtos (`orcamento.xlsx`)
- API Key do ZhipuAI GLM

## 🔧 Instalação

1. **Clone o repositório**:
```bash
git clone <repository-url>
cd <project-directory>
