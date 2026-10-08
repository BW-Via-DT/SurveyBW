import logging
import secrets
from datetime import datetime, timedelta

import psycopg2
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerifyMismatchError
from flask import (Blueprint, current_app, flash, jsonify, redirect,
                    render_template, request, session, url_for)

from extensions import limiter
from utils.call_conn import get_db_connection
from utils.call_conn import connect
from utils.auth_utils import get_operator_from_app_accounts

auth_api = Blueprint("auth", __name__)
logger = logging.getLogger("auth")
ph = PasswordHasher()

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
MIN_PASSWORD_LENGTH = 10

USER_COLUMNS = """Id, OperatorNumber, PasswordHash, Name, Email, isAdmin,
                   FailedAttempts, LockedUntil, MFAEnabled, MFASecret"""


def _post_login_redirect():
    return redirect(url_for('surveys_routes.surveys_page'))


def _set_session(local_id, operator_number, name, is_admin, email=None):
    session.clear()
    session.permanent = True

    session['local_user_id'] = local_id
    session['operator_number'] = operator_number
    session['name'] = name or operator_number
    session['email'] = email
    session['username'] = email.split('@')[0] if email and '@' in email else operator_number
    session['is_admin'] = bool(is_admin)
    session['role'] = 'admin' if is_admin else 'normal'


