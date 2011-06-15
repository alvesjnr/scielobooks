# coding: utf-8

from pyramid.view import view_config
from pyramid.response import Response
from pyramid import exceptions
from pyramid.url import route_url, static_url
from pyramid.httpexceptions import HTTPFound
from pyramid.renderers import get_renderer
from pyramid.security import remember, forget
from pyramid.i18n import get_localizer
from pyramid.i18n import TranslationStringFactory
_ = TranslationStringFactory('scielobooks')

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound
from datetime import date

from forms import SignupForm, LoginForm
from ..models import users_models as users
from ..models import models

from Crypto.Hash import SHA256

import json
import deform
import colander

BASE_TEMPLATE = 'scielobooks:templates/base.pt'

def login(request):
    FORM_TITLE = 'Login'
    localizer = get_localizer(request)
    main = get_renderer(BASE_TEMPLATE).implementation()
    login_form = LoginForm.get_form(localizer)

    login_url = route_url('users.login', request)
    referrer = request.url
    if referrer == login_url:
        referrer = '/' # never use the login form itself as came_from
    came_from = request.params.get('came_from', referrer)

    if 'submit' in request.POST:
        
        controls = request.POST.items()
        try:
            appstruct = login_form.validate(controls)
        except deform.ValidationFailure, e:
            
            return {'content':e.render(), 
                    'main':main, 
                    'form_title':FORM_TITLE,
                    }
        try:
            user = request.rel_db_session.query(users.User).filter_by(username=appstruct['username']).one()
        except NoResultFound:
            request.session.flash(_("Username doesn't exist."))
        else:
            if SHA256.new(appstruct['password']).hexdigest() == user.password:
                headers = remember(request, user.id)
                return HTTPFound(location=came_from, headers=headers)
            else:
                request.session.flash(_("Username/password doesn't match")) 

    return {'main':main,
            'content':login_form.render(),
            'form_title':FORM_TITLE,
           }


def logout(request):
    headers = forget(request)
    return HTTPFound(location = route_url('general.login', request),
                     headers = headers)


def signup(request):
    localizer = get_localizer(request)
    main = get_renderer(BASE_TEMPLATE).implementation()
    publisher = request.rel_db_session.query(models.Publisher.name_slug, models.Publisher.name).all()
    signup_form = SignupForm.get_form(localizer,publisher)

    if 'submit' in request.POST:
                
        controls = request.POST.items()
        try:
            appstruct = signup_form.validate(controls)
        except deform.ValidationFailure, e:
            
            return {'content':e.render(), 
                    'main':main, 
                    'form_title':_('Signup'),
                    }

        del(appstruct['__LOCALE__'])

        appstruct['publisher'] = request.rel_db_session.query(models.Publisher).filter_by(name_slug=appstruct['publisher']).one()
        editor = users.Editor(**appstruct)
        request.rel_db_session.add(editor)

        try:
            request.rel_db_session.commit()
        except IntegrityError:
            request.rel_db_session.rollback()
            request.session.flash(_('This username already exists.'))
            return {'content':signup_form.render(appstruct),
                    'main':main,
                    'form_title':'Signup',
                    }
        request.session.flash(_('Successfully added.'))
        return HTTPFound(location=request.route_path('staff.panel'))

    return {'content':signup_form.render(),
            'form_title': _('Signup'),
            'main':main,
            }