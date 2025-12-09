import sqlite3
from contextlib import contextmanager

DATABASE_PATH = 'caixa.db'


@contextmanager
def get_db_connection():
    """Context manager para conexão com o banco de dados."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_db():
    """Inicializa o banco de dados com as tabelas necessárias."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Tabela de pedidos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente VARCHAR(100) NOT NULL,
                item VARCHAR(100) NOT NULL,
                observacao TEXT,
                status VARCHAR(20) DEFAULT 'PENDENTE',
                valor DECIMAL(10, 2) DEFAULT 0.00,
                data_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tabela de itens do cardápio
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cardapio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome VARCHAR(100) UNIQUE NOT NULL,
                descricao TEXT,
                preco DECIMAL(10, 2) NOT NULL,
                disponivel BOOLEAN DEFAULT 1,
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Inserir itens iniciais do cardápio se não existirem
        cursor.execute('SELECT COUNT(*) as count FROM cardapio')
        if cursor.fetchone()['count'] == 0:
            itens_iniciais = [
                # Hambúrgueres
                ('X-Salada', 'Hambúrguer com salada', 15.00),
                ('X-Bacon', 'Hambúrguer com bacon', 18.00),
                ('X-Egg', 'Hambúrguer com ovo', 16.00),
                ('X-Calabresa', 'Carne, queijo, calabresa acebolada', 26.00),
                ('X-Frango', 'Filé de frango, queijo, presunto', 26.00),
                ('X-Tudo', 'Completo com bacon, ovo e presunto', 32.00),
                ('X-Ceara', 'O gigante: Carne dupla, frango, bacon,'
                 ' calabresa e ovo', 42.00),
                # Bebidas
                ('Coca-Cola', 'Refrigerante 350ml', 5.00),
                ('Guaraná', 'Refrigerante 350ml', 5.00),
                ('Suco de Laranja', 'Suco natural 300ml', 7.00),
                ('Água Mineral', 'Água sem gás 500ml', 3.00),
                ('Cerveja', 'Cerveja long neck 355ml', 8.00),
            ]
            cursor.executemany(
                'INSERT INTO cardapio (nome, descricao, preco) '
                'VALUES (?, ?, ?)',
                itens_iniciais
            )

        print("[DB] Banco de dados do Caixa inicializado com sucesso!")


def inserir_pedido(cliente, item, observacao=None):
    """Insere um novo pedido no banco de dados."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Buscar preço do item
        cursor.execute(
            'SELECT preco, disponivel FROM cardapio WHERE nome = ?',
            (item,)
        )
        result = cursor.fetchone()

        if not result:
            raise ValueError(f"Item '{item}' não encontrado no cardápio")

        if not result['disponivel']:
            raise ValueError(f"Item '{item}' não está disponível no momento")

        preco = result['preco']

        # Inserir pedido
        cursor.execute('''
            INSERT INTO pedidos (cliente, item, observacao, valor, status)
            VALUES (?, ?, ?, ?, 'PENDENTE')
        ''', (cliente, item, observacao, preco))

        pedido_id = cursor.lastrowid

        return {
            'id': pedido_id,
            'cliente': cliente,
            'item': item,
            'observacao': observacao,
            'valor': preco,
            'status': 'PENDENTE'
        }


def atualizar_status_pedido(pedido_id, novo_status):
    """Atualiza o status de um pedido."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE pedidos
            SET status = ?, data_atualizacao = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (novo_status, pedido_id))

        if cursor.rowcount == 0:
            raise ValueError(f"Pedido {pedido_id} não encontrado")


def listar_pedidos(status=None, limit=50):
    """Lista pedidos, opcionalmente filtrados por status."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        if status:
            cursor.execute('''
                SELECT * FROM pedidos
                WHERE status = ?
                ORDER BY data_pedido DESC
                LIMIT ?
            ''', (status, limit))
        else:
            cursor.execute('''
                SELECT * FROM pedidos
                ORDER BY data_pedido DESC
                LIMIT ?
            ''', (limit,))

        return [dict(row) for row in cursor.fetchall()]


def buscar_pedido(pedido_id):
    """Busca um pedido específico por ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM pedidos WHERE id = ?', (pedido_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def listar_cardapio():
    """Lista todos os itens do cardápio."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM cardapio
            WHERE disponivel = 1
            ORDER BY nome
        ''')
        return [dict(row) for row in cursor.fetchall()]
