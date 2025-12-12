import database as db
from flasgger import Swagger
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='static')
CORS(app)
swagger = Swagger(app)

db.init_db()

@app.route('/fila', methods=['GET'])
def listar_fila():
    """Lista pedidos na fila de preparação."""
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
    """Lista pedidos por status."""
    try:
        status_upper = status.upper()
        # IMPORTANTE: 'CANCELADO' deve estar nesta lista para o filtro funcionar
        if status_upper not in ['RECEBIDO', 'PREPARANDO', 'PRONTO', 'CANCELADO']:
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
    """Busca um pedido específico."""
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
    """Inicia o preparo de um pedido."""
    try:
        # Importação dentro da função para evitar erro circular
        from app import publicar_pedido_preparando
        
        pedido = db.buscar_pedido(cozinha_id)
        if not pedido:
            return jsonify({"erro": "Pedido não encontrado"}), 404

        if pedido['status'] != 'RECEBIDO':
            return jsonify({"erro": f"Pedido já está com status: {pedido['status']}"}), 400

        db.iniciar_preparo(cozinha_id)

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
    """Finaliza o pedido e calcula tempo."""
    try:
        # Importação dentro da função para evitar erro circular
        from app import publicar_pedido_pronto
        
        pedido = db.buscar_pedido(cozinha_id)
        if not pedido:
            return jsonify({"erro": "Pedido não encontrado"}), 404

        if pedido['status'] != 'PREPARANDO':
            return jsonify({"erro": "Pedido precisa estar EM PREPARO para finalizar"}), 400

        dados_pedido = db.finalizar_pedido_automatico(cozinha_id)

        publicado = publicar_pedido_pronto(
            dados_pedido['pedido_id'],
            dados_pedido['cliente'],
            dados_pedido['item']
        )

        return jsonify({
            "mensagem": "Pedido finalizado com sucesso",
            "tempo_total": dados_pedido['tempo_preparacao'],
            "pedido_id": dados_pedido['pedido_id'],
            "publicado_rabbitmq": publicado
        }), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

# --- ROTA QUE ESTAVA DANDO 404 ---
@app.route('/pedidos/<int:cozinha_id>/cancelar', methods=['PUT'])
def cancelar_pedido_endpoint(cozinha_id):
    """Cancela um pedido e notifica via RabbitMQ."""
    try:
        # Importação dentro da função para evitar erro circular
        from app import publicar_status_pedido

        dados = request.json
        motivo = dados.get('motivo', 'Cancelado pela cozinha')

        pedido = db.buscar_pedido(cozinha_id)
        if not pedido:
            return jsonify({"erro": "Pedido não encontrado"}), 404

        # Atualiza no banco local
        db.cancelar_pedido(cozinha_id)

        # Publica no RabbitMQ para o Caixa saber (status CANCELADO)
        publicado = publicar_status_pedido(
            pedido['pedido_id'],
            pedido['cliente'],
            pedido['item'],
            'CANCELADO'
        )

        return jsonify({
            "mensagem": "Pedido cancelado",
            "pedido_id": pedido['pedido_id'],
            "motivo": motivo,
            "publicado_rabbitmq": publicado
        }), 200
    except Exception as e:
        print(f"Erro ao cancelar: {e}")
        return jsonify({"erro": str(e)}), 500

@app.route('/estatisticas', methods=['GET'])
def estatisticas():
    """Retorna estatísticas da cozinha."""
    try:
        stats = db.estatisticas_cozinha()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "online", "servico": "cozinha_api"}), 200

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)