from flask import Blueprint, redirect, render_template, url_for
from utils.auth_utils import is_authenticated

surveys_routes = Blueprint("surveys_routes", __name__)


@surveys_routes.route('/surveys')
def surveys_page():
    if not is_authenticated():
        return redirect(url_for('index'))
    return render_template('surveys/list.html', page_title='Formulários')


@surveys_routes.route('/surveys/new')
def new_survey_page():
    if not is_authenticated():
        return redirect(url_for('index'))
    return render_template('surveys/survey.html', page_title='Novo Formulário', form_id=None)


@surveys_routes.route('/surveys/<int:form_id>/update')
def update_survey_page(form_id):
    if not is_authenticated():
        return redirect(url_for('index'))
    return render_template('surveys/survey.html', page_title='Atualizar Formulário', form_id=form_id)


@surveys_routes.route('/surveys/<int:form_id>/responses')
def survey_responses_page(form_id):
    if not is_authenticated():
        return redirect(url_for('index'))
    return render_template('surveys/responses.html', page_title='Respostas', form_id=form_id)

