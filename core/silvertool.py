import json
import os
from flask import Flask, render_template, request, send_file, redirect
import pyodbc
import subprocess
from pathlib import Path



app = Flask(__name__)

# Configurações
BASE_DIR = Path(__file__).resolve().parent
JSON_FILE = BASE_DIR /  "raw_files" / "raw.json"
OUTPUT_FILE = BASE_DIR / "filtered_files" / "filtered.json"
EDIT_FILE = BASE_DIR / "edit_files" / "edit.json"
DB_CONFIG = {
    'server': '',
    'database': '',
    'driver': '{ODBC Driver 17 for SQL Server}'
}



def get_schema_json():
    conn_str = f'DRIVER={DB_CONFIG["driver"]};SERVER={DB_CONFIG["server"]};DATABASE={DB_CONFIG["database"]};Authentication=ActiveDirectoryInteractive'
    
    schema_dict = {}
    try:
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            query = """
            SELECT TABLE_NAME, COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'dbo'
            ORDER BY TABLE_NAME, ORDINAL_POSITION
            """
            cursor.execute(query)
            
            for table, column in cursor.fetchall():
                schema_dict.setdefault(table, {"columns": []})["columns"].append(column)
                
        return schema_dict
    except Exception as e:
        print(f"Erro na conexão: {str(e)}")
        return None

def load_json():
    try:
        with open(JSON_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as e:
        print(f"Erro ao carregar JSON: {str(e)}")
        return {}

@app.route('/')
def index():
    data = load_json()
    return render_template('index.html', data=data)

@app.route('/update', methods=['POST'])
def update_db():
    data = request.json
    mode = data.get('mode', 'file')
    
    new_data = {}
    
    if mode == 'database':
        if data.get('dbLink'):
            DB_CONFIG['server'] = data['dbLink']
        if data.get('dbName'):
            DB_CONFIG['database'] = data['dbName']
        
        new_data = get_schema_json()
        
    elif mode == 'json' and data.get('jsonData'):
        try:
            new_data = json.loads(data['jsonData'])
        except json.JSONDecodeError:
            return "JSON inválido", 400
            
    elif mode == 'file':
        try:
            with open(JSON_FILE, "r", encoding="utf-8") as file:
                new_data = json.load(file)
        except Exception as e:
            print(f"Erro ao ler arquivo: {str(e)}")
            return "Erro interno", 500

    if new_data:
        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(new_data, f, indent=4)
        return redirect('/')
    
    return "Erro ao atualizar dados", 500


@app.route('/load_edit_file')
def load_edit_file():
    try:
        with open(EDIT_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
        return json.dumps(data), 200, {'Content-Type': 'application/json'}
    except Exception as e:
        return f"Erro: {e}", 500


@app.route('/save_filtered', methods=['POST'])
def save_filtered():
    selected = request.form.getlist('columns')
    filtered_data = processar_selecoes(selected) 
    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(filtered_data, file, indent=4)
    return send_file(OUTPUT_FILE, as_attachment=True, download_name="filtered_output.json")

@app.route('/save_edit', methods=['POST'])
def save_edit():
    selected = request.form.getlist('columns')
    filtered_data = processar_selecoes(selected)
    with open(EDIT_FILE, "w", encoding="utf-8") as file:
        json.dump(filtered_data, file, indent=4)
    return send_file(EDIT_FILE, as_attachment=True, download_name="edit.json")

@app.route('/save_raw')
def save_raw():
    return send_file(JSON_FILE, as_attachment=True)

def processar_selecoes(selected_columns): 
    data = load_json()
    filtered_data = {}
    for table, info in data.items():
        filtered_columns = [
            col for col in info['columns']
            if f"{table}.{col}" in selected_columns
        ]
        if filtered_columns:
            filtered_data[table] = {"columns": filtered_columns}
    return filtered_data

# Modifique a rota /save para copiar para área de transferência
@app.route('/get_filtered_json', methods=['POST'])
def get_filtered_json():
    selected = request.form.getlist('columns')
    filtered_data = {}
    
    data = load_json()
    for table, info in data.items():
        filtered_columns = [col for col in info['columns'] if f"{table}.{col}" in selected]
        if filtered_columns:
            filtered_data[table] = {"columns": filtered_columns}
    
    return filtered_data

if __name__ == '__main__':
    subprocess.run(["cmd", "/c", "start", "http://127.0.0.1:5000"], shell=True)
    app.run(debug=False)