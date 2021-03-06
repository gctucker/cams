# CAMS - libcams.py
#
# Copyright (C) 2009, 2010, 2011. 2012, 2013
# Guillaume Tucker <guillaume@mangoz.org>
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import csv
import datetime
import logging
from django.conf.urls import url as django_url
from django.core.urlresolvers import reverse
from django.http import HttpResponse

CAMS_VERSION = (0, 6)

# -----------------------------------------------------------------------------
# Main menu

class Menu(object):
    def __init__(self):
        self._items = []

    # ToDo: get the namespace from the urlpatterns?
    def add(self, urlpatterns=[], items=[], namespace=''):
        url_perms = dict()
        for url in urlpatterns:
            url_name = getattr(url, 'name', None)
            if url_name is None:
                continue
            try:
                cls = getattr(url, 'viewcls')
                perms = getattr(cls, 'perms')
            except AttributeError:
                perms = []
            url_perms[url_name] = perms
        for item in items:
            if not item.perms:
                item.perms = url_perms.get(item.url_name, [])
            if namespace:
                item.url_name = ':'.join([namespace, item.url_name])
            self._items.append(item)

    def get_user_items(self, user):
        for it in self._items:
            if it.user_authorised(user):
                yield it

    def set_current(self, url_name):
        for it in self._items:
            if it.url_name == url_name:
                it.current = True
            else:
                it.current = False

    class Item(object):
        def __init__(self, url_name, title='', perms=[]):
            self.url_name = url_name
            self._url = None
            if not title:
                self.title = url_name
            else:
                self.title = title
            self.perms = perms
            self.current = False

        def __str__(self):
            return ', '.join([self.url_name, self.title, str(self.perms)])

        @property
        def url(self):
            if self._url is None:
                self._url = reverse(self.url_name)
            return self._url

        def user_authorised(self, user):
            for p in self.perms:
                if not user.has_perm(p):
                    return False
            return True

    class StaffItem(Item):
        def __init__(self, url_name, title=''):
            super(Menu.StaffItem, self).__init__(url_name, title)

        def user_authorised(self, user):
            return user.is_staff


# -----------------------------------------------------------------------------
# CSV file response

class CSVFileResponse(object):
    def __init__(self, fields, **kwargs):
        self._resp = HttpResponse(mimetype='text/csv')
        self._csv = csv.writer(self._resp, **kwargs)
        self._csv.writerow(fields)

    def write(self, values):
        values_utf8 = []
        for v in values:
            values_utf8.append(v.encode('utf-8'))
        self._csv.writerow(values_utf8)

    def set_file_name(self, f):
        self._resp['Content-Disposition'] = \
            'attachement; filename=\"{:s}\"'.format(f)

    @property
    def response(self):
        return self._resp

# -----------------------------------------------------------------------------
# History

class HistoryLogger(object):
    def __init__(self, logger_name, plain_logger_name=None):
        self._logger = logging.getLogger(logger_name)
        if plain_logger_name:
            self._plain_logger = logging.getLogger(plain_logger_name)
        else:
            self._plain_logger = None

    def create(self, user, obj, fields):
        self._log(user, obj, 'CREATE', self._make_msg(obj, fields))

    def create_form(self, user, form, extra=[]):
        self.create(user, form.instance, form.fields.keys() + extra)

    def edit(self, user, obj, fields):
        self._log(user, obj, 'EDIT', self._make_msg(obj, fields))

    def edit_form(self, user, form, extra=[]):
        changed_data = form.changed_data + extra
        if changed_data:
            self.edit(user, form.instance, changed_data)

    def edit_changed(self, user, obj, form):
        changed_fields = list()
        for f in obj._meta.fields:
            if f.name in form.fields.keys():
                if getattr(obj, f.name) != getattr(form.instance, f.name):
                    changed_fields.append(f.name)
        if changed_fields:
            self.edit(user, form.instance, changed_fields)

    def delete(self, user, obj):
        self._log(user, obj, 'DELETE', '')

    def _make_msg(self, obj, fields):
        msg_str = []
        for it in fields:
            x = getattr(obj, '{}_str'.format(it), None)
            if not x:
                x = getattr(obj, it)
            pk = getattr(x, 'pk', None)
            if not pk:
                x = unicode(x).replace('\\', '\\\\').replace('\"', '\\\"')
                x = u'\"{}\"'.format(x)
            else:
                x = u':'.join([x.__class__.__name__, unicode(x.pk)])
            msg_str.append(u'{}: {}'.format(it, x))
        return u', '.join(msg_str)

    def _log(self, user, obj, action, msg):
        e = {'uid': user.id, 'action': action, 'otype': type(obj).__name__,
             'oid': obj.pk}
        self._logger.info(msg, extra=e)
        if self._plain_logger:
            plain_msg = u'{} {} [{}:{}] {}'. \
                format(user.username, action, e['otype'], e['oid'], msg)
            self._plain_logger.info(plain_msg)

    def unescape(self, txt):
        return txt.replace('\\\"', '\"').replace('\\\\', '\\')


