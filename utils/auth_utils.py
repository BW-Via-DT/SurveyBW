import logging

from flask import session

from utils.call_conn import connect

logger = logging.getLogger("auth_utils")


def is_authenticated():
    """Verifica se há uma sessão de login válida."""
    return 'local_user_id' in session


def connect_auth():
    """Mantido por compatibilidade. A tabela operator está agora na mesma BD."""
    return connect()


def _operator_to_dict(row):
    email = row[2] or ''
    username = email.split('@')[0] if '@' in email else email
    return {
        'number': row[0],
        'name': row[1],
        'email': email,
        'username': username,
    }


def get_operator_from_app_accounts(username=None, email=None):
    """
    Devolve os dados oficiais do utilizador vindos da tabela public.operator.

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
        conn = connect()
        cursor = conn.cursor()

        row = None

        # 1. Primeiro tenta procurar por email exato.
        if email:
            cursor.execute("""
                SELECT CAST(number AS VARCHAR), name, email
                FROM public.operator
                WHERE LOWER(email) = LOWER(%s)
                LIMIT 1
            """, (email,))

            row = cursor.fetchone()

        # 2. Se não encontrou por email, tenta pelo username.
        if not row and username:
            # Se vier DOMAIN\\username, fica só username.
            clean_username = username.split("\\")[-1]

            # Se o username já for um email, tenta email exato.
            if '@' in clean_username:
                cursor.execute("""
                    SELECT CAST(number AS VARCHAR), name, email
                    FROM public.operator
                    WHERE LOWER(email) = LOWER(%s)
                    LIMIT 1
                """, (clean_username,))
            else:
                # Compara a parte antes do @ (evita os wildcards do LIKE, como o "_").
                cursor.execute("""
                    SELECT CAST(number AS VARCHAR), name, email
                    FROM public.operator
                    WHERE LOWER(split_part(email, '@', 1)) = LOWER(%s)
                    LIMIT 1
                """, (clean_username,))

            row = cursor.fetchone()

        if not row:
            return None

        return _operator_to_dict(row)

    except Exception:
        logger.exception("[get_operator_from_app_accounts] Erro")
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
        conn = connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT CAST(number AS VARCHAR), name, email
            FROM public.operator
            WHERE CAST(number AS VARCHAR) = CAST(%s AS VARCHAR)
        """, (number,))

        row = cursor.fetchone()

        if not row:
            return None

        return _operator_to_dict(row)

    except Exception:
        logger.exception("Erro ao obter operador pelo number")
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
    Vai buscar o number do colaborador na tabela operator a partir do email.
    Se não encontrar, devolve fallback_id.
    """

    if not email:
        logger.warning("[_get_operator_number_by_email] email vazio/None -> a usar fallback_id=%r", fallback_id)
        return fallback_id

    conn_op = None
    cursor_op = None

    try:
        conn_op = connect()
        cursor_op = conn_op.cursor()

        cursor_op.execute("""
            SELECT CAST(number AS VARCHAR), name, costcenter
            FROM public.operator
            WHERE LOWER(email) = LOWER(%s)
            LIMIT 1
        """, (email,))

        row = cursor_op.fetchone()

        if row:
            return row[0]

        return fallback_id

    except Exception:
        logger.exception(
            "[_get_operator_number_by_email] ERRO ao consultar operator para email=%r -> a usar fallback_id=%r",
            email, fallback_id
        )
        return fallback_id

    finally:
        if cursor_op:
            cursor_op.close()
        if conn_op:
            conn_op.close()