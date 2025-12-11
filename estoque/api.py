import database as db
from flasgger import Swagger
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
swagger = Swagger(app)


db.init_db()


@app.route('/estoque', methods=['GET'])
def listar_estoque():
    """
    Lista todos os ingredientes do estoque.
    ---
    responses:
      200:
        description: Lista de ingredientes
    """
    try:
        estoque = db.listar_estoque()

        # Separar por status
        criticos = [i for i in estoque if i['status'] == 'CRITICO']
        baixos = [i for i in estoque if i['status'] == 'BAIXO']

        return jsonify({
            "total_ingredientes": len(estoque),
            "alertas": {
                "criticos": len(criticos),
                "baixos": len(baixos)
            },
            "estoque": estoque
        }), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route('/estoque/<ingrediente_nome>', methods=['GET'])
def consultar_ingrediente(ingrediente_nome):
    """
    Consulta um ingrediente específico.
    ---
    parameters:
      - name: ingrediente_nome
        in: path
        type: string
        required: true
    responses:
      200:
        description: Dados do ingrediente
      404:
        description: Ingrediente não encontrado
    """
    try:
        estoque = db.listar_estoque()
        ingrediente = next(
            (i for i in estoque if i['nome'] == ingrediente_nome), None)

        if ingrediente:
            return jsonify(ingrediente), 200
        else:
            return jsonify({"erro": "Ingrediente não encontrado"}), 404
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route('/estoque/<ingrediente_nome>/adicionar', methods=['POST'])
def adicionar_estoque(ingrediente_nome):
    """
    Adiciona quantidade a um ingrediente.
    ---
    parameters:
      - name: ingrediente_nome
        in: path
        type: string
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - quantidade
          properties:
            quantidade:
              type: integer
              example: 50
            motivo:
              type: string
              example: "Reposição semanal"
    responses:
      200:
        description: Estoque atualizado
      400:
        description: Dados inválidos
    """
    try:
        dados = request.json
        quantidade = dados.get('quantidade')
        motivo = dados.get('motivo', 'Reposição manual')

        if not quantidade or quantidade <= 0:
            return jsonify({"erro": "Quantidade deve ser maior que zero"}), 400

        resultado = db.adicionar_estoque(ingrediente_nome, quantidade, motivo)
        return jsonify({
            "status": "sucesso",
            "mensagem": f"Adicionado {quantidade} unidades"
            f" de {ingrediente_nome}",
            "resultado": resultado
        }), 200
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route('/estoque/historico', methods=['GET'])
def historico():
    """
    Retorna o histórico de movimentações.
    ---
    parameters:
      - name: ingrediente
        in: query
        type: string
        required: false
      - name: limit
        in: query
        type: integer
        default: 100
    responses:
      200:
        description: Histórico de movimentações
    """
    try:
        ingrediente = request.args.get('ingrediente')
        limit = request.args.get('limit', 100, type=int)

        movimentacoes = db.historico_movimentacoes(ingrediente, limit)
        return jsonify({
            "total": len(movimentacoes),
            "movimentacoes": movimentacoes
        }), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route('/estoque/verificar/<produto>', methods=['GET'])
def verificar_disponibilidade(produto):
    """
    Verifica se há ingredientes suficientes para um produto.
    ---
    parameters:
      - name: produto
        in: path
        type: string
        required: true
    responses:
      200:
        description: Disponibilidade do produto
    """
    try:
        disponivel, mensagem = db.verificar_disponibilidade(produto)
        receita = db.obter_receita(produto)

        return jsonify({
            "produto": produto,
            "disponivel": disponivel,
            "mensagem": mensagem,
            "receita": receita
        }), 200
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
        "servico": "estoque_api"
    }), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)
