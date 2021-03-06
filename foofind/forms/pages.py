# -*- coding: utf-8 -*-
"""
    Formularios para las pages
"""
from flask import request
from wtforms import Form,BooleanField,PasswordField,TextField,TextAreaField,SelectField,FileField,FieldList,SubmitField,ValidationError
from flaskext.babel import lazy_gettext as _
from foofind.forms.captcha import CaptchaField
from foofind.forms.validators import *
from urlparse import urlparse

class ContactForm(Form):
    '''
    Formulario de contacto
    '''
    email = TextField(_('your_email'), [require(), email()])
    message = TextAreaField(_('your_message'), [require()])
    captcha = CaptchaField()
    accept_tos = BooleanField(validators=[require()])
    submit = SubmitField(_("submit"))

class JobsForm(Form):
    '''
    Formulario para enviar oferta de trabajo
    '''
    email = TextField(_('your_email'), [require(), email()])
    offer = TextField("Oferta", [require()])
    message = TextAreaField(_('your_message'), [require()])
    cv = FileField("Curriculum Vitae (opcional, extensiones permitidas: pdf, doc, odt, html, htm, txt, rtf o zip):")
    captcha = CaptchaField()
    accept_tos = BooleanField(validators=[require()])
    submit = SubmitField(_("submit"))

    def validate_cv(form, field):
        '''
        Validador de tipo de archivo
        '''
        if request.files[form.cv.name].filename:
            if re.match(r'^.*\.(pdf|doc|odt|html|htm|txt|rtf|zip)$',request.files[form.cv.name].filename):
                field.data = request.files[form.cv.name].filename
            else:
                raise ValidationError("El archivo tiene una extensión no permitida")

class SubmitLinkForm(Form):
    '''
    Formulario para añadir URLs
    '''
    urls = TextAreaField('URLs', [require()])
    accept_tos = BooleanField(validators=[require()])
    captcha = CaptchaField()
    submit = SubmitField(_("submit"))
    _permited_links = ["https:/","http://","magnet:","ed2k://"]

    def validate_urls(form, field):
        '''
        Validador de los enlaces
        '''
        for link in re.split(r'^.*\\n', form.urls.data):
            if link[:7] not in form._permited_links:
                raise ValidationError(_("no_valid_url"))

class ReportLinkForm(Form):
    '''
    Formulario para reportar enlaces
    '''
    name = TextField(_("your_name"), [require()])
    surname = TextField(_("your_surname"), [require()])
    company = TextField(_("your_company"))
    email = TextField(_("your_email"), [require(),email()])
    phonenumber = TextField(_("your_phone"))
    linkreported = TextField(_("link_reviewed"), [require(),url(),Regexp("^(?!https?://[^/]*foofind.[com|is]/?).*$",re.IGNORECASE,_("not_foofind_page"))])
    urlreported = TextField(_("url_content"), [require(),url(),Regexp("^https?://foofind.[com|is]/\w\w/download/[a-zA-Z0-9!-]{16}(/.*)?$",re.IGNORECASE,_("not_foofind_link"))])
    reason = TextField(_("reason_complaint"), [require()])
    message = TextAreaField(_('your_message'), [require()])
    captcha = CaptchaField()
    accept_tos = BooleanField(validators=[require()])
    submit = SubmitField(_("submit"))

    def validate_message(form, field):
        '''
        Validador de los enlaces
        '''
        if re.match(r'.*https?://[^/]*foofind.[com|is]/?.*',field.data,re.IGNORECASE):
            raise ValidationError(_("include_reported_links"))

class SelectLanguageForm(Form):
    '''
    Formulario para seleccionar idioma a traducir
    '''
    lang = SelectField(_("select_language"), default="")

class TranslateForm(Form):
    '''
    Formulario para traducir a un idioma
    '''
    captcha = CaptchaField()
    submit_form = SubmitField(_("submit"))
