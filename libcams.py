import csv
import datetime
from django.http import HttpResponse

CAMS_VERSION = (0, 0, 0)

# -----------------------------------------------------------------------------
# Page system

class Page ():
    OPEN = 0
    ADMIN = 1

    def __init__ (self, name, url, title, group):
        self.name = name
        self.url = url
        self.title = title
        self.group = group

def filter_pages (page_list, group):
    filtered = []

    for p in page_list:
        if p.group == group:
            filtered.append (p)

    return filtered

def get_user_pages (page_list, user):
    if user.is_staff:
        return page_list
    else:
        return filter_pages (page_list, Page.OPEN)

# -----------------------------------------------------------------------------
# CSV file response

class CSVFileResponse:
    def __init__ (self, fields, **kwargs):
        self.resp = HttpResponse (mimetype = 'text/csv')
        self.csv = csv.writer (self.resp, **kwargs)
        self.csv.writerow (fields)

    def writerow (self, values):
        values_utf8 = []
        for v in values:
            values_utf8.append (v.encode ('utf-8'))
        self.csv.writerow (values_utf8)

    def set_file_name (self, f):
        self.resp['Content-Disposition'] = 'attachement; filename=\"%s\"' % f

    @property
    def response (self):
        return self.resp

# -----------------------------------------------------------------------------
# Helpers

def get_first_words (text, max_l = 24):
    if len (text) <= max_l:
        return text

    i = 0
    j = 0

    while (i < max_l) and (j >= 0):
        i = j
        j = text.find (' ', i + 1, max_l)

    return text[:i] + "..."

def str2list (match, sep = ' '):
    match = match.strip ()
    words = match.split (sep)
    ret = []

    for word in words:
        word.strip ()
        if word:
            ret.append (word)

    return ret

def get_time_string ():
    now = datetime.datetime.today ()
    return '%d-%02d-%02d_%02d:%02d:%02d' % \
        (now.year, now.month, now.day, now.hour, now.minute, now.second)

def get_obj_address (obj):
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
