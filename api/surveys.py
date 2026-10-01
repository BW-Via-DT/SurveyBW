import hashlib
import json
import logging
import secrets
from datetime import datetime
from functools import wraps

from flask import (Blueprint, current_app, jsonify, redirect, render_template,
                    request, session, url_for)

from extensions import limiter
from utils.call_conn import connect
from utils.email_template import build_share_link_email

surveys_api = Blueprint("surveys", __name__)
logger = logging.getLogger("surveys")

VALID_FIELD_TYPES = {
    'text', 'textarea', 'number', 'date', 'email',
    'single_choice', 'multiple_choice', 'dropdown', 'rating'
}
CHOICE_FIELD_TYPES = {'single_choice', 'multiple_choice', 'dropdown'}
VALID_STATUSES = {'draft', 'published', 'closed'}

MAX_TITLE_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 4000
MAX_LABEL_LENGTH = 500
MAX_HELP_TEXT_LENGTH = 500
MAX_OPTION_LABEL_LENGTH = 300
MAX_FIELDS_PER_FORM = 100
MAX_OPTIONS_PER_FIELD = 50
MAX_SHARE_RESPONSES = 100000


def _client_ip():
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr or '')
    return ip_address.split(',')[0].strip()


def login_required(view):
    """Bloqueia o acesso a quem não tem sessão iniciada.
    Devolve JSON 401 para chamadas de API, redireciona páginas normais."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'local_user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Not authenticated'}), 401
            return redirect(url_for('index'))
        return view(*args, **kwargs)
    return wrapped


# ============================================================
# VALIDAÇÃO
# ============================================================

def _validate_form_payload(data, require_fields=True):
    """Devolve uma mensagem de erro (string) se o payload for inválido,
    ou None se estiver tudo bem."""
    title = (data.get('title') or '').strip()
    if not title:
        return 'O título do formulário é obrigatório.'
    if len(title) > MAX_TITLE_LENGTH:
        return f'O título não pode exceder {MAX_TITLE_LENGTH} caracteres.'

    description = data.get('description') or ''
    if len(description) > MAX_DESCRIPTION_LENGTH:
        return f'A descrição não pode exceder {MAX_DESCRIPTION_LENGTH} caracteres.'

    status = data.get('status', 'draft')
    if status not in VALID_STATUSES:
        return 'Estado do formulário inválido.'

    if not require_fields:
        return None

    fields = data.get('fields', [])
    if not isinstance(fields, list) or len(fields) == 0:
        return 'O formulário precisa de ter pelo menos uma pergunta.'
    if len(fields) > MAX_FIELDS_PER_FORM:
        return f'Um formulário não pode ter mais de {MAX_FIELDS_PER_FORM} perguntas.'

    for field in fields:
        field_type = field.get('type')
        if field_type not in VALID_FIELD_TYPES:
            return f'Tipo de pergunta inválido: {field_type}'

        label = (field.get('label') or '').strip()
        if not label:
            return 'Todas as perguntas precisam de um enunciado.'
        if len(label) > MAX_LABEL_LENGTH:
            return f'O enunciado de uma pergunta não pode exceder {MAX_LABEL_LENGTH} caracteres.'

        help_text = field.get('help_text') or ''
        if len(help_text) > MAX_HELP_TEXT_LENGTH:
            return f'O texto de ajuda não pode exceder {MAX_HELP_TEXT_LENGTH} caracteres.'

        if field_type in CHOICE_FIELD_TYPES:
            options = field.get('options', [])
            if not isinstance(options, list) or len(options) < 2:
                return 'Perguntas de escolha precisam de pelo menos 2 opções.'
            if len(options) > MAX_OPTIONS_PER_FIELD:
                return f'Uma pergunta não pode ter mais de {MAX_OPTIONS_PER_FIELD} opções.'
            for opt in options:
                opt_label = (opt.get('label') or '').strip()
                if not opt_label:
                    return 'Todas as opções precisam de texto.'
                if len(opt_label) > MAX_OPTION_LABEL_LENGTH:
                    return f'Uma opção não pode exceder {MAX_OPTION_LABEL_LENGTH} caracteres.'

    return None


def _insert_fields(cursor, form_id, fields):
    for order, field in enumerate(fields):
        cursor.execute("""
            INSERT INTO public.FormFields
                (FormId, FieldOrder, FieldType, Label, HelpText, IsRequired, CreatedAt)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING Id
        """, (
            form_id, order, field['type'], field['label'].strip(),
            (field.get('help_text') or '').strip() or None,
            bool(field.get('required', False)), datetime.utcnow()
        ))
        field_id = cursor.fetchone()[0]

        if field['type'] in CHOICE_FIELD_TYPES:
            for opt_order, opt in enumerate(field.get('options', [])):
                cursor.execute("""
                    INSERT INTO public.FormFieldOptions (FieldId, OptionOrder, OptionLabel)
                    VALUES (%s, %s, %s)
                """, (field_id, opt_order, opt['label'].strip()))


def _get_form_row(cursor, form_id):
    cursor.execute("""
        SELECT Id, OwnerUserId, Title, Description, Status, IsAnonymous,
               AllowMultipleResponses, ClosesAt, CreatedAt, UpdatedAt
        FROM public.Forms
        WHERE Id = %s
    """, (form_id,))
    return cursor.fetchone()


def _response_count(cursor, form_id):
    cursor.execute(
        "SELECT COUNT(*) FROM public.FormResponses WHERE FormId = %s",
        (form_id,)
    )
    return cursor.fetchone()[0]


def _can_access(form_row):
    if form_row is None:
        return False
    return form_row.OwnerUserId == session.get('local_user_id') or session.get('is_admin')


def _audit(cursor, form_id, user_id, action, details=None):
    cursor.execute("""
        INSERT INTO public.FormAuditLog (FormId, UserId, Action, Details, IpAddress, CreatedAt)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (form_id, user_id, action, json.dumps(details) if details else None,
          _client_ip(), datetime.utcnow()))


