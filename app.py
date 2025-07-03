from flask import Flask, request, redirect, url_for, session
from datetime import date
import mysql.connector
from flask import render_template, flash

app = Flask(__name__)
app.secret_key = 'chave-secreta-simples'

# Configuração do banco MySQL
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Viana77@bank',
    'database': 'restaurante_universitario'
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

from flask import render_template, flash

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usuarios WHERE username = %s AND senha = %s", (username, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            session['user'] = user['username']
            session['tipo'] = user['tipo']
            if user['tipo'] == 'admin':
                return redirect(url_for('admin'))
            else:
                return redirect(url_for('solicitacao'))
        else:
            flash("Usuário ou senha inválidos.")

    return render_template("login.html")

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if session.get('tipo') != 'admin':
        return redirect(url_for('login'))

    mensagem_refeicao = ""
    mensagem_usuario = ""
    hoje = date.today()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Cadastro/edição da refeição
    if request.method == 'POST' and 'data' in request.form:
        data_refeicao = request.form['data']
        prato = request.form['prato']
        try:
            cursor.execute("""
                INSERT INTO refeicoes (data, prato)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE prato = %s
            """, (data_refeicao, prato, prato))
            conn.commit()
            mensagem_refeicao = "Refeição cadastrada/atualizada com sucesso!"
        except Exception as e:
            conn.rollback()
            mensagem_refeicao = f"Erro ao cadastrar refeição: {e}"

    # Cadastro de usuário
    if request.method == 'POST' and 'username' in request.form:
        username = request.form['username']
        senha = request.form['senha']
        tipo = request.form['tipo'].strip().lower()
        try:
            cursor.execute("""
                INSERT INTO usuarios (username, senha, tipo)
                VALUES (%s, %s, %s)
            """, (username, senha, tipo))
            conn.commit()
            mensagem_usuario = "Usuário cadastrado com sucesso!"
        except mysql.connector.IntegrityError:
            mensagem_usuario = "Nome de usuário já existe."
        except Exception as e:
            conn.rollback()
            mensagem_usuario = f"Erro ao cadastrar usuário: {e}"

    # Buscar refeição do dia
    cursor.execute("SELECT * FROM refeicoes WHERE data = %s", (hoje,))
    refeicao = cursor.fetchone()
    prato_do_dia = refeicao['prato'] if refeicao else "Nenhum"

    # Buscar confirmações
    cursor.execute("SELECT usuario, confirmacao FROM confirmacoes WHERE data = %s", (hoje,))
    confirmacoes = cursor.fetchall()
    total_sim = sum(1 for c in confirmacoes if c['confirmacao'] == 'Sim')

    # Listar usuários
    cursor.execute("SELECT username, tipo FROM usuarios")
    usuarios = cursor.fetchall()

    cursor.close()
    conn.close()

    lista_confirmacoes = ''.join(f"<li>{c['usuario']} - {c['confirmacao']}</li>" for c in confirmacoes)
    lista_usuarios = ''.join(f"<li>{u['username']} ({u['tipo']})</li>" for u in usuarios)

    return render_template(
        'admin.html',
        hoje=hoje,
        prato_do_dia=prato_do_dia,
        total_sim=total_sim,
        confirmacoes=confirmacoes,
        usuarios=usuarios,
        mensagem_refeicao=mensagem_refeicao,
        mensagem_usuario=mensagem_usuario
)


@app.route('/solicitacao', methods=['GET', 'POST'])
def solicitacao():
    if 'user' not in session or session.get('tipo') == 'admin':
        return redirect(url_for('login'))

    hoje = date.today()
    usuario = session['user']
    mensagem = ""

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM refeicoes WHERE data = %s", (hoje,))
    refeicao = cursor.fetchone()

    if request.method == 'POST':
        confirmacao = request.form.get('confirmacao')
        try:
            cursor.execute("""
                INSERT INTO confirmacoes (usuario, data, confirmacao)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE confirmacao = %s
            """, (usuario, hoje, confirmacao, confirmacao))
            conn.commit()
            mensagem = f"Confirmação '{confirmacao}' registrada com sucesso."
        except Exception as e:
            conn.rollback()
            mensagem = f"Erro ao registrar: {e}"

    cursor.close()
    conn.close()

    prato = refeicao['prato'] if refeicao else "Nenhuma refeição cadastrada para hoje."

    return render_template('solicitacao.html', hoje=hoje, prato=prato, mensagem=mensagem)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
