# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2018 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Invenio module that adds userprofiles to the platform."""

from __future__ import absolute_import, print_function

from flask import Blueprint, current_app, flash, render_template, request
from flask_babelex import lazy_gettext as _
from flask_breadcrumbs import register_breadcrumb
from flask_login import current_user, login_required
from flask_menu import register_menu
from flask_security.confirmable import send_confirmation_instructions
from invenio_db import db

from .api import current_userprofile
from .forms import EmailProfileForm, ProfileForm, VerificationForm, \
    confirm_register_form_factory, register_form_factory
from .models import UserProfile
from .signals import after_profile_update

blueprint = Blueprint(
    'invenio_userprofiles',
    __name__,
    template_folder='templates',
)

blueprint_api_init = Blueprint(
    'invenio_userprofiles_api_init',
    __name__,
    template_folder='templates',
)

blueprint_ui_init = Blueprint(
    'invenio_userprofiles_ui_init',
    __name__,
)


def init_common(app):
    """Post initialization."""
    if app.config['USERPROFILES_EXTEND_SECURITY_FORMS']:
        security_ext = app.extensions['security']
        security_ext.confirm_register_form = confirm_register_form_factory(
            security_ext.confirm_register_form)
        security_ext.register_form = register_form_factory(
            security_ext.register_form)


@blueprint_ui_init.record_once
def init_ui(state):
    """Post initialization for UI application."""
    app = state.app
    init_common(app)

    # Register blueprint for templates
    app.register_blueprint(
        blueprint, url_prefix=app.config['USERPROFILES_PROFILE_URL'])


@blueprint_api_init.record_once
def init_api(state):
    """Post initialization for API application."""
    init_common(state.app)


@blueprint.app_template_filter()
def userprofile(value):
    """Retrieve user profile for a given user id."""
    return UserProfile.get_by_userid(int(value))


@blueprint.route('/', methods=['GET', 'POST'])
@login_required
@register_menu(
    blueprint, 'settings.profile',
    # NOTE: Menu item text (icon replaced by a user icon).
    _('%(icon)s Profile', icon='<i class="fa fa-user fa-fw"></i>'),
    order=0)
@register_breadcrumb(
    blueprint, 'breadcrumbs.settings.profile', _('Profile')
)
def profile():
    """View for editing a profile."""
    # Create forms
    verification_form = VerificationForm(formdata=None, prefix="verification")
    profile_form = profile_form_factory()

    # Process forms
    form = request.form.get('submit', None)
    if form == 'profile':
        handle_profile_form(profile_form)
    elif form == 'verification':
        handle_verification_form(verification_form)

    return render_template(
        current_app.config['USERPROFILES_PROFILE_TEMPLATE'],
        profile_form=profile_form,
        verification_form=verification_form,)


def profile_form_factory():
    """Create a profile form."""
    if current_app.config['USERPROFILES_EMAIL_ENABLED']:
        return EmailProfileForm(
            formdata=None,
            username=current_userprofile.username,
            last_name=current_userprofile.last_name,
            first_name=current_userprofile.first_name,
            birth_date=current_userprofile.birth_date,
            street=current_userprofile.street,
            postal_code=current_userprofile.postal_code,
            city=current_userprofile.city,
            phone=current_userprofile.phone,
            keep_history=current_userprofile.keep_history,
            email=current_user.email,
            email_repeat=current_user.email,
            prefix='profile', )
    else:
        return ProfileForm(
            formdata=None,
            obj=current_userprofile,
            prefix='profile', )


def handle_verification_form(form):
    """Handle email sending verification form."""
    form.process(formdata=request.form)

    if form.validate_on_submit():
        send_confirmation_instructions(current_user)
        # NOTE: Flash message.
        flash(_("Verification email sent."), category="success")


def handle_profile_form(form):
    """Handle profile update form."""
    form.process(formdata=request.form)
    if form.validate_on_submit():
        email_changed = False
        with db.session.begin_nested():
            # Update profile.
            current_userprofile.username = form.username.data
            current_userprofile.last_name=form.last_name.data,
            current_userprofile.first_name=form.first_name.data,
            current_userprofile.birth_date=form.birth_date.data,
            current_userprofile.street=form.street.data,
            current_userprofile.postal_code=form.postal_code.data,
            current_userprofile.city=form.city.data,
            current_userprofile.phone=form.phone.data,
            current_userprofile.keep_history=form.keep_history.data
            db.session.add(current_userprofile)

            # Update email
            if current_app.config['USERPROFILES_EMAIL_ENABLED'] and \
               form.email.data != current_user.email:
                current_user.email = form.email.data
                current_user.confirmed_at = None
                db.session.add(current_user)
                email_changed = True
        db.session.commit()

        if email_changed:
            send_confirmation_instructions(current_user)
            # NOTE: Flash message after successful update of profile.
            flash(_('Profile was updated. We have sent a verification '
                    'email to %(email)s. Please check it.',
                    email=current_user.email),
                  category='success')
        else:
            # NOTE: Flash message after successful update of profile.
            flash(_('Profile was updated.'), category='success')
        after_profile_update.send(
            current_app._get_current_object(),
            profile=current_userprofile
        )