# ============================================================
# API — LISTAGEM
# ============================================================

@surveys_api.route('/api/surveys', methods=['GET'])
@login_required
def api_list_forms():
    user_id = session['local_user_id']
    is_admin = session.get('is_admin')
    show_all = is_admin and request.args.get('all') == '1'

    conn = connect()
    cursor = conn.cursor()
    try:
        query = """
            SELECT f.Id, f.Title, f.Status, f.CreatedAt, f.UpdatedAt,
                   (SELECT COUNT(*) FROM public.FormResponses r WHERE r.FormId = f.Id) AS ResponseCount
            FROM public.Forms f
        """
        if show_all:
            cursor.execute(query + " ORDER BY f.CreatedAt DESC")
        else:
            cursor.execute(query + " WHERE f.OwnerUserId = %s ORDER BY f.CreatedAt DESC", (user_id,))

        forms = [{
            'id': row.Id,
            'nome': row.Title,
            'status': row.Status,
            'data_criacao': row.CreatedAt.strftime('%Y-%m-%d %H:%M') if row.CreatedAt else None,
            'ultima_atualizacao': row.UpdatedAt.strftime('%Y-%m-%d %H:%M') if row.UpdatedAt else None,
            'respostas': row.ResponseCount,
        } for row in cursor.fetchall()]

        return jsonify(forms)
    except Exception:
        logger.exception("Erro ao listar formulários (user_id=%s)", user_id)
        return jsonify({'success': False, 'message': 'Não foi possível carregar os formulários.'}), 500
    finally:
        cursor.close()
        conn.close()


# ============================================================
# API — CRIAR
# ============================================================

