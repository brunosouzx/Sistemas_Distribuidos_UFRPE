import json
import time

import pika

# Receitas simples (Hardcoded para o protótipo)
RECEITAS = {
    "X-Salada": {"pao": 1, "carne": 1, "queijo": 1},
    "X-Bacon":  {"pao": 1, "carne": 1, "queijo": 1, "bacon": 2}
}


def carregar_banco():
    try:
        with open('bd_provisorio.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def salvar_banco(dados):
    with open('bd_provisorio.json', 'w') as f:
        json.dump(dados, f, indent=4)


def callback(ch, method, properties, body):
    pedido = json.loads(body)
    item_pedido = pedido.get('item')

    print(f" [x] ESTOQUE: Processando {item_pedido}...", flush=True)

    estoque = carregar_banco()

    if item_pedido in RECEITAS:
        ingredientes_necessarios = RECEITAS[item_pedido]

        # Desconta os ingredientes
        for ingrediente, qtd in ingredientes_necessarios.items():
            if ingrediente in estoque:
                estoque[ingrediente] -= qtd
                print(
                    f" - Baixou {qtd} de {ingrediente}. "
                    f"Restam: {estoque[ingrediente]}")
            else:
                print(
                    f"     ! ALERTA: {ingrediente} não encontrado no sistema!")

        salvar_banco(estoque)
        print(" [v] Estoque atualizado!", flush=True)
    else:
        print(
            f" [!] Item {item_pedido} não tem receita cadastrada.", flush=True)


def iniciar_consumidor():
    print("Conectando ao RabbitMQ...", flush=True)
    while True:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters('rabbitmq'))
            break
        except (pika.exceptions.AMQPConnectionError, OSError):
            time.sleep(2)

    channel = connection.channel()
    channel.exchange_declare(
        exchange='pedidos_exchange', exchange_type='fanout'
    )

    result = channel.queue_declare(queue='', exclusive=True)
    queue_name = result.method.queue
    channel.queue_bind(exchange='pedidos_exchange', queue=queue_name)

    print(' [*] Estoque pronto e ouvindo...', flush=True)
    channel.basic_consume(
        queue=queue_name, on_message_callback=callback, auto_ack=True
    )
    channel.start_consuming()


if __name__ == '__main__':
    iniciar_consumidor()
