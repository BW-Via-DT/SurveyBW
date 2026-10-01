import base64
import io
import logging
import secrets
from datetime import datetime, timedelta

import pyotp
import qrcode
from argon2.exceptions import InvalidHash, VerifyMismatchError
from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from extensions import limiter
from utils.call_conn import connect
from .auth import ph, log_login, _set_session, _login_fail

mfa_api = Blueprint("mfa", __name__)
logger = logging.getLogger("mfa")

MFA_PENDING_TTL_MINUTES = 5
BACKUP_CODES_COUNT = 10


# ---------------------------------------------------------------------------
# 2º passo do login (verificação do código)
# ---------------------------------------------------------------------------

@mfa_api.route('/mfa/challenge', methods=['GET'])
def mfa_challenge():
    """Página exibida depois da password correta, quando o utilizador tem MFA ativo."""
    if 'mfa_pending_user_id' not in session:
        return redirect(url_for('index'))
    return render_template('mfa_challenge.html')


@mfa_api.route('/mfa/verify', methods=['POST'])
@limiter.limit("6 per minute")
def mfa_verify():
    is_xhr = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    pending_id = session.get('mfa_pending_user_id')
    expires = session.get('mfa_pending_expires')

    if not pending_id or not expires or datetime.fromisoformat(expires) < datetime.utcnow():
        session.pop('mfa_pending_user_id', None)
        session.pop('mfa_pending_expires', None)
        return _login_fail(is_xhr, 'Session expired. Please log in again.')

    code = (request.form.get('code')
            or (request.get_json(silent=True) or {}).get('code')
            or '').strip().replace(' ', '')

    if not code:
        return _login_fail(is_xhr, 'Please enter the authentication code.')

    conn = connect()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT OperatorNumber, Name, isAdmin, MFASecret
        FROM public.Users
        WHERE Id = %s
    """, (pending_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row or not row.MFASecret:
        session.pop('mfa_pending_user_id', None)
        session.pop('mfa_pending_expires', None)
        return _login_fail(is_xhr, 'Invalid credentials.')

    op_number, name, is_admin, mfa_secret = row

    totp = pyotp.TOTP(mfa_secret)
    code_is_valid = totp.verify(code, valid_window=1)  # tolera +-30s de desfasamento
    used_backup = False

    if not code_is_valid:
        used_backup = _try_backup_code(pending_id, code)

    if not (code_is_valid or used_backup):
        log_login(operator_number=op_number, local_user_id=pending_id,
                  success=False, failure_reason='bad_mfa_code')
        return _login_fail(is_xhr, 'Invalid authentication code.')

    # Sucesso: limpa o estado pendente e cria a sessão autenticada de verdade
    session.pop('mfa_pending_user_id', None)
    session.pop('mfa_pending_expires', None)
    _set_session(pending_id, op_number, name, is_admin)

    log_login(operator_number=op_number, local_user_id=pending_id, success=True,
              failure_reason='backup_code_used' if used_backup else None)

    if is_xhr:
        return jsonify({'success': True, 'redirect': url_for('surveys_routes.surveys_page')})
    return redirect(url_for('surveys_routes.surveys_page'))


@mfa_api.route('/mfa/enroll', methods=['GET'])
def mfa_enroll():
    """
    Página de configuração obrigatória do MFA na primeira vez.
    O utilizador já validou a password, mas ainda não tem sessão autenticada completa.
    """
    enroll_id = _get_mfa_enroll_user_id()

    if not enroll_id:
        return redirect(url_for('index'))

    return render_template('mfa_enroll.html')


# ---------------------------------------------------------------------------
# Enrolamento / gestão do MFA (utilizador já autenticado)
# ---------------------------------------------------------------------------

@mfa_api.route('/mfa/setup', methods=['GET'])
def mfa_setup():
    """
    Gera um novo secret + QR code.
    Pode ser usado:
    - por utilizador já autenticado em /mfa/manage
    - por utilizador em primeira configuração obrigatória após password correta
    """

    local_user_id = session.get('local_user_id')
    enroll_user_id = _get_mfa_enroll_user_id()

    user_id = local_user_id or enroll_user_id

    if not user_id:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    conn = connect()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT OperatorNumber
        FROM public.Users
        WHERE Id = %s
    """, (user_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row:
        return jsonify({'success': False, 'message': 'User not found'}), 404

    operator_number = row.OperatorNumber

    secret = pyotp.random_base32()
    session['mfa_setup_secret'] = secret

    otpauth_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=operator_number,
        issuer_name='SurveyBW'
    )

    qr_img = qrcode.make(otpauth_uri)
    buf = io.BytesIO()
    qr_img.save(buf, format='PNG')
    qr_base64 = base64.b64encode(buf.getvalue()).decode()

    return jsonify({
        'success': True,
        'qr_code': f'data:image/png;base64,{qr_base64}',
        'secret': secret
    })


