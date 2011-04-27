import csv
import datetime
from django.http import HttpResponse

CAMS_VERSION = (0, 1, 0)

# -----------------------------------------------------------------------------
# Page system

class Page(object):
    COMMON = 0
    ADMIN = 1

    def __init__(self, name, url, title, group):
        self.name = name
        self.url = url
        self.title = title
        self.group = group

def filter_pages(page_list, group):
    filtered = []

    for p in page_list:
        if p.group == group:
            filtered.append(p)

    return filtered

def get_user_pages(page_list, user):
    if user.is_staff:
        return page_list
    else:
        return filter_pages(page_list, Page.COMMON)

# -----------------------------------------------------------------------------
# CSV file response

class CSVFileResponse(object):
    def __init__(self, fields, **kwargs):
        self._resp = HttpResponse(mimetype = 'text/csv')
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

    return text[:i] + "..."

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
    return '{:d}-{:02d}-{:02d}_{:02d}:{:02d}:{:2d}'.format \
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