def log_login(operator_number=None, local_user_id=None, success=True,
              failure_reason=None, attempted_username=None):
    conn = cursor = None
    try:
        conn = connect()
        cursor = conn.cursor()
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr or '')
        ip_address = ip_address.split(',')[0].strip()
        cursor.execute("""
            INSERT INTO public.LoginHistory
                (OperatorNumber, LocalUserId, AttemptedUsername, IpAddress, Success, FailureReason, CreatedAt)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (operator_number, local_user_id, attempted_username, ip_address,
              success, failure_reason, datetime.utcnow()))
        conn.commit()
    except Exception:
        logger.exception("Falha ao gravar log de login")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def _clean_windows_username(raw_user):
    """
    Recebe DOMAIN\\username, username@domain.com ou username.
    Devolve só username.
    """
    if not raw_user:
        return None

    value = raw_user.strip()

    if "\\" in value:
        value = value.split("\\")[-1]

    if "@" in value:
        value = value.split("@")[0]

    value = value.strip().lower()
    return value or None


def _find_local_user(identifier):
    conn = cursor = None

    try:
        conn = connect()
        cursor = conn.cursor()

        cursor.execute(f"""
            SELECT {USER_COLUMNS}
            FROM public.Users
            WHERE
                LOWER(Email) = LOWER(%s)
                OR LOWER(split_part(Email, '@', 1)) = LOWER(%s)
        """, (identifier, identifier))

        return cursor.fetchone()

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def _ensure_local_user_from_app_accounts(identifier):
    """Cria/sincroniza o utilizador local a partir da tabela oficial de contas quando ainda não existe localmente."""
    if not identifier:
        return None

    operator = get_operator_from_app_accounts(username=identifier)
    if not operator:
        return None

    return _sync_or_create_local_user_from_operator(operator)


def _sync_or_create_local_user_from_operator(operator):
    if not operator:
        return None

    operator_number = operator['number']
    name = operator['name']
    email = operator['email']

    conn = cursor = None

    try:
        conn = connect()
        cursor = conn.cursor()

        cursor.execute(f"""
            SELECT {USER_COLUMNS}
            FROM public.Users
            WHERE OperatorNumber = %s
               OR LOWER(Email) = LOWER(%s)
        """, (operator_number, email))

        existing = cursor.fetchone()

        if existing:
            local_id = existing[0]

            cursor.execute("""
                UPDATE public.Users
                SET OperatorNumber = %s,
                    Name = %s,
                    Email = %s,
                    UpdatedAt = %s
                WHERE Id = %s
            """, (operator_number, name, email, datetime.utcnow(), local_id))

            conn.commit()

            cursor.execute(f"""
                SELECT {USER_COLUMNS}
                FROM public.Users
                WHERE Id = %s
            """, (local_id,))

            return cursor.fetchone()

        now = datetime.utcnow()
        cursor.execute("""
            INSERT INTO public.Users
                (OperatorNumber, Name, Email, PasswordHash, isAdmin,
                 FailedAttempts, LockedUntil, CreatedAt, UpdatedAt,
                 MFASecret, MFAEnabled)
            VALUES (%s, %s, %s, '', FALSE, 0, NULL, %s, %s, NULL, FALSE)
            RETURNING Id
        """, (operator_number, name, email, now, now))

        local_id = cursor.fetchone()[0]
        conn.commit()

        cursor.execute(f"""
            SELECT {USER_COLUMNS}
            FROM public.Users
            WHERE Id = %s
        """, (local_id,))

        return cursor.fetchone()

    except Exception:
        logger.exception("Erro ao sincronizar/criar utilizador local")
        if conn:
            conn.rollback()
        return None

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def _redirect_to_mfa_flow(local_id, op_number, name, email, is_admin, mfa_enabled, mfa_secret, is_xhr=False):
    """
    Decide se vai para challenge MFA ou enrollment QR Code.
    """

    if not current_app.config.get('MFA_ENABLED', False):
        _set_session(local_id, op_number, name, is_admin, email)
        log_login(
            operator_number=op_number,
            local_user_id=local_id,
            success=True,
            failure_reason='mfa_disabled'
        )

        if is_xhr:
            return jsonify({
                'success': True,
                'redirect': url_for('surveys_routes.surveys_page')
            })

        return redirect(url_for('surveys_routes.surveys_page'))

    if mfa_enabled and mfa_secret:
        session.clear()
        session['mfa_pending_user_id'] = local_id
        session['mfa_pending_expires'] = (
            datetime.utcnow() + timedelta(minutes=5)
        ).isoformat()

        log_login(
            operator_number=op_number,
            local_user_id=local_id,
            success=False,
            failure_reason='mfa_required'
        )

        if is_xhr:
            return jsonify({
                'success': True,
                'mfa_required': True,
                'redirect': url_for('mfa.mfa_challenge')
            })

        return redirect(url_for('mfa.mfa_challenge'))

    session.clear()
    session['mfa_enroll_user_id'] = local_id
    session['mfa_enroll_expires'] = (
        datetime.utcnow() + timedelta(minutes=10)
    ).isoformat()

    log_login(
        operator_number=op_number,
        local_user_id=local_id,
        success=False,
        failure_reason='mfa_enrollment_required'
    )

    if is_xhr:
        return jsonify({
            'success': True,
            'mfa_setup_required': True,
            'redirect': url_for('mfa.mfa_enroll')
        })

    return redirect(url_for('mfa.mfa_enroll'))


@auth_api.route('/check_username', methods=['POST'])
def check_username():
    data = request.get_json(silent=True) or {}
    identifier = (data.get('username') or request.form.get('username', '')).strip()

    if not identifier:
        return jsonify({'exists': False, 'password_required': False})

    account = _find_local_user(identifier)
    if not account:
        account = _ensure_local_user_from_app_accounts(identifier)

    if not account:
        return jsonify({'exists': False, 'password_required': False})

    password_hash = account[2]
    if not password_hash:
        session.permanent = True
        session['initial_password_user_id'] = account[0]
        session['initial_password_expires'] = (
            datetime.utcnow() + timedelta(minutes=10)
        ).isoformat()
        session['needs_password_setup'] = True

    return jsonify({
        'exists': True,
        'password_required': not bool(password_hash)
    })


@auth_api.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if request.method != 'POST':
        return redirect(url_for('index'))

    is_xhr = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    identifier = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    generic_error = 'Invalid credentials.'

    if not identifier or not password:
        return _login_fail(is_xhr, generic_error)

    account = _find_local_user(identifier)

    if not account:
        account = _ensure_local_user_from_app_accounts(identifier)

    if not account:
        log_login(
            success=False,
            failure_reason='not_found',
            attempted_username=identifier
        )
        return _login_fail(is_xhr, generic_error)

    (
        local_id,
        op_number,
        password_hash,
        name,
        email,
        is_admin,
        failed_attempts,
        locked_until,
        mfa_enabled,
        mfa_secret
    ) = account

    if locked_until and locked_until > datetime.utcnow():
        log_login(
            operator_number=op_number,
            local_user_id=local_id,
            success=False,
            failure_reason='locked'
        )
        return _login_fail(is_xhr, 'Account temporarily locked. Please try again later.')

    if not password_hash:
        session.clear()
        session.permanent = True
        session['initial_password_user_id'] = local_id
        session['initial_password_expires'] = (
            datetime.utcnow() + timedelta(minutes=10)
        ).isoformat()
        session['needs_password_setup'] = True

        log_login(
            operator_number=op_number,
            local_user_id=local_id,
            success=False,
            failure_reason='password_not_set',
            attempted_username=identifier
        )

        if is_xhr:
            return jsonify({
                'success': False,
                'needs_initial_password': True,
                'redirect': url_for('index'),
                'message': 'Set your initial password to continue.'
            }), 403

        flash('Please set your initial password to continue.', category='info')
        return redirect(url_for('index'))

    try:
        ph.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHash):
        _register_failed_attempt(local_id, failed_attempts or 0)

        log_login(
            operator_number=op_number,
            local_user_id=local_id,
            success=False,
            failure_reason='wrong_password'
        )

        return _login_fail(is_xhr, generic_error)

    _reset_failed_attempts(local_id)

    if ph.check_needs_rehash(password_hash):
        _update_password_hash(local_id, ph.hash(password))

    # Sincroniza dados oficiais do APP_DT_Accounts
    operator = get_operator_from_app_accounts(
        username=identifier,
        email=email
    )

    if operator:
        synced = _sync_or_create_local_user_from_operator(operator)

        if synced:
            (
                local_id,
                op_number,
                password_hash,
                name,
                email,
                is_admin,
                failed_attempts,
                locked_until,
                mfa_enabled,
                mfa_secret
            ) = synced

    return _redirect_to_mfa_flow(
        local_id=local_id,
        op_number=op_number,
        name=name,
        email=email,
        is_admin=is_admin,
        mfa_enabled=mfa_enabled,
        mfa_secret=mfa_secret,
        is_xhr=is_xhr
    )


@auth_api.route('/windows_login')
@limiter.limit("10 per minute")
def windows_login():
    raw_user = request.environ.get('REMOTE_USER')
    username = _clean_windows_username(raw_user)

    if not username:
        log_login(
            success=False,
            failure_reason='missing_remote_user'
        )
        flash('Windows authentication failed or is not active.', category='error')
        return redirect(url_for('index'))

    operator = get_operator_from_app_accounts(username=username)

    if not operator:
        log_login(
            success=False,
            failure_reason='operator_not_found',
            attempted_username=username
        )
        flash('User not found in APP_DT_Accounts.', category='error')
        return redirect(url_for('index'))

    account = _sync_or_create_local_user_from_operator(operator)

    if not account:
        log_login(
            operator_number=operator.get('number'),
            success=False,
            failure_reason='local_user_sync_failed',
            attempted_username=username
        )
        flash('Could not create or update local user.', category='error')
        return redirect(url_for('index'))

    (
        local_id,
        op_number,
        password_hash,
        name,
        email,
        is_admin,
        failed_attempts,
        locked_until,
        mfa_enabled,
        mfa_secret
    ) = account

    if locked_until and locked_until > datetime.utcnow():
        log_login(
            operator_number=op_number,
            local_user_id=local_id,
            success=False,
            failure_reason='locked'
        )
        flash('Account temporarily locked. Please try again later.', category='error')
        return redirect(url_for('index'))

    if not password_hash:
        session.clear()
        session.permanent = True
        session['initial_password_user_id'] = local_id
        session['initial_password_expires'] = (
            datetime.utcnow() + timedelta(minutes=10)
        ).isoformat()
        session['needs_password_setup'] = True

        log_login(
            operator_number=op_number,
            local_user_id=local_id,
            success=False,
            failure_reason='initial_password_required'
        )

        flash('Please set your initial password to continue.', category='info')
        return redirect(url_for('index'))

    return _redirect_to_mfa_flow(
        local_id=local_id,
        op_number=op_number,
        name=name,
        email=email,
        is_admin=is_admin,
        mfa_enabled=mfa_enabled,
        mfa_secret=mfa_secret,
        is_xhr=False
    )


def _login_fail(is_xhr, message):
    if is_xhr:
        return jsonify({'success': False, 'message': message}), 401
    flash(message, category='error')
    return redirect(url_for('index'))


def _register_failed_attempt(local_id, current_failed_attempts):
    conn = connect()
    cursor = conn.cursor()
    new_count = current_failed_attempts + 1
    locked_until = None
    if new_count >= MAX_FAILED_ATTEMPTS:
        locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_MINUTES)
        new_count = 0
    cursor.execute("""
        UPDATE public.Users
        SET FailedAttempts = %s, LockedUntil = %s
        WHERE Id = %s
    """, (new_count, locked_until, local_id))
    conn.commit()
    cursor.close()
    conn.close()


def _reset_failed_attempts(local_id):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE public.Users
        SET FailedAttempts = 0, LockedUntil = NULL
        WHERE Id = %s
    """, (local_id,))
    conn.commit()
    cursor.close()
    conn.close()


