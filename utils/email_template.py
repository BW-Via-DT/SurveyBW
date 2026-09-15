from markupsafe import escape


def build_share_link_email(form_title, share_url, emailsender='surveybw@borgwarner.com',
                            expires_at=None, max_responses=None):
    colors = {
        'primary': '#051729',
        'primary_light': '#113561',
        'accent': '#2EFAD9',
        'light_bg': '#f8f9fc',
    }

    # Linha(s) extra de info (expiração / limite de respostas), só se existirem
    info_linhas = []
    if expires_at:
        info_linhas.append(('Válido até', expires_at.strftime('%d/%m/%Y %H:%M')))
    if max_responses:
        info_linhas.append(('Limite de respostas', str(max_responses)))

    info_html = ""
    if info_linhas:
        linhas_html = "".join(f'''
            <tr>
                <td style="padding:10px 8px; border-bottom:1px solid #e3e6f0; color:#888; font-size:0.85rem; width:180px;">
                    {label}
                </td>
                <td style="padding:10px 8px; border-bottom:1px solid #e3e6f0; color:{colors['primary']}; font-weight:600;">
                    {valor}
                </td>
            </tr>
        ''' for label, valor in info_linhas)

        info_html = f'''
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="background:#fff;
                          border:1px solid #e3e6f0;
                          border-left:4px solid {colors['accent']};
                          border-radius:4px;
                          margin-top:12px;">
                <tbody>
                    {linhas_html}
                </tbody>
            </table>
        '''

    botao_html = f'''
        <div style="text-align:center; margin-top:24px;">
            <a href="{share_url}" style="
                background:{colors['primary_light']};
                color:#fff;
                text-decoration:none;
                padding:12px 32px;
                border-radius:6px;
                font-weight:700;
                display:inline-block;
                font-size:0.95rem;
                letter-spacing:0.3px;">
                Abrir Formulário →
            </a>
        </div>
    '''

    return f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Convite para Responder ao Formulário</title>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&display=swap" rel="stylesheet">
</head>
<body style="margin:0; padding:0; background:{colors['light_bg']}; font-family:'Montserrat', Arial, sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:{colors['light_bg']};">
<tr>
<td align="center">

<table width="600" cellpadding="0" cellspacing="0"
       style="background:#fff; border-radius:8px; margin:32px 0; border:1px solid #e3e6f0;">
    <tr>
        <td style="padding:24px 32px 8px 32px;">
            <h2 style="color:{colors['primary_light']}; font-weight:700; margin:0;">
                Convite para Responder
            </h2>
            <p style="color:{colors['primary']}; margin:5px 0 0 0;">
                Foi convidado a preencher um formulário
            </p>
        </td>
    </tr>

    <tr>
        <td style="background:{colors['primary_light']}; padding:14px 32px;">
            <h3 style="margin:0; color:white;">
                {escape(form_title)}
            </h3>
        </td>
    </tr>
    <tr>
        <td style="padding:24px 32px;">
            <p style="color:#444;">
                Foi convidado para responder ao formulário
                <b>{escape(form_title)}</b>. Clique no botão abaixo para começar.
            </p>

            {info_html}
            {botao_html}

            <p style="color:#888; font-size:0.85rem; margin-top:20px;">
                Se o botão não funcionar, copie e cole este endereço no seu navegador:<br>
                <a href="{share_url}" style="color:{colors['primary_light']};">{escape(share_url)}</a>
            </p>
        </td>
    </tr>
    <tr>
        <td style="
            background:{colors['light_bg']};
            text-align:center;
            padding:16px 32px;
            border-top:1px solid #e3e6f0;">

            Mensagem enviada por <b>{emailsender}</b>.<br>

            <span style="color:#999;">
                Por favor, não responda a este e-mail.
            </span>
            <br><br>
            <span style="color:#adb5bd; font-size:0.82rem;">
                © 2026 SurveyBW.
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