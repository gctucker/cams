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
    def __init__ (self, fields):
        self.resp = HttpResponse (mimetype = 'text/csv')
        self.csv = csv.writer (self.resp)
        self.csv.writerow (fields)

    def writerow (self, values):
        self.csv.writerow (values)

    def set_file_name (self, fname, append_timestamp = True):
        if append_timestamp:
            now = datetime.datetime.today ()
            f = '%s_%d-%02d-%02d:%02d-%02d-%02d.csv' % (fname,
                now.year, now.month, now.day, now.hour, now.minute, now.second)
        else:
            f = '%s.csv' % fname

        self.resp['Content-Disposition'] = 'attachement; filename=\"%s\"' % f
        return f

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
