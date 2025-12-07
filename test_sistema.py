#!/usr/bin/env python3
"""
Script de teste para o Sistema de Hamburgueria Distribuído.
Testa os principais endpoints e funcionalidades.
"""

import time

import requests

# URLs dos serviços
CAIXA_URL = "http://localhost:5000"
COZINHA_API_URL = "http://localhost:5001"
ESTOQUE_API_URL = "http://localhost:5002"


def print_section(title):
    """Imprime um cabeçalho de seção."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_health_checks():
    """Testa se todos os serviços estão online."""
    print_section("1. VERIFICANDO SAÚDE DOS SERVIÇOS")

    services = [
        ("Caixa", f"{CAIXA_URL}/health"),
        ("Cozinha API", f"{COZINHA_API_URL}/health"),
        ("Estoque API", f"{ESTOQUE_API_URL}/health"),
    ]

    for name, url in services:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✓ {name}: Online")
            else:
                print(f"✗ {name}: Erro (status {response.status_code})")
        except Exception as e:
            print(f"✗ {name}: Não disponível ({str(e)})")


def test_cardapio():
    """Lista o cardápio disponível."""
    print_section("2. CONSULTANDO CARDÁPIO")

    try:
        response = requests.get(f"{CAIXA_URL}/cardapio")
        if response.status_code == 200:
            data = response.json()
            print(f"Total de itens: {data['total']}\n")
            for item in data['cardapio']:
                print(f"  • {item['nome']:15} - R$ {item['preco']:.2f}")
                if item['descricao']:
                    print(f"    {item['descricao']}")
        else:
            print(f"Erro ao consultar cardápio: {response.status_code}")
    except Exception as e:
        print(f"Erro: {e}")


def test_estoque_inicial():
    """Verifica o estoque inicial."""
    print_section("3. VERIFICANDO ESTOQUE INICIAL")

    try:
        response = requests.get(f"{ESTOQUE_API_URL}/estoque")
        if response.status_code == 200:
            data = response.json()
            print(f"Total de ingredientes: {data['total_ingredientes']}")
            print(f"Alertas críticos: {data['alertas']['criticos']}")
            print(f"Alertas baixos: {data['alertas']['baixos']}\n")

            print("Estoque atual:")
            for ing in data['estoque']:
                status_icon = "✓" if ing['status'] == 'OK' else "⚠" if ing['status'] == 'BAIXO' else "✗"
                print(
                    f"  {status_icon} {ing['nome']:15} - {ing['quantidade']:3} {ing['unidade']:10} [{ing['status']}]")
        else:
            print(f"Erro ao consultar estoque: {response.status_code}")
    except Exception as e:
        print(f"Erro: {e}")


def test_criar_pedidos():
    """Cria alguns pedidos de teste."""
    print_section("4. CRIANDO PEDIDOS DE TESTE")

    pedidos = [
        {"cliente": "João Silva", "item": "X-Salada", "observacao": "Sem tomate"},
        {"cliente": "Maria Santos", "item": "X-Bacon", "observacao": None},
        {"cliente": "Pedro Oliveira", "item": "X-Egg", "observacao": "Bem passado"},
    ]

    pedidos_criados = []

    for pedido in pedidos:
        try:
            response = requests.post(
                f"{CAIXA_URL}/pedidos",
                json=pedido,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 201:
                data = response.json()
                pedido_id = data['pedido']['id']
                pedidos_criados.append(pedido_id)
                print(
                    f"✓ Pedido #{pedido_id} criado: {pedido['item']} para {pedido['cliente']}")
            else:
                print(f"✗ Erro ao criar pedido: {response.json()}")
        except Exception as e:
            print(f"✗ Erro: {e}")

    return pedidos_criados


def test_acompanhar_fila():
    """Acompanha a fila da cozinha."""
    print_section("5. ACOMPANHANDO FILA DA COZINHA")

    print("Aguardando processamento dos pedidos (10 segundos)...")
    time.sleep(10)

    try:
        response = requests.get(f"{COZINHA_API_URL}/fila")
        if response.status_code == 200:
            data = response.json()
            print(f"\nTotal na fila: {data['total_fila']}")
            print(f"Recebidos: {data['recebidos']}")
            print(f"Em preparo: {data['preparando']}")

            if data['pedidos']:
                print("\nPedidos na fila:")
                for p in data['pedidos']:
                    print(
                        f"  • Pedido #{p['pedido_id']}: {p['item']} - Status: {p['status']}")
        else:
            print(f"Erro ao consultar fila: {response.status_code}")
    except Exception as e:
        print(f"Erro: {e}")


def test_verificar_estoque_pos_pedidos():
    """Verifica o estoque após os pedidos."""
    print_section("6. VERIFICANDO ESTOQUE APÓS PEDIDOS")

    try:
        response = requests.get(f"{ESTOQUE_API_URL}/estoque")
        if response.status_code == 200:
            data = response.json()

            print("Estoque atualizado:")
            for ing in data['estoque']:
                status_icon = "✓" if ing['status'] == 'OK' else "⚠" if ing['status'] == 'BAIXO' else "✗"
                print(
                    f"  {status_icon} {ing['nome']:15} - {ing['quantidade']:3} {ing['unidade']:10} [{ing['status']}]")
        else:
            print(f"Erro ao consultar estoque: {response.status_code}")
    except Exception as e:
        print(f"Erro: {e}")


def test_estatisticas_cozinha():
    """Verifica estatísticas da cozinha."""
    print_section("7. ESTATÍSTICAS DA COZINHA")

    try:
        response = requests.get(f"{COZINHA_API_URL}/estatisticas")
        if response.status_code == 200:
            data = response.json()

            print("Pedidos por status:")
            for status, qtd in data['pedidos_por_status'].items():
                print(f"  • {status}: {qtd}")

            print(f"\nTempo médio de preparo: {data['tempo_medio_preparo']}s")
            print(f"Tempo mínimo: {data['tempo_minimo']}s")
            print(f"Tempo máximo: {data['tempo_maximo']}s")
        else:
            print(f"Erro ao consultar estatísticas: {response.status_code}")
    except Exception as e:
        print(f"Erro: {e}")


def test_listar_pedidos():
    """Lista todos os pedidos cadastrados."""
    print_section("8. LISTANDO TODOS OS PEDIDOS")

    try:
        response = requests.get(f"{CAIXA_URL}/pedidos")
        if response.status_code == 200:
            data = response.json()
            print(f"Total de pedidos: {data['total']}\n")

            for pedido in data['pedidos'][:10]:  # Mostra apenas os 10 primeiros
                obs = f" - {pedido['observacao']}" if pedido['observacao'] else ""
                print(f"  #{pedido['id']:3} | {pedido['cliente']:20} | {pedido['item']:15} | "
                      f"R$ {pedido['valor']:6.2f} | {pedido['status']}{obs}")
        else:
            print(f"Erro ao listar pedidos: {response.status_code}")
    except Exception as e:
        print(f"Erro: {e}")


def main():
    """Executa todos os testes."""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "TESTE DO SISTEMA DE HAMBURGUERIA" + " " * 15 + "║")
    print("╚" + "═" * 58 + "╝")

    try:
        test_health_checks()
        test_cardapio()
        test_estoque_inicial()
        test_criar_pedidos()
        test_acompanhar_fila()
        test_verificar_estoque_pos_pedidos()
        test_estatisticas_cozinha()
        test_listar_pedidos()

        print_section("✓ TODOS OS TESTES CONCLUÍDOS")
        print("\nPara mais detalhes, acesse:")
        print(f"  • Swagger Caixa:    {CAIXA_URL}/apidocs")
        print(f"  • Swagger Cozinha:  {COZINHA_API_URL}/apidocs")
        print(f"  • Swagger Estoque:  {ESTOQUE_API_URL}/apidocs")

    except KeyboardInterrupt:
        print("\n\nTeste interrompido pelo usuário.")
    except Exception as e:
        print(f"\n\nErro durante execução: {e}")


if __name__ == "__main__":
    main()
