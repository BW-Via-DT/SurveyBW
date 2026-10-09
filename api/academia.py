import logging
import os
import secrets
from datetime import datetime
from functools import wraps

from flask import Blueprint, jsonify, render_template, request

from extensions import limiter
from utils.call_conn import connect

surveys_fill = Blueprint("surveys_fill", __name__)
logger = logging.getLogger("surveys_fill")

CHOICE_FIELD_TYPES = {'single_choice', 'multiple_choice', 'dropdown'}
RATING_MAX = {'rating': 5, 'rating_4': 4, 'rating_5': 5}


def _client_ip():
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr or '')
    return ip_address.split(',')[0].strip()


def api_key_required(view=None, *, page=False):
    """Acesso por chave no header X-API-Key (para obter as respostas)."""
    if view is None:
        return lambda decorated_view: api_key_required(decorated_view, page=page)

    @wraps(view)
    def wrapped(*args, **kwargs):
        expected = os.environ.get('SECRET_KEY', '')
        provided = request.headers.get('X-API-Key') or request.args.get('api_key', '')
        if not expected or not secrets.compare_digest(provided, expected):
            logger.warning("Acesso negado (ip=%s)", _client_ip())
            if page:
                return render_template('surveys/link_invalid.html'), 401
            return jsonify({'success': False, 'message': 'Not authorized'}), 401
        return view(*args, **kwargs)
    return wrapped


def _load_form(cursor, form_id):
    """Devolve (form, fields) ou (None, None) se não existir / não estiver publicado."""
    cursor.execute(
        "SELECT id, title, description, status FROM public.forms WHERE id = %s",
        (form_id,))
    row = cursor.fetchone()
    if row is None or row[3] != 'published':
        return None, None

    cursor.execute("""
        SELECT id, fieldtype, section, label, helptext, isrequired
        FROM public.formfields
        WHERE formid = %s
        ORDER BY fieldorder
    """, (form_id,))
    fields = []
    for fid, ftype, section, label, helptext, required in cursor.fetchall():
        options = []
        if ftype in CHOICE_FIELD_TYPES:
            cursor.execute("""
                SELECT id, optionlabel FROM public.formfieldoptions
                WHERE fieldid = %s ORDER BY optionorder
            """, (fid,))
            options = [{'id': o[0], 'label': o[1]} for o in cursor.fetchall()]
        fields.append({
            'id': fid, 'type': ftype, 'section': section, 'label': label,
            'help_text': helptext, 'required': bool(required), 'options': options,
        })

    form = {'id': row[0], 'title': row[1], 'description': row[2]}
    return form, fields


# ============================================================
# PÁGINA  ->  /responder?form=1&number=150339&name=Ruben%20Morais
# ============================================================
@surveys_fill.route('/responder', methods=['GET'])
@api_key_required(page=True)
def respond_page():
    form_id = request.args.get('form', type=int)
    schedule_id = (request.args.get('Schedule_ID') or request.args.get('schedule_id') or '').strip()[:100]
    academia = (request.args.get('academia') or '').strip()[:200]
    number = (request.args.get('number') or '').strip()[:50]
    name = (request.args.get('name') or '').strip()[:200]
    api_key = request.headers.get('X-API-Key') or request.args.get('api_key', '')

    return render_template(
        'surveys/survey_academia.html',
        form_id=form_id,
        schedule_id=schedule_id,
        academia=academia,
        prefill_number=number,
        prefill_name=name,
        api_key=api_key,
        show_app_shell=False,
    )


# ============================================================
# API — IR BUSCAR AS PERGUNTAS
# ============================================================
@surveys_fill.route('/api/fill/<int:form_id>', methods=['GET'])
@api_key_required
def api_get_form(form_id):
    conn = connect()
    cursor = conn.cursor()
    try:
        form, fields = _load_form(cursor, form_id)
        if form is None:
            return jsonify({'success': False, 'message': 'Questionário não disponível.'}), 404
        return jsonify({'success': True, 'form': form, 'fields': fields})
    except Exception:
        logger.exception("Erro ao carregar formulário %s", form_id)
        return jsonify({'success': False, 'message': 'Erro ao carregar o questionário.'}), 500
    finally:
        cursor.close()
        conn.close()


