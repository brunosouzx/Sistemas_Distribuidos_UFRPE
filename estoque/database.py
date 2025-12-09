import sqlite3
from contextlib import contextmanager

DATABASE_PATH = 'estoque.db'


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

        # Tabela de ingredientes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ingredientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome VARCHAR(100) UNIQUE NOT NULL,
                quantidade INTEGER DEFAULT 0,
                unidade VARCHAR(20) DEFAULT 'unidade',
                estoque_minimo INTEGER DEFAULT 10,
                data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tabela de receitas (relacionamento ingredientes x produtos)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS receitas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                produto VARCHAR(100) NOT NULL,
                ingrediente_nome VARCHAR(100) NOT NULL,
                quantidade_necessaria INTEGER NOT NULL,
                FOREIGN KEY (ingrediente_nome) REFERENCES ingredientes(nome)
            )
        ''')

        # Tabela de histórico de movimentação
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS movimentacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ingrediente_nome VARCHAR(100) NOT NULL,
                tipo VARCHAR(20) NOT NULL,  -- ENTRADA, SAIDA, AJUSTE
                quantidade INTEGER NOT NULL,
                quantidade_anterior INTEGER,
                quantidade_posterior INTEGER,
                motivo TEXT,
                pedido_id INTEGER,
                data_movimentacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ingrediente_nome) REFERENCES ingredientes(nome)
            )
        ''')

        # Verificar se já existem dados
        cursor.execute('SELECT COUNT(*) as count FROM ingredientes')
        if cursor.fetchone()['count'] == 0:
            # Inserir ingredientes iniciais
            ingredientes_iniciais = [
                ('pao', 100, 'unidade', 20),
                ('carne', 100, 'unidade', 20),
                ('queijo', 50, 'fatia', 10),
                ('presunto', 50, 'fatia', 10),
                ('bacon', 30, 'fatia', 10),
                ('calabresa', 30, 'fatia', 10),
                ('frango', 30, 'porcao', 10),
                ('ovo', 50, 'unidade', 15),
                ('alface', 40, 'folha', 10),
                ('tomate', 40, 'fatia', 10),
            ]
            cursor.executemany('''
                INSERT INTO ingredientes (
                               nome, quantidade, unidade, estoque_minimo
                            )
                VALUES (?, ?, ?, ?)
            ''', ingredientes_iniciais)

            # Inserir receitas
            receitas_iniciais = [
                ('X-Salada', 'pao', 1),
                ('X-Salada', 'carne', 1),
                ('X-Salada', 'queijo', 1),
                ('X-Salada', 'alface', 2),
                ('X-Salada', 'tomate', 2),

                ('X-Bacon', 'pao', 1),
                ('X-Bacon', 'carne', 1),
                ('X-Bacon', 'queijo', 1),
                ('X-Bacon', 'bacon', 2),

                ('X-Egg', 'pao', 1),
                ('X-Egg', 'carne', 1),
                ('X-Egg', 'queijo', 1),
                ('X-Egg', 'ovo', 1),


                ('X-Calabresa', 'pao', 1), ('X-Calabresa', 'carne', 1),
                ('X-Calabresa', 'queijo', 1), ('X-Calabresa', 'calabresa', 1),
                ('X-Calabresa', 'alface', 1),


                ('X-Frango', 'pao', 1), ('X-Frango', 'frango', 1),
                ('X-Frango', 'queijo', 1), ('X-Frango', 'presunto', 1),
                ('X-Frango', 'alface', 1),


                ('X-Ceara', 'pao', 1), ('X-Ceara', 'carne', 2),
                ('X-Ceara', 'frango', 1), ('X-Ceara', 'bacon', 2),
                ('X-Ceara', 'calabresa', 1), ('X-Ceara', 'queijo', 2),
                ('X-Ceara', 'presunto', 2), ('X-Ceara', 'ovo', 2),


                ('X-Tudo', 'pao', 1), ('X-Tudo', 'carne', 1),
                ('X-Tudo', 'queijo', 1), ('X-Tudo', 'presunto', 1),
                ('X-Tudo', 'bacon', 1), ('X-Tudo', 'ovo', 1),
            ]
            cursor.executemany('''
                INSERT INTO receitas (
                               produto, ingrediente_nome, quantidade_necessaria
                               )
                VALUES (?, ?, ?)
            ''', receitas_iniciais)

        print("[DB] Banco de dados do Estoque inicializado com sucesso!")


