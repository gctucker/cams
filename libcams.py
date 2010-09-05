class Page ():
    OPEN = 0
    ADMIN = 1

    def __init__ (self, name, url, title, group):
        self.name = name
        self.url = url
        self.title = title
        self.group = group

def filter_pages (group):
    filtered = []

    for p in PAGE_LIST:
        if p.group == group:
            filtered.append (p)

    return filtered

def get_user_pages (user):
    if user.is_staff:
        return PAGE_LIST
    else:
        return filter_pages (Page.OPEN)

# -----------------------------------------------------------------------------

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
