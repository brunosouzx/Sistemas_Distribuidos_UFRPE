import database as db
# Importar função de publicação do módulo app
from app import publicar_pedido_preparando, publicar_pedido_pronto
from flasgger import Swagger
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='static')
CORS(app)
swagger = Swagger(app)


db.init_db()


@app.route('/fila', methods=['GET'])
def listar_fila():
    """
    Lista pedidos na fila de preparação.
    ---
    responses:
      200:
        description: Fila de pedidos
    """
    try:
        fila = db.listar_fila_preparo()

        recebidos = [p for p in fila if p['status'] == 'RECEBIDO']
        preparando = [p for p in fila if p['status'] == 'PREPARANDO']

        return jsonify({
            "total_fila": len(fila),
            "recebidos": len(recebidos),
            "preparando": len(preparando),
            "pedidos": fila
        }), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route('/pedidos/<status>', methods=['GET'])
def listar_por_status(status):
    """
    Lista pedidos por status.
    ---
    parameters:
      - name: status
        in: path
        type: string
        required: true
        enum: [RECEBIDO, PREPARANDO, PRONTO]
    responses:
      200:
        description: Lista de pedidos
    """
    try:
        status_upper = status.upper()
        if status_upper not in ['RECEBIDO', 'PREPARANDO', 'PRONTO']:
            return jsonify({"erro": "Status inválido"}), 400

        pedidos = db.listar_pedidos_por_status(status_upper)
        return jsonify({
            "status": status_upper,
            "total": len(pedidos),
            "pedidos": pedidos
        }), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route('/pedidos/<int:cozinha_id>', methods=['GET'])
def buscar_pedido(cozinha_id):
    """
    Busca um pedido específico.
    ---
    parameters:
      - name: cozinha_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Dados do pedido
      404:
        description: Pedido não encontrado
    """
    try:
        pedido = db.buscar_pedido(cozinha_id)
        if pedido:
            return jsonify(pedido), 200
        else:
            return jsonify({"erro": "Pedido não encontrado"}), 404
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route('/pedidos/<int:cozinha_id>/iniciar', methods=['PUT'])
def iniciar_preparo_endpoint(cozinha_id):
    """
    Inicia o preparo de um pedido.
    ---
    parameters:
      - name: cozinha_id
        in: path
        type: integer
        required: true
        description: ID do pedido na cozinha
    responses:
      200:
        description: Preparo iniciado
      404:
        description: Pedido não encontrado
      400:
        description: Pedido já está em preparo
    """
    try:
        pedido = db.buscar_pedido(cozinha_id)
        if not pedido:
            return jsonify({"erro": "Pedido não encontrado"}), 404

        if pedido['status'] != 'RECEBIDO':
            return jsonify(
                {"erro": f"Pedido já está com status: {pedido['status']}"}
            ), 400

        db.iniciar_preparo(cozinha_id)

        # Publicar mensagem no RabbitMQ
        publicado = publicar_pedido_preparando(
            pedido['pedido_id'],
            pedido['cliente'],
            pedido['item']
        )

        return jsonify({
            "mensagem": "Preparo iniciado",
            "pedido_id": pedido['pedido_id'],
            "item": pedido['item'],
            "publicado_rabbitmq": publicado
        }), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route('/pedidos/<int:cozinha_id>/finalizar', methods=['PUT'])
def finalizar_pedido_endpoint(cozinha_id):
    """
    Finaliza o pedido e CALCULA automaticamente o tempo de preparo.
    """
    try:
        # 1. Busca o pedido para ver a hora que começou
        pedido = db.buscar_pedido(cozinha_id)
        if not pedido:
            return jsonify({"erro": "Pedido não encontrado"}), 404

        if pedido['status'] != 'PREPARANDO':
            return jsonify({"erro": "Pedido precisa estar EM PREPARO para finalizar"}), 400

        # 2. Calcula o tempo decorrido (Agora - Inicio)
        import datetime
        
        # A data vem do banco como string, precisamos converter se necessário
        # O SQLite retorna strings no formato 'YYYY-MM-DD HH:MM:SS'
        # Vamos deixar o banco calcular ou fazer uma estimativa simples aqui se o banco falhar
        
        # Na verdade, a melhor prática é deixar o banco calcular na hora do UPDATE
        # Mas para simplificar, vamos passar o cálculo para a função do database.py
        # Vamos alterar a chamada do database para não exigir tempo manual
        
        # NOTA: Vamos alterar a função finalizar_pedido no database.py logo abaixo para calcular sozinha
        
        # Chama o banco (que vai calcular o tempo)
        dados_pedido = db.finalizar_pedido_automatico(cozinha_id)

        # Publica no RabbitMQ
        publicado = publicar_pedido_pronto(
            dados_pedido['pedido_id'],
            dados_pedido['cliente'],
            dados_pedido['item']
        )

        return jsonify({
            "mensagem": "Pedido finalizado com sucesso",
            "tempo_total": dados_pedido['tempo_preparacao'], # O banco devolve o tempo calculado
            "pedido_id": dados_pedido['pedido_id'],
            "publicado_rabbitmq": publicado
        }), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route('/estatisticas', methods=['GET'])
def estatisticas():
    """
    Retorna estatísticas da cozinha.
    ---
    responses:
      200:
        description: Estatísticas de operação
    """
    try:
        stats = db.estatisticas_cozinha()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """
    Verifica o status do serviço.
    ---
    responses:
      200:
        description: Serviço operacional
    """
    return jsonify({
        "status": "online",
        "servico": "cozinha_api"
    }), 200


@app.route('/')
def index():
    """Serve a página inicial do frontend da cozinha."""
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve arquivos estáticos (CSS, JS, etc)."""
    return send_from_directory(app.static_folder, filename)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
