# app.py
from flask import Flask, request, jsonify, render_template_string
import sqlite3
import os
from datetime import datetime

# Define o nome do arquivo do banco de dados
DB_FILE = 'clientes.db'

app = Flask(__name__)

# Função para conectar ao banco de dados
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# Cria a tabela de clientes se ela não existir
def create_db_table():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hwid TEXT NOT NULL UNIQUE,
            license_key TEXT NOT NULL,
            last_seen TIMESTAMP NOT NULL
        );
    ''')
    conn.commit()
    conn.close()

# Chama a função para garantir que o banco de dados e a tabela existam na inicialização
create_db_table()

# Rota para receber dados dos clientes. Esta é a API para seu programa.
@app.route('/monitorar', methods=['POST'])
def monitorar_cliente():
    """
    Recebe os dados do cliente (HWID e chave de licença) e salva/atualiza no banco de dados.
    """
    if not request.is_json:
        return jsonify({"status": "erro", "mensagem": "Formato de dados inválido. Esperado JSON."}), 400

    dados = request.get_json()
    hwid = dados.get('hwid')
    license_key = dados.get('license_key')

    if not hwid or not license_key:
        return jsonify({"status": "erro", "mensagem": "HWID e license_key são campos obrigatórios."}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Tenta encontrar um cliente com o HWID fornecido
        cursor.execute("SELECT * FROM clientes WHERE hwid = ?", (hwid,))
        cliente_existente = cursor.fetchone()

        if cliente_existente:
            # Se o cliente já existe, atualiza apenas o timestamp
            cursor.execute(
                "UPDATE clientes SET last_seen = ? WHERE hwid = ?",
                (datetime.now(), hwid)
            )
            mensagem = "Cliente existente atualizado."
        else:
            # Se é um cliente novo, insere um novo registro
            cursor.execute(
                "INSERT INTO clientes (hwid, license_key, last_seen) VALUES (?, ?, ?)",
                (hwid, license_key, datetime.now())
            )
            mensagem = "Novo cliente registrado."
        
        conn.commit()
        conn.close()

        print(f"[{datetime.now()}] {mensagem} - HWID: {hwid[:10]}... | Licença: {license_key}")
        
        return jsonify({"status": "sucesso", "mensagem": mensagem}), 200

    except sqlite3.Error as e:
        print(f"Erro no banco de dados: {e}")
        return jsonify({"status": "erro", "mensagem": f"Erro interno do servidor: {e}"}), 500

# Rota do painel de monitoramento (dashboard) para o seu uso
@app.route('/')
def dashboard():
    """
    Exibe uma tabela com os clientes que enviaram dados.
    Esta é a página que você acessará no seu navegador.
    """
    conn = get_db_connection()
    clientes = conn.execute("SELECT * FROM clientes ORDER BY last_seen DESC").fetchall()
    conn.close()

    # HTML com Tailwind CSS para um visual moderno e responsivo
    html_template = """
    <!doctype html>
    <html lang="pt-BR" class="bg-gray-900 text-white">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Painel de Monitoramento</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');
            body { font-family: 'Inter', sans-serif; }
        </style>
    </head>
    <body class="p-6">
        <div class="max-w-4xl mx-auto bg-gray-800 rounded-lg shadow-xl p-8">
            <h1 class="text-3xl font-bold mb-6 text-center text-yellow-500">
                🚀 Painel de Monitoramento de Clientes
            </h1>
            <div class="mb-4">
                <span class="text-gray-400">Total de clientes monitorados:</span>
                <span class="font-bold text-lg text-yellow-500">{{ total_clientes }}</span>
            </div>
            
            {% if clientes %}
            <div class="overflow-x-auto">
                <table class="min-w-full divide-y divide-gray-700">
                    <thead class="bg-gray-700">
                        <tr>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                                Chave de Licença
                            </th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                                HWID
                            </th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                                Última Atividade
                            </th>
                        </tr>
                    </thead>
                    <tbody class="bg-gray-800 divide-y divide-gray-700">
                        {% for cliente in clientes %}
                        <tr>
                            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-yellow-300">
                                {{ cliente['license_key'] }}
                            </td>
                            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-400">
                                <span title="{{ cliente['hwid'] }}">{{ cliente['hwid'][:15] }}...</span>
                            </td>
                            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-400">
                                {{ cliente['last_seen'] }}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% else %}
            <p class="text-center text-gray-500 py-10">Nenhum cliente registrado ainda.</p>
            {% endif %}
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template, clientes=clientes, total_clientes=len(clientes))

# Ponto de entrada para o servidor web
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 5000))