@surveys_api.route('/api/surveys', methods=['POST'])
@login_required
@limiter.limit("30 per hour")
def api_create_form():
    data = request.get_json(silent=True) or {}
    error = _validate_form_payload(data, require_fields=True)
    if error:
        return jsonify({'success': False, 'message': error}), 400

    user_id = session['local_user_id']
    conn = connect()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO public.Forms
                (OwnerUserId, Title, Description, Status, IsAnonymous,
                 AllowMultipleResponses, ClosesAt, CreatedAt)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING Id
        """, (
            user_id, data['title'].strip(), (data.get('description') or '').strip() or None,
            data.get('status', 'draft'), True,
            bool(data.get('allow_multiple_responses', False)),
            data.get('closes_at') or None, datetime.utcnow()
        ))
        form_id = cursor.fetchone()[0]

        _insert_fields(cursor, form_id, data['fields'])
        _audit(cursor, form_id, user_id, 'created', {'title': data['title'].strip()})

        conn.commit()
        return jsonify({'success': True, 'id': form_id}), 201
    except Exception:
        conn.rollback()
        logger.exception("Erro ao criar formulário (user_id=%s)", user_id)
        return jsonify({'success': False, 'message': 'Ocorreu um erro ao criar o formulário.'}), 500
    finally:
        cursor.close()
        conn.close()


# ============================================================
# API — OBTER UM FORMULÁRIO (para a página de edição)
# ============================================================

@surveys_api.route('/api/surveys/<int:form_id>', methods=['GET'])
@login_required
def api_get_form(form_id):
    conn = connect()
    cursor = conn.cursor()
    try:
        form_row = _get_form_row(cursor, form_id)
        if form_row is None:
            return jsonify({'success': False, 'message': 'Formulário não encontrado.'}), 404
        if not _can_access(form_row):
            return jsonify({'success': False, 'message': 'Sem permissão para aceder a este formulário.'}), 403

        cursor.execute("""
            SELECT Id, FieldOrder, FieldType, Label, HelpText, IsRequired
            FROM public.FormFields
            WHERE FormId = %s
            ORDER BY FieldOrder
        """, (form_id,))
        field_rows = cursor.fetchall()

        fields = []
        for fr in field_rows:
            options = []
            if fr.FieldType in CHOICE_FIELD_TYPES:
                cursor.execute("""
                    SELECT Id, OptionOrder, OptionLabel
                    FROM public.FormFieldOptions
                    WHERE FieldId = %s
                    ORDER BY OptionOrder
                """, (fr.Id,))
                options = [{'id': o.Id, 'label': o.OptionLabel} for o in cursor.fetchall()]

            fields.append({
                'id': fr.Id, 'type': fr.FieldType, 'label': fr.Label,
                'help_text': fr.HelpText, 'required': bool(fr.IsRequired),
                'options': options,
            })

        return jsonify({
            'id': form_row.Id,
            'title': form_row.Title,
            'description': form_row.Description,
            'status': form_row.Status,
            'is_anonymous': bool(form_row.IsAnonymous),
            'allow_multiple_responses': bool(form_row.AllowMultipleResponses),
            'closes_at': form_row.ClosesAt.isoformat() if form_row.ClosesAt else None,
            'response_count': _response_count(cursor, form_id),
            'fields': fields,
        })
    except Exception:
        logger.exception("Erro ao obter formulário %s", form_id)
        return jsonify({'success': False, 'message': 'Ocorreu um erro ao carregar o formulário.'}), 500
    finally:
        cursor.close()
        conn.close()


@surveys_api.route('/api/surveys/<int:form_id>/responses', methods=['GET'])
@login_required
def api_list_form_responses(form_id):
    conn = connect()
    cursor = conn.cursor()
    try:
        form_row = _get_form_row(cursor, form_id)
        if form_row is None:
            return jsonify({'success': False, 'message': 'Formulário não encontrado.'}), 404
        if not _can_access(form_row):
            return jsonify({'success': False, 'message': 'Sem permissão para ver as respostas.'}), 403

        cursor.execute("""
            SELECT Id, RespondentEmail, SubmittedAt
            FROM public.FormResponses
            WHERE FormId = %s
            ORDER BY SubmittedAt DESC, Id DESC
        """, (form_id,))
        response_rows = cursor.fetchall()

        cursor.execute("""
            SELECT Id, FieldOrder, FieldType, Label
            FROM public.FormFields
            WHERE FormId = %s
            ORDER BY FieldOrder
        """, (form_id,))
        field_rows = cursor.fetchall()
        fields_by_id = {
            field.Id: {
                'id': field.Id,
                'label': field.Label,
                'type': field.FieldType,
                'order': field.FieldOrder,
            }
            for field in field_rows
        }

        responses = []
        for response in response_rows:
            cursor.execute("""
                SELECT a.Id, a.FieldId, a.AnswerText, o.OptionLabel
                FROM public.FormResponseAnswers a
                LEFT JOIN public.FormResponseAnswerOptions ao
                    ON ao.ResponseAnswerId = a.Id
                LEFT JOIN public.FormFieldOptions o
                    ON o.Id = ao.OptionId
                WHERE a.ResponseId = %s
                ORDER BY a.Id, o.OptionOrder
            """, (response.Id,))

            answers_by_field = {}
            for answer in cursor.fetchall():
                if answer.FieldId not in fields_by_id:
                    continue
                item = answers_by_field.setdefault(answer.FieldId, {
                    'field_id': answer.FieldId,
                    'value': answer.AnswerText or '',
                    'options': [],
                })
                if answer.OptionLabel:
                    item['options'].append(answer.OptionLabel)

            answers = []
            for field in fields_by_id.values():
                answer = answers_by_field.get(field['id'], {
                    'field_id': field['id'],
                    'value': '',
                    'options': [],
                })
                answers.append({
                    'field_id': field['id'],
                    'label': field['label'],
                    'type': field['type'],
                    'value': ', '.join(answer['options']) if answer['options'] else answer['value'],
                })

            responses.append({
                'id': response.Id,
                'respondent': response.RespondentEmail or 'Resposta anónima',
                'submitted_at': response.SubmittedAt.strftime('%Y-%m-%d %H:%M') if response.SubmittedAt else '',
                'answers': answers,
            })

        return jsonify({
            'success': True,
            'form': {'id': form_row.Id, 'title': form_row.Title},
            'total': len(responses),
            'responses': responses,
        })
    except Exception:
        logger.exception("Erro ao listar respostas do formulário %s", form_id)
        return jsonify({'success': False, 'message': 'Não foi possível carregar as respostas.'}), 500
    finally:
        cursor.close()
        conn.close()


# ============================================================
# API — ATUALIZAR
# ============================================================

@surveys_api.route('/api/surveys/<int:form_id>', methods=['PUT'])
@login_required
@limiter.limit("60 per hour")
def api_update_form(form_id):
    data = request.get_json(silent=True) or {}
    fields_provided = 'fields' in data
    error = _validate_form_payload(data, require_fields=fields_provided)
    if error:
        return jsonify({'success': False, 'message': error}), 400

    user_id = session['local_user_id']
    conn = connect()
    cursor = conn.cursor()
    try:
        form_row = _get_form_row(cursor, form_id)
        if form_row is None:
            return jsonify({'success': False, 'message': 'Formulário não encontrado.'}), 404
        if not _can_access(form_row):
            return jsonify({'success': False, 'message': 'Sem permissão para editar este formulário.'}), 403

        response_count = _response_count(cursor, form_id)
        if fields_provided and response_count > 0:
            return jsonify({
                'success': False,
                'message': 'Este formulário já tem respostas - não é possível alterar as perguntas. '
                            'Feche o formulário e crie uma nova versão, se precisar de o alterar.'
            }), 409

        cursor.execute("""
            UPDATE public.Forms
            SET Title = %s, Description = %s, Status = %s, IsAnonymous = %s,
                AllowMultipleResponses = %s, ClosesAt = %s, UpdatedAt = %s
            WHERE Id = %s
        """, (
            data['title'].strip(), (data.get('description') or '').strip() or None,
            data.get('status', form_row.Status), True,
            bool(data.get('allow_multiple_responses', form_row.AllowMultipleResponses)),
            data.get('closes_at') or None, datetime.utcnow(), form_id
        ))

        if fields_provided:
            # Sem respostas ainda -> seguro substituir a estrutura toda.
            # ON DELETE CASCADE em FormFieldOptions trata das opções sozinho.
            cursor.execute("DELETE FROM public.FormFields WHERE FormId = %s", (form_id,))
            _insert_fields(cursor, form_id, data['fields'])

        _audit(cursor, form_id, user_id, 'updated', {'fields_replaced': fields_provided})

        conn.commit()
        return jsonify({'success': True})
    except Exception:
        conn.rollback()
        logger.exception("Erro ao atualizar formulário %s", form_id)
        return jsonify({'success': False, 'message': 'Ocorreu um erro ao guardar o formulário.'}), 500
    finally:
        cursor.close()
        conn.close()


# ============================================================
# API — APAGAR
# ============================================================

@surveys_api.route('/api/surveys/<int:form_id>', methods=['DELETE'])
@login_required
@limiter.limit("20 per hour")
def api_delete_form(form_id):
    user_id = session['local_user_id']
    conn = connect()
    cursor = conn.cursor()
    try:
        form_row = _get_form_row(cursor, form_id)
        if form_row is None:
            return jsonify({'success': False, 'message': 'Formulário não encontrado.'}), 404
        if not _can_access(form_row):
            return jsonify({'success': False, 'message': 'Sem permissão para apagar este formulário.'}), 403

        if _response_count(cursor, form_id) > 0:
            return jsonify({
                'success': False,
                'message': 'Este formulário já tem respostas e não pode ser apagado. Feche-o em vez disso.'
            }), 409

        # FormAuditLog não tem ON DELETE CASCADE a partir de Forms (é histórico
        # de propósito) - por isso o registo de auditoria fica órfão de FormId
        # (NULL) em vez de ser apagado, preservando o rasto de quem fez o quê.
        cursor.execute(
            "UPDATE public.FormAuditLog SET FormId = NULL WHERE FormId = %s",
            (form_id,)
        )
        _audit(cursor, None, user_id, 'deleted', {'form_id': form_id, 'title': form_row.Title})
        cursor.execute("DELETE FROM public.Forms WHERE Id = %s", (form_id,))

        conn.commit()
        return jsonify({'success': True})
    except Exception:
        conn.rollback()
        logger.exception("Erro ao apagar formulário %s", form_id)
        return jsonify({'success': False, 'message': 'Ocorreu um erro ao apagar o formulário.'}), 500
    finally:
        cursor.close()
        conn.close()


# ============================================================
# PARTILHA — GERAR LINK
# ============================================================

@surveys_api.route('/api/surveys/<int:form_id>/share-links', methods=['GET'])
@login_required
def api_list_share_links(form_id):
    conn = connect()
    cursor = conn.cursor()
    try:
        form_row = _get_form_row(cursor, form_id)
        if form_row is None:
            return jsonify({'success': False, 'message': 'Formulário não encontrado.'}), 404
        if not _can_access(form_row):
            return jsonify({'success': False, 'message': 'Sem permissão.'}), 403

        cursor.execute("""
            SELECT Id, InvitedEmail, MaxResponses, ResponseCount, ExpiresAt, IsActive, CreatedAt
            FROM public.FormShareLinks
            WHERE FormId = %s
            ORDER BY CreatedAt DESC
        """, (form_id,))

        links = [{
            'id': row.Id,
            'invited_email': row.InvitedEmail,
            'max_responses': row.MaxResponses,
            'response_count': row.ResponseCount,
            'expires_at': row.ExpiresAt.isoformat() if row.ExpiresAt else None,
            'is_active': bool(row.IsActive),
            'created_at': row.CreatedAt.strftime('%Y-%m-%d %H:%M'),
        } for row in cursor.fetchall()]

        return jsonify(links)
    except Exception:
        logger.exception("Erro ao listar links de partilha do formulário %s", form_id)
        return jsonify({'success': False, 'message': 'Ocorreu um erro ao carregar os links.'}), 500
    finally:
        cursor.close()
        conn.close()


@surveys_api.route('/api/surveys/<int:form_id>/share-links', methods=['POST'])
@login_required
@limiter.limit("20 per hour")
def api_create_share_link(form_id):
    data = request.get_json(silent=True) or {}
    raw_emails = data.get('invited_emails', data.get('invited_email', '')) or ''
    if isinstance(raw_emails, list):
        email_values = raw_emails
    else:
        email_values = str(raw_emails).replace(';', ',').replace('\n', ',').split(',')
    invited_emails = []
    for email in email_values:
        normalized_email = str(email).strip().lower()
        if normalized_email and normalized_email not in invited_emails:
            invited_emails.append(normalized_email)

    if len(invited_emails) > 50:
        return jsonify({'success': False, 'message': 'Podes indicar no máximo 50 emails de cada vez.'}), 400
    if any('@' not in email or len(email) > 255 for email in invited_emails):
        return jsonify({'success': False, 'message': 'Um ou mais emails são inválidos.'}), 400

    max_responses = data.get('max_responses')
    expires_at_raw = data.get('expires_at') or None

    if max_responses is not None:
        try:
            max_responses = int(max_responses)
            if max_responses < 1 or max_responses > MAX_SHARE_RESPONSES:
                raise ValueError
        except (TypeError, ValueError):
            return jsonify({'success': False, 'message': 'Limite de respostas inválido.'}), 400

    expires_at = None
    if expires_at_raw:
        try:
            expires_at = datetime.fromisoformat(expires_at_raw)
        except ValueError:
            return jsonify({'success': False, 'message': 'Data de expiração inválida.'}), 400

        if expires_at <= datetime.now():
            return jsonify({'success': False, 'message': 'A data de expiração tem de ser no futuro.'}), 400

    user_id = session['local_user_id']
    conn = connect()
    cursor = conn.cursor()
    try:
        form_row = _get_form_row(cursor, form_id)
        if form_row is None:
            return jsonify({'success': False, 'message': 'Formulário não encontrado.'}), 404
        if not _can_access(form_row):
            return jsonify({'success': False, 'message': 'Sem permissão.'}), 403
        if form_row.Status != 'published':
            return jsonify({'success': False, 'message': 'Só é possível partilhar formulários publicados.'}), 409

        recipients = invited_emails or [None]
        generated_links = []
        for invited_email in recipients:
            token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(token.encode()).hexdigest()

            cursor.execute("""
                INSERT INTO public.FormShareLinks
                    (FormId, TokenHash, InvitedEmail, MaxResponses, ExpiresAt, IsActive, CreatedByUserId, CreatedAt)
                VALUES (%s, %s, %s, %s, %s, TRUE, %s, %s)
                RETURNING Id
            """, (form_id, token_hash, invited_email, max_responses, expires_at, user_id, datetime.utcnow()))
            link_id = cursor.fetchone()[0]
            generated_links.append({
                'id': link_id,
                'email': invited_email,
                'url': url_for('surveys.public_response_page', token=token, _external=True),
            })

        _audit(cursor, form_id, user_id, 'link_generated', {
            'recipient_count': len(invited_emails),
            'emails_sent': bool(invited_emails),
        })
        conn.commit()

        failed_emails = []
        if invited_emails:
            for link in generated_links:
                try:
                    from flask_mail import Message

                    message = Message(
                        subject=f'Convite para responder: {form_row.Title}',
                        recipients=[link['email']],
                    )
                    message.html = build_share_link_email(
                        form_title=form_row.Title,
                        share_url=link['url'],
                        expires_at=expires_at,
                        max_responses=max_responses,
                    )
                    current_app.extensions['mail'].send(message)
                except Exception:
                    failed_emails.append(link['email'])
                    logger.exception('Erro ao enviar convite para %s', link['email'])

            if failed_emails:
                return jsonify({
                    'success': True,
                    'message': f'Links criados, mas não foi possível enviar {len(failed_emails)} email(s).',
                    'sent_count': len(invited_emails) - len(failed_emails),
                    'failed_emails': failed_emails,
                }), 201

            return jsonify({
                'success': True,
                'message': f'Link enviado para {len(invited_emails)} destinatário(s).',
                'sent_count': len(invited_emails),
            }), 201

        return jsonify({
            'success': True,
            'id': generated_links[0]['id'],
            'share_url': generated_links[0]['url'],
            'message': 'Link geral criado.',
        }), 201
    except Exception:
        conn.rollback()
        logger.exception("Erro ao gerar link de partilha (form_id=%s)", form_id)
        return jsonify({'success': False, 'message': 'Ocorreu um erro ao gerar o link.'}), 500
    finally:
        cursor.close()
        conn.close()


@surveys_api.route('/api/surveys/share-links/<int:link_id>/revoke', methods=['POST'])
@login_required
def api_revoke_share_link(link_id):
    user_id = session['local_user_id']
    conn = connect()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT sl.Id, sl.FormId, f.OwnerUserId
            FROM public.FormShareLinks sl
            JOIN public.Forms f ON f.Id = sl.FormId
            WHERE sl.Id = %s
        """, (link_id,))
        row = cursor.fetchone()

        if row is None:
            return jsonify({'success': False, 'message': 'Link não encontrado.'}), 404
        if row.OwnerUserId != user_id and not session.get('is_admin'):
            return jsonify({'success': False, 'message': 'Sem permissão.'}), 403

        cursor.execute("UPDATE public.FormShareLinks SET IsActive = FALSE WHERE Id = %s", (link_id,))
        _audit(cursor, row.FormId, user_id, 'link_revoked', {'link_id': link_id})
        conn.commit()

        return jsonify({'success': True})
    except Exception:
        conn.rollback()
        logger.exception("Erro ao revogar link %s", link_id)
        return jsonify({'success': False, 'message': 'Ocorreu um erro ao revogar o link.'}), 500
    finally:
        cursor.close()
        conn.close()


