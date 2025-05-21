# Neste projeto, usa-se o bando de dados SQLite3 e o framework Flask      
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, g, flash
from datetime import datetime
import math # Para paginação

# Configuração do Aplicativo
app = Flask(__name__)
app.secret_key = '1*/-wRy8!0pK~q$' # Senha super secreta!
DATABASE = 'controle_chaves.db'    # Nome do banco de dados
ITEMS_PER_PAGE = 10 

# Funções básicas do Banco de Dados
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()
    print("Banco de dados inicializado com sucesso.")

@app.cli.command('init-db')
def init_db_command():
    init_db()

# Outras Funções 
def format_datetime_for_display(dt_str):
    if not dt_str:
        return None
    try:
        dt_obj = datetime.fromisoformat(dt_str)
        return dt_obj.strftime('%d/%m/%Y %H:%M')
    except (ValueError, TypeError):
        return dt_str 

def format_datetime_for_input(dt_str):
    if not dt_str:
        return None
    try:
        
        dt_obj = datetime.fromisoformat(dt_str)
        return dt_obj.strftime('%Y-%m-%dT%H:%M')
    except (ValueError, TypeError):
         
        try:
            datetime.strptime(dt_str, '%Y-%m-%dT%H:%M')
            return dt_str
        except ValueError:
            return None 


@app.route('/', methods=['GET'])
def index():
    db = get_db()
    page = request.args.get('page', 1, type=int)
    busca_termo = request.args.get('busca', '').strip()
    filtro_pendentes = request.args.get('filtro_pendentes', 'false').lower() == 'true'

    query_conditions = []
    query_params = []

    if busca_termo:
        like_term = f"%{busca_termo}%"
        query_conditions.append(
            "(nome_responsavel LIKE ? OR nome_chave LIKE ? OR empresa LIKE ? OR codigo_empresa LIKE ?)"
        )
        query_params.extend([like_term] * 4)

    if filtro_pendentes:
        query_conditions.append("data_hora_devolucao IS NULL")

    where_clause = ""
    if query_conditions:
        where_clause = "WHERE " + " AND ".join(query_conditions)

    # Calcular o total de itens para paginação
    count_cursor = db.execute(f"SELECT COUNT(id) FROM registros_chaves {where_clause}", query_params)
    total_items = count_cursor.fetchone()[0]
    total_pages = math.ceil(total_items / ITEMS_PER_PAGE)

    offset = (page - 1) * ITEMS_PER_PAGE

    # Busca com paginação
    sql_query = (
        f"SELECT id, nome_responsavel, telefone, empresa, codigo_empresa, nome_chave, "
        f"data_hora_retirada, data_hora_devolucao, observacoes "
        f"FROM registros_chaves {where_clause} "
        f"ORDER BY data_hora_retirada DESC LIMIT ? OFFSET ?"
    )
    final_query_params = query_params + [ITEMS_PER_PAGE, offset]
    
    cursor = db.execute(sql_query, final_query_params)
    registros_raw = cursor.fetchall()

    registros_formatados = []
    for reg in registros_raw:
        reg_dict = dict(reg) # Converte sqlite3.Row para dict para poder adicionar chaves
        reg_dict['data_hora_retirada_f'] = format_datetime_for_display(reg['data_hora_retirada'])
        reg_dict['data_hora_devolucao_f'] = format_datetime_for_display(reg['data_hora_devolucao'])
        registros_formatados.append(reg_dict)
    
    return render_template('index.html',
                           registros=registros_formatados,
                           pagina_atual=page,
                           total_paginas=total_pages,
                           busca_termo=busca_termo,
                           filtro_pendentes=filtro_pendentes)

@app.route('/registrar', methods=['POST'])
def registrar_chave():
    if request.method == 'POST':
        nome_chave = request.form['nome_chave']
        nome_responsavel = request.form['nome_responsavel']
        telefone = request.form.get('telefone')
        empresa = request.form.get('empresa')
        codigo_empresa = request.form.get('codigo_empresa')
        data_hora_retirada_str = request.form['data_hora_retirada']
        observacoes = request.form.get('observacoes')

        if not nome_chave or not nome_responsavel or not data_hora_retirada_str:
            flash('Campos "Nome da Chave", "Nome do Responsável" e "Data/Hora Retirada" são obrigatórios!', 'error')
            return redirect(url_for('index'))
        
        try:
            # Converte a string do formulário para o formato do padrão ISO que o SQLite entende melhor para DATETIME
            data_hora_retirada_dt = datetime.strptime(data_hora_retirada_str, '%Y-%m-%dT%H:%M')
            data_hora_retirada_iso = data_hora_retirada_dt.isoformat()
        except ValueError:
            flash('Formato de Data/Hora da Retirada inválido.', 'error')
            return redirect(url_for('index'))

        try:
            db = get_db()
            db.execute(
                'INSERT INTO registros_chaves (nome_chave, nome_responsavel, telefone, empresa, codigo_empresa, data_hora_retirada, observacoes) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (nome_chave, nome_responsavel, telefone, empresa, codigo_empresa, data_hora_retirada_iso, observacoes)
            )
            db.commit()
            flash('Retirada de chave registrada com sucesso!', 'success')
        except sqlite3.Error as e:
            flash(f'Erro ao salvar o registro: {e}', 'error')
        return redirect(url_for('index'))