# ============================================================
# API — RESPONDER
# ============================================================
@surveys_fill.route('/api/fill/<int:form_id>', methods=['POST'])
@api_key_required
@limiter.limit("60 per hour")
def api_submit_form(form_id):
    data = request.get_json(silent=True) or {}

    number = str(data.get('number') or '').strip()
    name = str(data.get('name') or '').strip()
    schedule_id = str(data.get('schedule_id') or '').strip()
    academia = str(data.get('academia') or '').strip()
    answers = data.get('answers')

    if not number or len(number) > 50:
        return jsonify({'success': False, 'message': 'Número inválido.'}), 400
    if not name or len(name) > 200:
        return jsonify({'success': False, 'message': 'Nome inválido.'}), 400
    if not schedule_id or len(schedule_id) > 100:
        return jsonify({'success': False, 'message': 'Schedule_ID inválido.'}), 400
    if not academia or len(academia) > 200:
        return jsonify({'success': False, 'message': 'Academia inválida.'}), 400
    if not isinstance(answers, list):
        return jsonify({'success': False, 'message': 'Dados de resposta inválidos.'}), 400

    conn = connect()
    cursor = conn.cursor()
    try:
        form, fields = _load_form(cursor, form_id)
        if form is None:
            return jsonify({'success': False, 'message': 'Questionário não disponível.'}), 410

        fields_by_id = {f['id']: f for f in fields}
        answers_by_field = {}
        for a in answers:
            if not isinstance(a, dict):
                return jsonify({'success': False, 'message': 'Dados de resposta inválidos.'}), 400
            try:
                fid = int(a.get('field_id'))
            except (TypeError, ValueError):
                return jsonify({'success': False, 'message': 'Pergunta inválida.'}), 400
            if fid not in fields_by_id or fid in answers_by_field:
                return jsonify({'success': False, 'message': 'Pergunta inválida.'}), 400
            answers_by_field[fid] = a.get('value')

        # Validação
        for fid, field in fields_by_id.items():
            value = answers_by_field.get(fid)
            empty = value is None or value == '' or value == []
            if field['required'] and empty:
                return jsonify({'success': False, 'message': 'Preenche todos os campos obrigatórios.'}), 400
            if empty:
                continue

            if field['type'] in CHOICE_FIELD_TYPES:
                values = value if isinstance(value, list) else [value]
                valid_ids = {o['id'] for o in field['options']}
                try:
                    ids = {int(v) for v in values}
                except (TypeError, ValueError):
                    return jsonify({'success': False, 'message': 'Opção inválida.'}), 400
                if not ids.issubset(valid_ids):
                    return jsonify({'success': False, 'message': 'Opção inválida.'}), 400
                if field['type'] != 'multiple_choice' and len(ids) != 1:
                    return jsonify({'success': False, 'message': 'Resposta inválida.'}), 400

            elif field['type'] in RATING_MAX:
                try:
                    n = int(value)
                except (TypeError, ValueError):
                    return jsonify({'success': False, 'message': 'Classificação inválida.'}), 400
                if n < 1 or n > RATING_MAX[field['type']]:
                    return jsonify({'success': False, 'message': 'Classificação inválida.'}), 400

        # Gravação
        cursor.execute("""
            INSERT INTO public.formresponses
                                (formid, scheduleid, academia, respondentnumber, respondentname,
                                 ipaddress, useragent, submittedat)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
          """, (form_id, schedule_id, academia, number, name, _client_ip(),
              request.headers.get('User-Agent', '')[:500], datetime.utcnow()))
        response_id = cursor.fetchone()[0]

        for fid, field in fields_by_id.items():
            value = answers_by_field.get(fid)
            is_choice = field['type'] in CHOICE_FIELD_TYPES
            answer_text = None if is_choice else ('' if value is None else str(value))

            cursor.execute("""
                INSERT INTO public.formresponseanswers (responseid, fieldid, answertext)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (response_id, fid, answer_text))
            answer_id = cursor.fetchone()[0]

            if is_choice and value not in (None, '', []):
                for option_id in (value if isinstance(value, list) else [value]):
                    cursor.execute("""
                        INSERT INTO public.formresponseansweroptions (responseanswerid, optionid)
                        VALUES (%s, %s)
                    """, (answer_id, int(option_id)))

        conn.commit()
        return jsonify({'success': True}), 201
    except Exception:
        conn.rollback()
        logger.exception("Erro ao gravar resposta (form_id=%s)", form_id)
        return jsonify({'success': False, 'message': 'Ocorreu um erro ao submeter.'}), 500
    finally:
        cursor.close()
        conn.close()


# ============================================================
# API — OBTER AS RESPOSTAS
#   /api/fill/responses?form_id=1&since=2026-09-01&until=2026-09-30&limit=100&offset=0
#   Header: X-API-Key
# ============================================================
@surveys_fill.route('/api/fill/responses', methods=['GET'])
@api_key_required
@limiter.limit("60 per hour")
def api_export_responses():
    form_id = request.args.get('form_id', type=int)
    number = (request.args.get('number') or '').strip() or None
    limit = min(max(request.args.get('limit', 100, type=int), 1), 1000)
    offset = max(request.args.get('offset', 0, type=int), 0)

    try:
        since = datetime.fromisoformat(request.args['since']) if request.args.get('since') else None
        until = datetime.fromisoformat(request.args['until']) if request.args.get('until') else None
    except ValueError:
        return jsonify({'success': False, 'message': 'Data inválida. Usa o formato AAAA-MM-DD.'}), 400

    where, params = [], []
    if form_id:
        where.append("r.formid = %s")
        params.append(form_id)
    if number:
        where.append("r.respondentnumber = %s")
        params.append(number)
    if since:
        where.append("r.submittedat >= %s")
        params.append(since)
    if until:
        where.append("r.submittedat <= %s")
        params.append(until)
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    conn = connect()
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT COUNT(*) FROM public.formresponses r {where_sql}", params)
        total = cursor.fetchone()[0]

        cursor.execute(f"""
            WITH page AS (
                SELECT r.id
                FROM public.formresponses r
                {where_sql}
                ORDER BY r.submittedat DESC, r.id DESC
                LIMIT %s OFFSET %s
            )
                 SELECT r.id, r.formid, f.title, r.scheduleid, r.academia,
                     r.respondentnumber, r.respondentname, r.submittedat,
                   ff.id, ff.section, ff.label, ff.fieldtype, a.answertext, o.optionlabel
            FROM page p
            JOIN public.formresponses r ON r.id = p.id
            JOIN public.forms f ON f.id = r.formid
            LEFT JOIN public.formresponseanswers a ON a.responseid = r.id
            LEFT JOIN public.formfields ff ON ff.id = a.fieldid
            LEFT JOIN public.formresponseansweroptions ao ON ao.responseanswerid = a.id
            LEFT JOIN public.formfieldoptions o ON o.id = ao.optionid
            ORDER BY r.submittedat DESC, r.id DESC, ff.fieldorder, o.optionorder
        """, params + [limit, offset])

        responses = {}
        for (resp_id, f_id, f_title, schedule_id, academia, r_number, r_name, submitted,
             field_id, section, label, ftype, answer_text, option_label) in cursor.fetchall():

            resp = responses.setdefault(resp_id, {
                'response_id': resp_id,
                'form_id': f_id,
                'form_title': f_title,
                'schedule_id': schedule_id,
                'academia': academia,
                'number': r_number,
                'name': r_name,
                'submitted_at': submitted.isoformat() if submitted else None,
                '_answers': {},
            })
            if field_id is None:
                continue

            ans = resp['_answers'].setdefault(field_id, {
                'field_id': field_id, 'section': section, 'label': label,
                'type': ftype, 'text': answer_text or '', 'options': [],
            })
            if option_label:
                ans['options'].append(option_label)

        result = []
        for resp in responses.values():
            answers = resp.pop('_answers')
            resp['answers'] = [{
                'field_id': a['field_id'],
                'section': a['section'],
                'label': a['label'],
                'type': a['type'],
                'value': ', '.join(a['options']) if a['options'] else a['text'],
            } for a in answers.values()]
            result.append(resp)

        return jsonify({
            'success': True, 'total': total, 'limit': limit,
            'offset': offset, 'count': len(result), 'responses': result,
        })
    except Exception:
        logger.exception("Erro na exportação de respostas")
        return jsonify({'success': False, 'message': 'Erro ao exportar respostas.'}), 500
    finally:
        cursor.close()
        conn.close()