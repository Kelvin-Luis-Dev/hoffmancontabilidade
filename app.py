import os
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, send_from_directory, abort, \
    Response, current_app
from flask_mail import Mail, Message  # Importando Flask-Mail
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Inicializa o Mail globalmente
mail = Mail()


def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # --- CONFIGURAÇÃO DO BANCO E CHAVES ---
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        DATABASE=os.path.join(app.instance_path, 'contatos.db'),
    )

    # --- CONFIGURAÇÃO DE EMAIL (GMAIL Resend) ---
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
            {'id': 'contabilidade-fiscal', 'title': 'Contabilidade/Fiscal',
             'excerpt': 'Apoio completo para suas obrigações contábeis e fiscais.', 'image': 'obrigacoesfiscais.png'},
            {'id': 'ir-pf-pj', 'title': 'Demandas Financeiras e Administrativas',
             'excerpt': 'Atendemos as principais demandas financeiras e administrativas do seu negócio.', 'image': 'demandasadm.png'},
            {'id': 'planejamento-tributario', 'title': 'Planejamento Tributário',
             'excerpt': 'Estratégias para otimizar impostos e aumentar resultados.',
             'image': 'planejamentotributario.png'},
            {'id': 'gestao-folha', 'title': 'Imposto de Renda',
             'excerpt': 'Suporte completo na declaração do Imposto de Renda.', 'image': 'impostoderenda.png'},
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
            {
                'id': 'contabilidade-fiscal',
                'title': 'Contabilidade/Fiscal',
                'body': 'Garantimos que sua empresa esteja 100% em dia com o fisco. Atuamos com fechamento contábil, apuração dos impostos e cumprimento das obrigações fiscais.',
                'image': 'obrigacoesfiscais.png'
            },
            {
                'id': 'ir-pf-pj',
                'title': 'Demandas Administrativas',
                'body': 'Conte com a gente para lidar com as burocracias! Fazemos emissão de certidões de débito, parcelamento de débitos, alterações contratuais, emissão de alvarás e regularização completa junto a órgãos públicos.',
                'image': 'demandasadm.png'
            },
            {
                'id': 'planejamento-tributario',
                'title': 'Planejamento Tributário',
                'body': 'Pagar impostos é obrigatório, pagar mais do que deve é opcional. Analisamos profundamente seu modelo de negócio para encontrar o regime tributário mais adequado (Simples Nacional, Lucro Presumido ou Real), aplicando estratégias inteligentes para reduzir sua carga tributária.',
                'image': 'planejamentotributario.png'
            },
            {
                'id': 'escrituracao',
                'title': 'Estratégias de Redução de Custos',
                'body': 'Transformamos números em inteligência de negócio. Através da assessoria financeira, desenvolvemos relatórios gerenciais e análises de fluxo de caixa que visam identificar gargalos, reduzir custos e aumentar a margem de lucro da sua empresa.',
                'image': 'estrategiascustos.png'
            },
            {
                'id': 'gestao-folha',
                'title': 'Imposto de Renda',
                'body': 'Assessoria completa em Imposto de Renda, garantindo apuração correta, conformidade legal e segurança nas informações declaradas. Atuamos na análise de dados, elaboração e envio das declarações, reduzindo riscos e prevenindo inconsistências junto ao Fisco.',
                'image': 'impostoderenda.png'
            },
        ]
        anchor = request.args.get('anchor')
        return render_template('servicos.html', services=services, anchor=anchor)

    @app.route('/contato', methods=['GET'])
    def contato_get():
        return render_template('contato.html')

    @app.route('/api/contato', methods=['POST'])
    def contato_post():
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()

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
            ''', (data.get('nome'), data.get('email'), data.get('telefone'), data.get('interesse'),
                  data.get('mensagem')))
            conn.commit()

            # 2. Tentar enviar e-mail
            try:
                print(f"--- TENTANDO ENVIAR EMAIL... ---")
                enviar_email_notificacao(data)
                print(f"--- EMAIL ENVIADO COM SUCESSO (Verifique o servidor/terminal) ---")
            except Exception as e:
                print(f"--- ERRO NO ENVIO DE EMAIL: {e} ---")
                app.logger.warning(f'Falha ao enviar e-mail: {e}')
                # Não retornamos erro 500 aqui para não assustar o usuário, já que salvou no banco.

            return jsonify(
                {'status': 'ok', 'message': 'Mensagem enviada com sucesso! Em breve entraremos em contato.'}), 200

        except Exception as db_err:
            app.logger.error(f'Erro no banco de dados: {db_err}')
            return jsonify({'status': 'error', 'message': 'Erro interno ao salvar mensagem.'}), 500

    @app.route('/sitemap.xml')
    def sitemap():
        pages = [
            url_for('home', _external=True),
            url_for('sobre', _external=True),
            url_for('servicos', _external=True),
            url_for('contato_get', _external=True),
        ]
        xml = render_template('sitemap.xml', pages=pages)
        return Response(xml, mimetype='application/xml')

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
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute('''
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
        conn.commit()
        conn.close()

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def enviar_email_notificacao(data):
    # Pega as configurações direto do Render
    smtp_server = "smtp.resend.com"
    smtp_port = 587
    sender_email = os.environ.get('MAIL_DEFAULT_SENDER')
    receiver_email = "hoffmannconsultoriacontabil@gmail.com"
    password = os.environ.get('MAIL_PASSWORD')

    # Monta a mensagem manualmente para evitar erros de biblioteca
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = f"Novo Contato Site: {data.get('nome')}"

    corpo = f"""
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
    message.attach(MIMEText(corpo, "plain"))

    # Envia de forma direta (sem passar pelo Flask-Mail)
    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()  # Ativa a segurança obrigatória do Resend
    server.login("resend", password)
    server.sendmail(sender_email, receiver_email, message.as_string())
    server.quit()

# --- EXECUÇÃO ---
# Necessário para rodar com 'python app.py'
application = create_app()
app = application

if __name__ == '__main__':
    app.run(debug=True)
