import csv
import datetime
from django.conf.urls.defaults import url as django_url
from django.core.urlresolvers import reverse
from django.http import HttpResponse

CAMS_VERSION = (0, 2, 0)

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
def get_obj_address(obj):
    address = ''

    if obj.line_1:
        address = obj.line_1
        if obj.line_2:
            address += ', ' + obj.line_2
            if obj.line_3:
                address += ', ' + obj.line_3

    if obj.town:
        if address:
            address += ', '
        address += obj.town

    if obj.postcode:
        if address:
            address += ', '
        address += obj.postcode

    return address

def make_group_file_name (group, sx = ''):
    if group.fair:
        year_str = '-%d' % group.fair.date.year
    else:
        year_str = ''

    return '%s%s%s_%s' % (group.name.replace (' ', '_'),
                          year_str, sx, get_time_string ())

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