def _update_password_hash(local_id, new_hash):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("UPDATE public.Users SET PasswordHash = %s WHERE Id = %s", (new_hash, local_id))
    conn.commit()
    cursor.close()
    conn.close()


@auth_api.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@auth_api.route('/initial_password', methods=['GET'])
def initial_password():
    local_id = session.get('initial_password_user_id')
    expires = session.get('initial_password_expires')

    if not local_id or not expires:
        flash('Invalid password setup session.', category='error')
        return redirect(url_for('index'))

    try:
        expires_dt = datetime.fromisoformat(expires)
    except ValueError:
        session.clear()
        flash('Invalid password setup session.', category='error')
        return redirect(url_for('index'))

    if datetime.utcnow() > expires_dt:
        session.clear()
        flash('Password setup session expired.', category='error')
        return redirect(url_for('index'))

    return render_template('initial_password.html')


@auth_api.route('/set_initial_password', methods=['POST'])
@limiter.limit("5 per hour")
def set_initial_password():
    local_id = session.get('initial_password_user_id')
    expires = session.get('initial_password_expires')

    if not local_id or not expires:
        return jsonify({'success': False, 'message': 'Invalid session.'}), 401

    try:
        expires_dt = datetime.fromisoformat(expires)
    except ValueError:
        session.clear()
        return jsonify({'success': False, 'message': 'Invalid session.'}), 401

    if datetime.utcnow() > expires_dt:
        session.clear()
        return jsonify({'success': False, 'message': 'Session expired.'}), 401

    data = request.get_json(silent=True) or {}
    new_password = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')

    if len(new_password) < MIN_PASSWORD_LENGTH:
        return jsonify({
            'success': False,
            'message': f'The password must have at least {MIN_PASSWORD_LENGTH} characters.'
        }), 400

    if new_password != confirm_password:
        return jsonify({
            'success': False,
            'message': 'The passwords do not match.'
        }), 400

    new_hash = ph.hash(new_password)

    conn = cursor = None

    try:
        conn = connect()
        cursor = conn.cursor()

        # Só deixa definir password inicial se ainda estiver NULL/vazia.
        cursor.execute("""
            UPDATE public.Users
            SET PasswordHash = %s,
                FailedAttempts = 0,
                LockedUntil = NULL,
                UpdatedAt = %s
            WHERE Id = %s
              AND (PasswordHash IS NULL OR PasswordHash = '')
        """, (new_hash, datetime.utcnow(), local_id))

        if cursor.rowcount != 1:
            conn.rollback()
            session.clear()
            return jsonify({
                'success': False,
                'message': 'Password already set or user not found.'
            }), 400

        conn.commit()

    except Exception:
        logger.exception("Erro ao definir password inicial")

        if conn:
            conn.rollback()

        return jsonify({'success': False, 'message': 'Could not set password.'}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    session.clear()
    session['mfa_enroll_user_id'] = local_id
    session['mfa_enroll_expires'] = (
        datetime.utcnow() + timedelta(minutes=10)
    ).isoformat()
    session['needs_password_setup'] = False

    return jsonify({'success': True, 'redirect': url_for('mfa.mfa_enroll')})


@auth_api.route('/change_password', methods=['POST'])
@limiter.limit("10 per hour")
def change_password():
    local_user_id = session.get('local_user_id')
    if not local_user_id:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    data = request.get_json(silent=True) or {}
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')

    if len(new_password) < MIN_PASSWORD_LENGTH:
        return jsonify({
            'success': False,
            'message': f'The new password must have at least {MIN_PASSWORD_LENGTH} characters'
        }), 400

    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT PasswordHash FROM public.Users WHERE Id = %s", (local_user_id,))
    row = cursor.fetchone()

    if not row:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'User not found'}), 404

    if not row[0]:
        cursor.close()
        conn.close()
        return jsonify({
            'success': False,
            'message': 'Password is not set for this account'
        }), 400

    try:
        ph.verify(row[0], current_password)
    except (VerifyMismatchError, InvalidHash):
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'The current password is incorrect'}), 401

    new_hash = ph.hash(new_password)
    cursor.execute("UPDATE public.Users SET PasswordHash = %s WHERE Id = %s", (new_hash, local_user_id))
    conn.commit()
    cursor.close()
    conn.close()

    logger.info("Password alterada para local_user_id=%s", local_user_id)
    return jsonify({'success': True, 'message': 'Password changed successfully'})


