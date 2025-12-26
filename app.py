import os
import sqlite3
import threading # Novo: para enviar e-mail sem travar o site
from flask import Flask, render_template, request, jsonify, Response, current_app, url_for
from flask_mail import Mail, Message

# Inicializa o Mail globalmente
mail = Mail()

def send_async_email(app, msg):
    """Função auxiliar para enviar o e-mail em segundo plano"""
    with app.app_context():
        try:
            mail.send(msg)
            print("--- EMAIL ENVIADO COM SUCESSO ---")
        except Exception as e:
            print(f"--- ERRO NO ENVIO DE EMAIL: {e} ---")

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # --- CONFIGURAÇÃO DO BANCO E CHAVES ---
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        DATABASE=os.path.join(app.instance_path, 'contatos.db'),
    )

    # --- CONFIGURAÇÃO DE EMAIL (Resend via Flask-Mail) ---
    app.config['MAIL_SERVER'] = 'smtp.resend.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_USERNAME'] = 'resend'
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')

    # Inicializa o Mail com a app configurada
    mail.init_app(app)

    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    init_db(app)

    # --- ROTAS ---

    @app.route('/')
    def home():
        services = [
            {'id': 'contabilidade-fiscal', 'title': 'Contabilidade/Fiscal', 'excerpt': 'Apoio completo para suas obrigações contábeis e fiscais.', 'image': 'obrigacoesfiscais.png'},
            {'id': 'ir-pf-pj', 'title': 'Demandas Financeiras e Administrativas', 'excerpt': 'Atendemos as principais demandas financeiras e administrativas do seu negócio.', 'image': 'demandasadm.png'},
            {'id': 'planejamento-tributario', 'title': 'Planejamento Tributário', 'excerpt': 'Estratégias para otimizar impostos e aumentar resultados.', 'image': 'planejamentotributario.png'},
            {'id': 'gestao-folha', 'title': 'Imposto de Renda', 'excerpt': 'Suporte completo na declaração do Imposto de Renda.', 'image': 'impostoderenda.png'},
        ]
        return render_template('home.html', services=services)

    @app.route('/sobre')
    def sobre():
        team = [
            {'name': 'Pablo Hoffmann', 'role': 'Sócio Administrador', 'photo': '/static/img/team-placeholder.png'},
            {'name': 'Natália Debastiani', 'role': 'Sócia', 'photo': '/static/img/team-placeholder.png'},
        ]
        return render_template('sobre.html', team=team)

    @app.route('/servicos')
    def servicos():
        services = [
            {'id': 'contabilidade-fiscal', 'title': 'Contabilidade/Fiscal', 'body': 'Garantimos que sua empresa esteja 100% em dia com o fisco.', 'image': 'obrigacoesfiscais.png'},
            {'id': 'ir-pf-pj', 'title': 'Demandas Administrativas', 'body': 'Conte com a gente para lidar com as burocracias!', 'image': 'demandasadm.png'},
            {'id': 'planejamento-tributario', 'title': 'Planejamento Tributário', 'body': 'Analisamos profundamente seu modelo de negócio.', 'image': 'planejamentotributario.png'},
            {'id': 'escrituracao', 'title': 'Estratégias de Redução de Custos', 'body': 'Transformamos números em inteligência de negócio.', 'image': 'estrategiascustos.png'},
            {'id': 'gestao-folha', 'title': 'Imposto de Renda', 'body': 'Assessoria completa em Imposto de Renda.', 'image': 'impostoderenda.png'},
        ]
        anchor = request.args.get('anchor')
        return render_template('servicos.html', services=services, anchor=anchor)

    @app.route('/contato', methods=['GET'])
    def contato_get():
        return render_template('contato.html')

    @app.route('/api/contato', methods=['POST'])
    def contato_post():
        data = request.get_json() if request.is_json else request.form.to_dict()

        required_fields = ['nome', 'email', 'mensagem']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'status': 'error', 'message': f'O campo {field} é obrigatório.'}), 400

        try:
            # 1. Salvar no Banco de Dados
            conn = get_db()
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO contatos (nome, email, telefone, interesse, mensagem) 
                VALUES (?, ?, ?, ?, ?)
            ''', (data.get('nome'), data.get('email'), data.get('telefone'), data.get('interesse'), data.get('mensagem')))
            conn.commit()

            # 2. Enviar e-mail usando Threading (não trava o botão)
            enviar_email_notificacao(data)

            return jsonify({'status': 'ok', 'message': 'Mensagem enviada com sucesso!'}), 200

        except Exception as db_err:
            app.logger.error(f'Erro: {db_err}')
            return jsonify({'status': 'error', 'message': 'Erro interno.'}), 500

    @app.route('/sitemap.xml')
    def sitemap():
        pages = [url_for('home', _external=True), url_for('sobre', _external=True), url_for('servicos', _external=True), url_for('contato_get', _external=True)]
        return Response(render_template('sitemap.xml', pages=pages), mimetype='application/xml')

    @app.route('/robots.txt')
    def robots():
        return "User-agent: *\nDisallow:"

    return app

# --- HELPERS ---

def get_db():
    db_path = current_app.config['DATABASE']
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(app):
    db_path = app.config['DATABASE']
    if not os.path.exists(db_path):
        with sqlite3.connect(db_path) as conn:
            conn.execute('''
                CREATE TABLE contatos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    email TEXT NOT NULL,
                    telefone TEXT,
                    interesse TEXT,
                    mensagem TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')

def enviar_email_notificacao(data):
    """Prepara o e-mail e dispara a thread assíncrona"""
    msg = Message(
        subject=f"Novo Contato Site: {data.get('nome')}",
        recipients=["hoffmannconsultoriacontabil@gmail.com"],
        body=f"""
        Olá! Um novo contato foi recebido pelo site.
        ------------------------------------------
        Nome: {data.get('nome')}
        E-mail: {data.get('email')}
        Telefone: {data.get('telefone')}
        Interesse: {data.get('interesse')}

        Mensagem:
        {data.get('mensagem')}
        ------------------------------------------
        """
    )
    # Dispara o envio em uma nova thread para não bloquear o Gunicorn
    thread = threading.Thread(target=send_async_email, args=(current_app._get_current_object(), msg))
    thread.start()

# --- EXECUÇÃO ---
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
