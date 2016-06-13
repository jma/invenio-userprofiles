# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015, 2016 CERN.
#
# Invenio is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""Database models for user profiles."""

from __future__ import absolute_import, print_function

from invenio_accounts.models import User
from invenio_db import db
from sqlalchemy import event
from sqlalchemy.ext.hybrid import hybrid_property

from .validators import validate_username


class AnonymousUserProfile():
    """Anonymous user profile."""

    @property
    def is_anonymous(self):
        """Return whether this UserProfile is anonymous."""
        return True


class UserProfile(db.Model):
    """UserProfile model.

    UserProfiles store information about account users.
    """

    __tablename__ = 'userprofiles_userprofile'

    user_id = db.Column(
        db.Integer,
        db.ForeignKey(User.id),
        primary_key=True
    )
    """Foreign key to user."""

    user = db.relationship(
        User, backref=db.backref(
            'profile', uselist=False, cascade='all, delete-orphan')
    )
    """User relationship."""

    _username = db.Column('username', db.String(255), unique=True)
    """Lower-case version of username to assert uniqueness."""

    _displayname = db.Column('displayname', db.String(255))
    """Case preserving version of username."""

    full_name = db.Column(db.String(255), nullable=False, default='')
    """Full name of person."""

    @hybrid_property
    def username(self):
        """Get username."""
        return self._displayname

    @username.setter
    def username(self, username):
        """Set username."""
        validate_username(username)
        self._username = username.lower()
        self._displayname = username

    @classmethod
    def get_by_username(cls, username):
        """Get profile by username."""
        return cls.query.filter(
            UserProfile._username == username.lower()
        ).one()

    @classmethod
    def get_by_userid(cls, user_id):
        """Get profile by username."""
        return cls.query.filter_by(user_id=user_id).one_or_none()

    @property
    def is_anonymous(self):
        """Return whether this UserProfile is anonymous."""
        return False


@event.listens_for(User, 'init')
def on_user_init(target, args, kwargs):
    """Hook into User initialization.

    Automagically convert a dict to a UserProfile instance. This is needed
    during e.g. user registration where Flask-Security will initialize a
    User model with all the form data (which when Invenio-UserProfiles is
    enabled includes a ``profile`` key). This will make the User creation fail
    unless we convert the profile dict into a UserProfile object.
    """
    if 'profile' in kwargs and not isinstance(kwargs['profile'], UserProfile):
        kwargs['profile'] = UserProfile(**kwargs['profile'])