@auth_api.route('/send_reset_link', methods=['POST'])
@limiter.limit("3 per hour")
def send_reset_link():
    username = request.form.get('username', '').strip()
    # Resposta genérica SEMPRE igual, exista ou não a conta -> evita enumeration.
    generic_message = 'If an account exists for that username, a reset link has been sent.'

    if not username:
        flash(generic_message, category='info')
        return redirect(url_for('index'))

    conn = connect()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT Id, Email
        FROM public.Users
        WHERE LOWER(Email) = LOWER(%s)
           OR LOWER(split_part(Email, '@', 1)) = LOWER(%s)
    """, (username, username))
    account = cursor.fetchone()

    if account and account[1]:
        token = secrets.token_urlsafe(32)
        expiration_time = datetime.utcnow() + timedelta(hours=2)
        cursor.execute("DELETE FROM public.Tokens WHERE OperatorId = %s", (account[0],))
        cursor.execute("""
            INSERT INTO public.Tokens (OperatorId, Token, DataExpiracao, CreatedAt)
            VALUES (%s, %s, %s, %s)
        """, (account[0], token, expiration_time, datetime.utcnow()))
        conn.commit()

        try:
            from flask_mail import Message
            mail = current_app.extensions['mail']
            reset_link = url_for('auth.reset_password', token=token, _external=True)
            msg = Message(subject='Password Reset Request', recipients=[account[1]])
            msg.html = build_reset_password_email(reset_link)
            mail.send(msg)
        except Exception:
            logger.exception("Falha ao enviar email de reset de password")

    cursor.close()
    conn.close()

    flash(generic_message, category='info')
    return redirect(url_for('index'))


@auth_api.route('/reset_password/<string:token>', methods=['GET', 'POST'])
def reset_password(token):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT OperatorId, DataExpiracao FROM public.Tokens WHERE Token = %s", (token,))
    token_record = cursor.fetchone()

    if not token_record or datetime.utcnow() > token_record[1]:
        cursor.close()
        conn.close()
        flash('Invalid or expired token. Please request a new reset link.', category='error')
        return redirect(url_for('index'))

    operator_id = token_record[0]

    if request.method == 'POST':
        new_password = request.form.get('newPassword', '')
        confirm_password = request.form.get('confirmPassword', '')

        if len(new_password) < MIN_PASSWORD_LENGTH:
            flash(f'The password must have at least {MIN_PASSWORD_LENGTH} characters.', category='error')
            cursor.close()
            conn.close()
            return render_template('reset_password.html', token=token)

        if new_password != confirm_password:
            flash('The passwords do not match.', category='error')
            cursor.close()
            conn.close()
            return render_template('reset_password.html', token=token)

        new_hash = ph.hash(new_password)
        cursor.execute("""
            UPDATE public.Users
            SET PasswordHash = %s, FailedAttempts = 0, LockedUntil = NULL
            WHERE Id = %s
        """, (new_hash, operator_id))
        cursor.execute("DELETE FROM public.Tokens WHERE Token = %s", (token,))
        conn.commit()
        cursor.close()
        conn.close()

        flash('Your password has been updated successfully. Please log in.', category='success')
        return redirect(url_for('index'))

    cursor.close()
    conn.close()
    return render_template('reset_password.html', token=token)


def build_reset_password_email(reset_link, emailsender='surveybw@borgwarner.com'):
    colors = {
        'primary': '#051729',
        'primary_light': '#113561',
        'accent': '#2EFAD9',
        'success': '#28a745',
        'danger': '#dc3545',
        'warning': '#ffc107',
        'light_bg': '#f8f9fc',
    }

    return f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Recuperação de Password</title>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&display=swap" rel="stylesheet">
</head>

<body style="margin:0; padding:0; background:{colors['light_bg']}; font-family:'Montserrat', Arial, sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:{colors['light_bg']};">
<tr>
<td align="center">

<table width="560" cellpadding="0" cellspacing="0"
       style="background:#fff; border-radius:8px; margin:32px 0; border:1px solid #e3e6f0;">

    <tr>
        <td style="padding:24px 32px 8px 32px;">
            <h2 style="color:{colors['primary_light']}; font-weight:700; margin:0;">
                SurveyBW
            </h2>
            <p style="color:{colors['primary']}; margin:5px 0 0 0;">
                Recuperação de Password
            </p>
        </td>
    </tr>

    <tr>
        <td style="background:{colors['primary_light']}; padding:14px 32px;">
            <h3 style="margin:0; color:white;">
                Pedido de Recuperação de Password
            </h3>
        </td>
    </tr>

    <tr>
        <td style="padding:28px 32px;">
            <p style="color:{colors['primary']}; margin:0 0 12px 0;">
                Olá,
            </p>

            <p style="color:#444; margin:0 0 20px 0;">
                Recebemos um pedido para redefinir a password da sua conta na aplicação
                de SurveyBW. Clique no botão abaixo para criar uma nova password.
            </p>

            <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                    <td align="center" style="padding:8px 0 24px 0;">
                        <a href="{reset_link}"
                           style="
                               display:inline-block;
                               background:{colors['primary_light']};
                               color:white;
                               text-decoration:none;
                               font-weight:700;
                               font-size:1rem;
                               padding:14px 36px;
                               border-radius:6px;
                               border-bottom:3px solid {colors['accent']};
                               letter-spacing:0.5px;">
                            Redefinir Password
                        </a>
                    </td>
                </tr>
            </table>

            <table width="100%" cellpadding="0" cellspacing="0"
                   style="background:#fff;
                          border:1px solid #e3e6f0;
                          border-left:4px solid {colors['accent']};
                          border-radius:4px;
                          margin-bottom:20px;">
                <tr>
                    <td style="padding:14px 16px; color:#444; font-size:0.9rem;">
                        <b style="color:{colors['primary']};">Link alternativo:</b><br>
                        <a href="{reset_link}"
                           style="color:{colors['primary_light']}; word-break:break-all; font-size:0.82rem;">
                            {reset_link}
                        </a>
                    </td>
                </tr>
            </table>

            <div style="
                padding:12px 16px;
                background:#fff8e1;
                border-left:4px solid {colors['warning']};
                border-radius:4px;
                font-size:0.88rem;
                color:#444;">
                Este link é válido por <b>2 horas</b>.
                Se não solicitou esta alteração, pode ignorar este e-mail — a sua password não será alterada.
            </div>
        </td>
    </tr>

    <tr>
        <td style="
            background:{colors['light_bg']};
            text-align:center;
            padding:16px 32px;
            border-top:1px solid #e3e6f0;
            color:#555;
            font-size:0.9rem;">

            Mensagem enviada por <b>{emailsender}</b>.<br>

            <span style="color:#999;">
                Por favor, não responda a este e-mail.
            </span>

            <br><br>

            <span style="color:#adb5bd; font-size:0.82rem;">
                © 2026 SurveyBW · Digital Transformation Viana.
            </span>
        </td>
    </tr>

</table>

</td>
</tr>
</table>
</body>
</html>
'''