@app.route('/devolver/<int:id>', methods=['POST'])
def devolver_chave(id):
    try:
        db = get_db()
        # Pega a data e hora atuais e formata para o padrão ISO
        data_hora_devolucao_iso = datetime.now().isoformat()
        db.execute('UPDATE registros_chaves SET data_hora_devolucao = ? WHERE id = ?', (data_hora_devolucao_iso, id))
        db.commit()
        flash(f'Chave do registro #{id} marcada como devolvida!', 'success')
    except sqlite3.Error as e:
        flash(f'Erro ao marcar chave como devolvida: {e}', 'error')
    return redirect(url_for('index', page=request.args.get('page', 1, type=int), busca=request.args.get('busca', ''), filtro_pendentes=request.args.get('filtro_pendentes', '')))


@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar_chave(id):
    db = get_db()
    
    if request.method == 'POST':
        nome_chave = request.form['nome_chave']
        nome_responsavel = request.form['nome_responsavel']
        telefone = request.form.get('telefone')
        empresa = request.form.get('empresa')
        codigo_empresa = request.form.get('codigo_empresa')
        data_hora_retirada_str = request.form['data_hora_retirada']
        data_hora_devolucao_str = request.form.get('data_hora_devolucao')
        observacoes = request.form.get('observacoes')

        if not nome_chave or not nome_responsavel or not data_hora_retirada_str:
            flash('Campos "Nome da Chave", "Nome do Responsável" e "Data/Hora Retirada" são obrigatórios!', 'error')
            # Em caso de erro, recarregas-se os dados do registro para o template de edição
            registro_raw = db.execute('SELECT * FROM registros_chaves WHERE id = ?', (id,)).fetchone()
            if not registro_raw:
                flash('Registro não encontrado!', 'error')
                return redirect(url_for('index'))
            
            registro = dict(registro_raw)
            registro['data_hora_retirada_formato_input'] = format_datetime_for_input(registro['data_hora_retirada'])
            registro['data_hora_devolucao_formato_input'] = format_datetime_for_input(registro['data_hora_devolucao'])
            return render_template('editar.html', registro=registro)
        
        try:
            data_hora_retirada_iso = datetime.strptime(data_hora_retirada_str, '%Y-%m-%dT%H:%M').isoformat()
            data_hora_devolucao_iso = None
            if data_hora_devolucao_str: # Converte se estiver preenchido
                data_hora_devolucao_iso = datetime.strptime(data_hora_devolucao_str, '%Y-%m-%dT%H:%M').isoformat()
        except ValueError:
            flash('Formato de Data/Hora inválido.', 'error')
            # Recarregar dados em caso de erro de formato
            registro_raw = db.execute('SELECT * FROM registros_chaves WHERE id = ?', (id,)).fetchone()
            if not registro_raw:
                flash('Registro não encontrado!', 'error')
                return redirect(url_for('index'))
            
            registro = dict(registro_raw)
            registro['data_hora_retirada_formato_input'] = format_datetime_for_input(registro['data_hora_retirada'])
            registro['data_hora_devolucao_formato_input'] = format_datetime_for_input(registro['data_hora_devolucao'])
            return render_template('editar.html', registro=registro)

        try:
            db.execute(
                'UPDATE registros_chaves SET nome_chave=?, nome_responsavel=?, telefone=?, empresa=?, codigo_empresa=?, data_hora_retirada=?, data_hora_devolucao=?, observacoes=? WHERE id=?',
                (nome_chave, nome_responsavel, telefone, empresa, codigo_empresa, data_hora_retirada_iso, data_hora_devolucao_iso, observacoes, id)
            )
            db.commit()
            flash('Registro atualizado com sucesso!', 'success')
            return redirect(url_for('index'))
        except sqlite3.Error as e:
            flash(f'Erro ao atualizar o registro: {e}', 'error')
            # Caso ocorra um erro no banco de dados, recarrega-se os dados
            registro_raw = db.execute('SELECT * FROM registros_chaves WHERE id = ?', (id,)).fetchone()
            if not registro_raw: # Improvável, mas seguro
                flash('Registro não encontrado!', 'error')
                return redirect(url_for('index'))
            
            registro = dict(registro_raw)
            registro['data_hora_retirada_formato_input'] = format_datetime_for_input(registro['data_hora_retirada'])
            registro['data_hora_devolucao_formato_input'] = format_datetime_for_input(registro['data_hora_devolucao'])
            return render_template('editar.html', registro=registro)

    else: # Método GET para carregar o formulário de edição
        registro_raw = db.execute('SELECT * FROM registros_chaves WHERE id = ?', (id,)).fetchone()
        if registro_raw is None:
            flash('Registro não encontrado!', 'error')
            return redirect(url_for('index'))
        
        # Converte para dict para adicionar os campos formatados para o input
        registro = dict(registro_raw)
        registro['data_hora_retirada_formato_input'] = format_datetime_for_input(registro['data_hora_retirada'])
        registro['data_hora_devolucao_formato_input'] = format_datetime_for_input(registro['data_hora_devolucao'])
        
        return render_template('editar.html', registro=registro)


@app.route('/excluir/<int:id>', methods=['POST'])
def excluir_chave(id):
    try:
        db = get_db()
        db.execute('DELETE FROM registros_chaves WHERE id = ?', (id,))
        db.commit()
        flash(f'Registro #{id} excluído com sucesso!', 'success')
    except sqlite3.Error as e:
        flash(f'Erro ao excluir o registro: {e}', 'error')
    return redirect(url_for('index', page=request.args.get('page', 1, type=int), busca=request.args.get('busca', ''), filtro_pendentes=request.args.get('filtro_pendentes', '')))


#Executando o Aplicativo
if __name__ == '__main__':
    # Verifica se o Banco de Dados já existe senão, ele é criado na primeira execução.
    import os
    if not os.path.exists(DATABASE):
        print(f"Banco de dados {DATABASE} não encontrado. Criando e inicializando...")
        init_db()
    app.run() 

    