def obter_receita(produto):
    """Retorna os ingredientes necessários para um produto."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ingrediente_nome, quantidade_necessaria
            FROM receitas
            WHERE produto = ?
        ''', (produto,))

        return {row['ingrediente_nome']: row['quantidade_necessaria']
                for row in cursor.fetchall()}


def verificar_disponibilidade(produto):
    """Verifica se há ingredientes suficientes para preparar um produto."""
    receita = obter_receita(produto)

    if not receita:
        return False, f"Receita não encontrada para '{produto}'"

    with get_db_connection() as conn:
        cursor = conn.cursor()

        ingredientes_faltando = []

        for ingrediente, qtd_necessaria in receita.items():
            cursor.execute(
                'SELECT quantidade FROM ingredientes WHERE nome = ?',
                (ingrediente,)
            )
            result = cursor.fetchone()

            if not result:
                ingredientes_faltando.append(f"{ingrediente} (não cadastrado)")
            elif result['quantidade'] < qtd_necessaria:
                ingredientes_faltando.append(
                    f"{ingrediente} (disponível: {result['quantidade']},"
                    f"  necessário: {qtd_necessaria})"
                )

        if ingredientes_faltando:
            return False, f"Ingredientes insuficientes: {', '.join(ingredientes_faltando)}"

        return True, "Ingredientes disponíveis"


def dar_baixa_ingredientes(produto, pedido_id=None):
    """Dá baixa nos ingredientes necessários para um produto."""
    receita = obter_receita(produto)

    if not receita:
        raise ValueError(f"Receita não encontrada para '{produto}'")

    # Verificar disponibilidade primeiro
    disponivel, mensagem = verificar_disponibilidade(produto)
    if not disponivel:
        raise ValueError(mensagem)

    with get_db_connection() as conn:
        cursor = conn.cursor()

        movimentacoes = []

        for ingrediente, qtd_necessaria in receita.items():
            # Buscar quantidade atual
            cursor.execute(
                'SELECT quantidade FROM ingredientes WHERE nome = ?',
                (ingrediente,)
            )
            qtd_anterior = cursor.fetchone()['quantidade']
            qtd_posterior = qtd_anterior - qtd_necessaria

            # Atualizar estoque
            cursor.execute('''
                UPDATE ingredientes
                SET quantidade = quantidade - ?,
                    data_atualizacao = CURRENT_TIMESTAMP
                WHERE nome = ?
            ''', (qtd_necessaria, ingrediente))

            # Registrar movimentação
            cursor.execute('''
                INSERT INTO movimentacoes
                (ingrediente_nome, tipo, quantidade, quantidade_anterior,
                 quantidade_posterior, motivo, pedido_id)
                VALUES (?, 'SAIDA', ?, ?, ?, ?, ?)
            ''', (ingrediente, qtd_necessaria, qtd_anterior, qtd_posterior,
                  f"Baixa para produto: {produto}", pedido_id))

            movimentacoes.append({
                'ingrediente': ingrediente,
                'quantidade_baixada': qtd_necessaria,
                'quantidade_restante': qtd_posterior
            })

        return movimentacoes


def listar_estoque():
    """Lista todos os ingredientes do estoque."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT
                nome,
                quantidade,
                unidade,
                estoque_minimo,
                CASE
                    WHEN quantidade <= estoque_minimo THEN 'CRITICO'
                    WHEN quantidade <= estoque_minimo * 1.5 THEN 'BAIXO'
                    ELSE 'OK'
                END as status,
                data_atualizacao
            FROM ingredientes
            ORDER BY nome
        ''')
        return [dict(row) for row in cursor.fetchall()]


def adicionar_estoque(ingrediente_nome, quantidade, motivo="Reposição"):
    """Adiciona quantidade ao estoque de um ingrediente."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Buscar quantidade atual
        cursor.execute(
            'SELECT quantidade FROM ingredientes WHERE nome = ?',
            (ingrediente_nome,)
        )
        result = cursor.fetchone()

        if not result:
            raise ValueError(
                f"Ingrediente '{ingrediente_nome}' não encontrado")

        qtd_anterior = result['quantidade']
        qtd_posterior = qtd_anterior + quantidade

        # Atualizar estoque
        cursor.execute('''
            UPDATE ingredientes
            SET quantidade = quantidade + ?,
                data_atualizacao = CURRENT_TIMESTAMP
            WHERE nome = ?
        ''', (quantidade, ingrediente_nome))

        # Registrar movimentação
        cursor.execute('''
            INSERT INTO movimentacoes
            (ingrediente_nome, tipo, quantidade, quantidade_anterior,
             quantidade_posterior, motivo)
            VALUES (?, 'ENTRADA', ?, ?, ?, ?)
        ''', (ingrediente_nome, quantidade, qtd_anterior, qtd_posterior,
              motivo))

        return {
            'ingrediente': ingrediente_nome,
            'quantidade_adicionada': quantidade,
            'quantidade_anterior': qtd_anterior,
            'quantidade_atual': qtd_posterior
        }


def historico_movimentacoes(ingrediente_nome=None, limit=100):
    """Retorna o histórico de movimentações."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        if ingrediente_nome:
            cursor.execute('''
                SELECT * FROM movimentacoes
                WHERE ingrediente_nome = ?
                ORDER BY data_movimentacao DESC
                LIMIT ?
            ''', (ingrediente_nome, limit))
        else:
            cursor.execute('''
                SELECT * FROM movimentacoes
                ORDER BY data_movimentacao DESC
                LIMIT ?
            ''', (limit,))

        return [dict(row) for row in cursor.fetchall()]