class HistoryParser(object):
    cache = dict()

    def __init__(self, file_name, classes):
        self._file_name = file_name
        self._classes = classes
        self._data = list()
        self._f = None

    @property
    def data(self):
        return self._data

    def open(self):
        self._f = open(self._file_name, 'r')
        self._mtime = os.path.getmtime(self._file_name)
        cache_mtime, self._data, self._lines = \
            self.cache.setdefault(self._file_name, (None, list(), list()))
        if self._mtime != cache_mtime:
            self._data = list()
            self._lines = self._f.readlines()

    def close(self):
        self._f.close()
        self._f = None
        self.cache[self._file_name] = (self._mtime, self._data, self._lines)

    def __getitem__(self, i):
        if self._f is None:
            raise Exception('History log file not open')
        while len(self._data) < (i + 1):
            line = self._lines.pop(-1)
            if not line:
                raise IndexError
            pline = HistoryParser.Line(line)
            self._data.append(HistoryParser.Item \
                (datetime=self._parse_date_time(pline),
                 user=self._parse_obj(pline),
                 obj=self._parse_obj(pline),
                 action=pline.parse_block(),
                 args=pline.parse_args()))
        return self._data[i]

    def _parse_date_time(self, pline):
        block = pline.parse_block()
        date_ints = []
        for date_str in block.split(' '):
            date_ints += [int(x) for x in date_str.split('.')]
        return datetime.datetime(*date_ints)

    def _parse_obj(self, pline):
        block = pline.parse_block()
        obj_class, obj_pk = block.split(':')
        cls = self._classes.get(obj_class)
        if not cls:
            return None
        try:
            return cls.objects.get(pk=obj_pk)
        except cls.DoesNotExist:
            return None


    class Line(object):
        def __init__(self, line):
            self._line = line
            self._pos = 0

        def parse_block(self):
            start = self._line.find('[', self._pos)
            if start == -1:
                raise Exception("Failed to find block start")
            start += 1
            stop = self._line.find(']', start)
            if stop == -1:
                raise Exception("Failed to find block end")
            self._pos = stop + 1
            return self._line[start:stop]

        def parse_args(self):
            return self._line[self._pos:].strip()


    class Item(object):
        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)



# -----------------------------------------------------------------------------
# Helpers

def get_first_words(text, max_l=24):
    if len(text) <= max_l:
        return text

    i = 0
    j = 0

    while (i < max_l) and (j >= 0):
        i = j
        j = text.find(' ', i + 1, max_l)

    return text[:i] + '...'

def str2list(match, sep=' '):
    match = match.strip()
    words = match.split(sep)
    ret = []

    for word in words:
        word.strip()
        if word:
            ret.append(word)

    return ret

def get_time_string():
    now = datetime.datetime.today()
    return '{:d}-{:02d}-{:02d}_{:02d}:{:02d}:{:02d}'.format \
        (now.year, now.month, now.day, now.hour, now.minute, now.second)

# ToDo: that should really go away eventually
# (class methods in the models should be able to do that in a nicer way)
def get_obj_address(obj, sep=', '):
    addr = []
    if obj.line_1:
        addr.append(obj.line_1)
        if obj.line_2:
            addr.append(obj.line_2)
            if obj.line_3:
                addr.append(obj.line_3)
    if obj.town:
        addr.append(obj.town)
    if obj.postcode:
        addr.append(obj.postcode)
    return sep.join(addr)

def make_group_file_name (group, sx = ''):
    if group.board:
        board_str = '-%s' % group.board.name.replace (' ', '')
    else:
        board_str = ''

    return '%s%s%s_%s' % (group.name.replace (' ', '_'),
                          board_str, sx, get_time_string ())

def get_user_email(user):
    if user.email:
        return user.email
    try:
        return user.player.person.contact_set.exclude(email='')[0].email
    except IndexError:
        return None

def urlcls(regex, cls, **kw):
    url_obj = django_url(regex, cls.as_view(), **kw)
    url_obj.viewcls = cls
    return url_obj
