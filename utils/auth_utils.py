from flask import session
import pyodbc
from utils.call_conn import get_db_connection


def is_authenticated():
    """Verifica se há uma sessão de login válida."""
    return 'local_user_id' in session


def connect_auth():
    conn_str = get_db_connection()
    return pyodbc.connect(conn_str)


def get_operator_from_app_accounts(username=None, email=None):
    """
    Devolve os dados oficiais do utilizador vindos de APP_DT_Accounts.dbo.Operator.

    Pode procurar por:
    - email exato;
    - username técnico antes do @;
    - username já em formato email.

    Retorna:
        {
            'number': ...,
            'name': ...,
            'email': ...,
            'username': ...
        }

    Ou None se não encontrar.
    """

    if username:
        username = username.strip()

    if email:
        email = email.strip()

    if not username and not email:
        return None

    conn = None
    cursor = None

    try:
        conn = connect_auth()
        cursor = conn.cursor()

        row = None

        # 1. Primeiro tenta procurar por email exato.
        if email:
            cursor.execute("""
                SELECT
                    CAST([number] AS VARCHAR),
                    [name],
                    [email]
                FROM [APP_DT_Accounts].[dbo].[Operator]
                WHERE LOWER([email]) = LOWER(?)
            """, (email,))

            row = cursor.fetchone()

        # 2. Se não encontrou por email, tenta pelo username.
        if not row and username:
            # Se vier DOMAIN\\username, fica só username.
            clean_username = username.split("\\")[-1]

            # Se o username já for um email, tenta email exato.
            if '@' in clean_username:
                cursor.execute("""
                    SELECT
                        CAST([number] AS VARCHAR),
                        [name],
                        [email]
                    FROM [APP_DT_Accounts].[dbo].[Operator]
                    WHERE LOWER([email]) = LOWER(?)
                """, (clean_username,))
            else:
                cursor.execute("""
                    SELECT
                        CAST([number] AS VARCHAR),
                        [name],
                        [email]
                    FROM [APP_DT_Accounts].[dbo].[Operator]
                    WHERE LOWER([email]) LIKE LOWER(?)
                """, (clean_username + '@%',))

            row = cursor.fetchone()

        if not row:
            return None

        operator_email = row[2] or ''
        operator_username = operator_email.split('@')[0] if '@' in operator_email else operator_email

        return {
            'number': row[0],
            'name': row[1],
            'email': operator_email,
            'username': operator_username
        }

    except Exception as e:
        print(f"[get_operator_from_app_accounts] Erro: {str(e)}")
        return None

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_operator_by_number(number):
    """Devolve {number, name, email, username} a partir do number. None se não encontrar."""

    if not number:
        return None

    conn = None
    cursor = None

    try:
        conn = connect_auth()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                CAST([number] AS VARCHAR),
                [name],
                [email]
            FROM [APP_DT_Accounts].[dbo].[Operator]
            WHERE [number] = ?
        """, (number,))

        row = cursor.fetchone()

        if not row:
            return None

        email = row[2] or ''
        username = email.split('@')[0] if '@' in email else email

        return {
            'number': row[0],
            'name': row[1],
            'email': email,
            'username': username
        }

    except Exception as e:
        print(f"Erro ao obter operador pelo number: {str(e)}")
        return None

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_username_by_number(number):
    """Mantido por compatibilidade com o código existente."""
    operator = get_operator_by_number(number)
    return operator['username'] if operator else None


def _get_operator_number_by_email(email, fallback_id):
    """
    Vai buscar o number do colaborador na tabela Operator a partir do email.
    Se não encontrar, devolve fallback_id.
    """

    if not email:
        print(f"[_get_operator_number_by_email] email vazio/None -> a usar fallback_id={fallback_id!r}")
        return fallback_id

    conn_op = None
    cursor_op = None

    try:
        conn_op = connect_auth()
        cursor_op = conn_op.cursor()

        cursor_op.execute("""
            SELECT
                CAST([number] AS VARCHAR),
                [name],
                [costcenter]
            FROM [APP_DT_Accounts].[dbo].[Operator]
            WHERE LOWER([email]) = LOWER(?)
        """, (email,))

        row = cursor_op.fetchone()

        if row:
            return row[0]

        return fallback_id

    except Exception as e:
        print(
            f"[_get_operator_number_by_email] ERRO ao consultar Operator "
            f"para email={email!r} -> a usar fallback_id={fallback_id!r}. "
            f"Erro: {str(e)}"
        )
        return fallback_id

    finally:
        if cursor_op:
            cursor_op.close()
        if conn_op:
            conn_op.close()