@mfa_api.route('/mfa/enable', methods=['POST'])
@limiter.limit("6 per minute")
def mfa_enable():
    """
    Confirma o setup: exige um código válido antes de gravar o secret definitivamente.

    Funciona em dois cenários:
    - Utilizador já autenticado a ativar MFA nas definições.
    - Primeira configuração obrigatória logo após login com password.
    """

    local_user_id = session.get('local_user_id')
    enroll_user_id = _get_mfa_enroll_user_id()
    setup_secret = session.get('mfa_setup_secret')

    user_id = local_user_id or enroll_user_id

    if not user_id:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    if not setup_secret:
        return jsonify({'success': False, 'message': 'Setup session expired. Start again.'}), 400

    data = request.get_json(silent=True) or {}
    code = (data.get('code') or '').strip().replace(' ', '')

    if not code:
        return jsonify({'success': False, 'message': 'Please enter the authentication code.'}), 400

    totp = pyotp.TOTP(setup_secret)

    if not totp.verify(code, valid_window=1):
        return jsonify({'success': False, 'message': 'Invalid code. Please try again.'}), 400

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE public.Users
        SET MFASecret = %s,
            MFAEnabled = TRUE
        WHERE Id = %s
    """, (setup_secret, user_id))

    conn.commit()

    cursor.execute("""
        SELECT OperatorNumber, Name, isAdmin
        FROM public.Users
        WHERE Id = %s
    """, (user_id,))
    user_row = cursor.fetchone()

    cursor.close()
    conn.close()

    if not user_row:
        return jsonify({'success': False, 'message': 'User not found'}), 404

    backup_codes = _generate_backup_codes(user_id)

    session.pop('mfa_setup_secret', None)
    session.pop('mfa_enroll_user_id', None)
    session.pop('mfa_enroll_expires', None)

    op_number, name, is_admin = user_row

    # Se era primeira configuração, autentica agora.
    # Se já estava autenticado, isto também renova a sessão.
    _set_session(user_id, op_number, name, is_admin)

    log_login(
        operator_number=op_number,
        local_user_id=user_id,
        success=True,
        failure_reason=None
    )

    logger.info("MFA ativado para local_user_id=%s", user_id)

    return jsonify({
        'success': True,
        'redirect': url_for('surveys_routes.surveys_page'),
        'backup_codes': backup_codes
    })


@mfa_api.route('/mfa/disable', methods=['POST'])
@limiter.limit("5 per hour")
def mfa_disable():
    """Desativa o MFA. Exige a password atual para confirmar a identidade."""
    local_user_id = session.get('local_user_id')
    if not local_user_id:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    data = request.get_json(silent=True) or {}
    password = data.get('password', '')

    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT PasswordHash FROM public.Users WHERE Id = %s", (local_user_id,))
    row = cursor.fetchone()

    if not row:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'User not found'}), 404

    try:
        ph.verify(row[0], password)
    except (VerifyMismatchError, InvalidHash):
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Incorrect password.'}), 401

    cursor.execute("""
        UPDATE public.Users
        SET MFAEnabled = FALSE, MFASecret = NULL
        WHERE Id = %s
    """, (local_user_id,))
    cursor.execute("DELETE FROM public.MFABackupCodes WHERE UserId = %s", (local_user_id,))
    conn.commit()
    cursor.close()
    conn.close()

    logger.info("MFA desativado para local_user_id=%s", local_user_id)
    return jsonify({'success': True})


@mfa_api.route('/mfa/regenerate_backup_codes', methods=['POST'])
@limiter.limit("5 per hour")
def mfa_regenerate_backup_codes():
    """Invalida os backup codes antigos e gera um conjunto novo."""
    local_user_id = session.get('local_user_id')
    if not local_user_id:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    data = request.get_json(silent=True) or {}
    password = data.get('password', '')

    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT PasswordHash, MFAEnabled FROM public.Users WHERE Id = %s", (local_user_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row:
        return jsonify({'success': False, 'message': 'User not found'}), 404

    password_hash, mfa_enabled = row
    if not mfa_enabled:
        return jsonify({'success': False, 'message': 'MFA is not enabled.'}), 400

    try:
        ph.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHash):
        return jsonify({'success': False, 'message': 'Incorrect password.'}), 401

    backup_codes = _generate_backup_codes(local_user_id)
    logger.info("Backup codes regenerados para local_user_id=%s", local_user_id)
    return jsonify({'success': True, 'backup_codes': backup_codes})


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _generate_backup_codes(local_user_id, count=BACKUP_CODES_COUNT):
    """Gera backup codes novos, guarda-os com hash e devolve os códigos em claro
    (só nesta chamada -> nunca mais serão visíveis em texto simples)."""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM public.MFABackupCodes WHERE UserId = %s", (local_user_id,))

    plain_codes = []
    for _ in range(count):
        code = f"{secrets.token_hex(2)}-{secrets.token_hex(2)}"  # ex: a1b2-c3d4
        plain_codes.append(code)
        cursor.execute("""
            INSERT INTO public.MFABackupCodes (UserId, CodeHash, CreatedAt)
            VALUES (%s, %s, %s)
        """, (local_user_id, ph.hash(code), datetime.utcnow()))

    conn.commit()
    cursor.close()
    conn.close()
    return plain_codes


def _try_backup_code(local_user_id, code):
    """Verifica se `code` corresponde a algum backup code ainda não usado.
    Se corresponder, marca-o como usado (uso único) e devolve True."""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT Id, CodeHash
        FROM public.MFABackupCodes
        WHERE UserId = %s AND UsedAt IS NULL
    """, (local_user_id,))
    rows = cursor.fetchall()

    matched_id = None
    for row_id, code_hash in rows:
        try:
            ph.verify(code_hash, code)
            matched_id = row_id
            break
        except (VerifyMismatchError, InvalidHash):
            continue

    if matched_id:
        cursor.execute("""
            UPDATE public.MFABackupCodes
            SET UsedAt = %s
            WHERE Id = %s
        """, (datetime.utcnow(), matched_id))
        conn.commit()

    cursor.close()
    conn.close()
    return matched_id is not None


def _get_mfa_enroll_user_id():
    enroll_id = session.get('mfa_enroll_user_id')
    expires = session.get('mfa_enroll_expires')

    if not enroll_id or not expires:
        return None

    try:
        if datetime.fromisoformat(expires) < datetime.utcnow():
            session.pop('mfa_enroll_user_id', None)
            session.pop('mfa_enroll_expires', None)
            session.pop('mfa_setup_secret', None)
            return None
    except ValueError:
        session.pop('mfa_enroll_user_id', None)
        session.pop('mfa_enroll_expires', None)
        session.pop('mfa_setup_secret', None)
        return None

    return enroll_id