# ============================================================
# PÁGINA PÚBLICA DE RESPOSTA (sem login)
# ============================================================

@surveys_api.route('/r/<string:token>', methods=['GET', 'POST'])
def public_response_page(token):
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    conn = connect()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT sl.Id, sl.FormId, sl.MaxResponses, sl.ResponseCount, sl.ExpiresAt, sl.IsActive,
                   f.Title, f.Description, f.Status, f.IsAnonymous
            FROM public.FormShareLinks sl
            JOIN public.Forms f ON f.Id = sl.FormId
            WHERE sl.TokenHash = %s
        """, (token_hash,))
        row = cursor.fetchone()

        invalid = (
            row is None
            or not row.IsActive
            or row.Status != 'published'
            or (row.ExpiresAt and row.ExpiresAt <= datetime.now())
            or (row.MaxResponses and row.ResponseCount >= row.MaxResponses)
        )

        if invalid:
            if request.method == 'POST':
                return jsonify({'success': False, 'message': 'Este formulário já não está disponível.'}), 410
            return render_template(
                'surveys/link_invalid.html',
                show_app_shell=False,
            ), 410

        cursor.execute("""
            SELECT Id, FieldOrder, FieldType, Label, HelpText, IsRequired
            FROM public.FormFields
            WHERE FormId = %s
            ORDER BY FieldOrder
        """, (row.FormId,))
        field_rows = cursor.fetchall()

        fields = []
        for fr in field_rows:
            options = []
            if fr.FieldType in CHOICE_FIELD_TYPES:
                cursor.execute("""
                    SELECT Id, OptionOrder, OptionLabel
                    FROM public.FormFieldOptions
                    WHERE FieldId = %s
                    ORDER BY OptionOrder
                """, (fr.Id,))
                options = [{'id': o.Id, 'label': o.OptionLabel} for o in cursor.fetchall()]

            fields.append({
                'id': fr.Id, 'type': fr.FieldType, 'label': fr.Label,
                'help_text': fr.HelpText, 'required': bool(fr.IsRequired),
                'options': options,
            })

        if request.method == 'POST':
            data = request.get_json(silent=True) or {}
            answers = data.get('answers')
            if not isinstance(answers, list):
                return jsonify({'success': False, 'message': 'Dados de resposta inválidos.'}), 400

            fields_by_id = {field['id']: field for field in fields}
            answers_by_field = {}
            for answer in answers:
                if not isinstance(answer, dict):
                    return jsonify({'success': False, 'message': 'Dados de resposta inválidos.'}), 400
                try:
                    field_id = int(answer.get('field_id'))
                except (TypeError, ValueError):
                    return jsonify({'success': False, 'message': 'Pergunta inválida.'}), 400
                if field_id not in fields_by_id or field_id in answers_by_field:
                    return jsonify({'success': False, 'message': 'Pergunta inválida.'}), 400
                answers_by_field[field_id] = answer.get('value')

            for field_id, field in fields_by_id.items():
                value = answers_by_field.get(field_id)
                if field['required'] and (value is None or value == '' or value == []):
                    return jsonify({'success': False, 'message': 'Preenche todos os campos obrigatórios.'}), 400

                if field['type'] in CHOICE_FIELD_TYPES and value not in (None, '', []):
                    values = value if isinstance(value, list) else [value]
                    valid_option_ids = {option['id'] for option in field['options']}
                    try:
                        option_ids = {int(option_id) for option_id in values}
                    except (TypeError, ValueError):
                        return jsonify({'success': False, 'message': 'Opção inválida.'}), 400
                    if not option_ids.issubset(valid_option_ids):
                        return jsonify({'success': False, 'message': 'Opção inválida.'}), 400
                    if field['type'] != 'multiple_choice' and len(option_ids) != 1:
                        return jsonify({'success': False, 'message': 'Resposta inválida.'}), 400

            cursor.execute("""
                INSERT INTO public.FormResponses
                    (FormId, ShareLinkId, RespondentEmail, IpAddress, UserAgent, SubmittedAt)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING Id
            """, (
                row.FormId, row.Id,
                session.get('email') or session.get('operator_number'),
                _client_ip(),
                request.headers.get('User-Agent', '')[:500], datetime.utcnow()
            ))
            response_id = cursor.fetchone()[0]

            for field_id, field in fields_by_id.items():
                value = answers_by_field.get(field_id)
                answer_text = None if field['type'] in CHOICE_FIELD_TYPES else (
                    '' if value is None else str(value)
                )
                cursor.execute("""
                    INSERT INTO public.FormResponseAnswers
                        (ResponseId, FieldId, AnswerText)
                    VALUES (%s, %s, %s)
                    RETURNING Id
                """, (response_id, field_id, answer_text))
                answer_id = cursor.fetchone()[0]

                if field['type'] in CHOICE_FIELD_TYPES and value not in (None, '', []):
                    for option_id in (value if isinstance(value, list) else [value]):
                        cursor.execute("""
                            INSERT INTO public.FormResponseAnswerOptions
                                (ResponseAnswerId, OptionId)
                            VALUES (%s, %s)
                        """, (answer_id, int(option_id)))

            cursor.execute("""
                UPDATE public.FormShareLinks
                SET ResponseCount = ResponseCount + 1
                WHERE Id = %s AND IsActive = TRUE
                  AND (MaxResponses IS NULL OR ResponseCount < MaxResponses)
            """, (row.Id,))
            if cursor.rowcount != 1:
                conn.rollback()
                return jsonify({'success': False, 'message': 'Este formulário já não está disponível.'}), 410

            conn.commit()
            return jsonify({'success': True}), 201

        return render_template(
            'surveys/respond.html',
            token=token,
            form_title=row.Title,
            form_description=row.Description,
            fields=fields,
            is_anonymous=bool(row.IsAnonymous),
            show_app_shell=False,
        )
    except Exception:
        conn.rollback()
        logger.exception("Erro ao carregar página pública de resposta (token hash não registado)")
        return render_template(
            'surveys/link_invalid.html',
            show_app_shell=False,
        ), 500
    finally:
        cursor.close()
        conn.close()