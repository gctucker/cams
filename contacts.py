from cams.models import Record, Contactable, Contact, Member

# -----------------------------------------------------------------------------
# contacts

class ExportContact (object):
    def __init__(self, person, ctype, org_name, contact):
        self.p = person
        self.ctype = ctype
        self.org_name = org_name
        self.c = contact

def iterate_group_contacts (group): # ToDo: move into group model ?
    contactables = group.members.filter (status = Record.ACTIVE)
    for it in iterate_group_p_contacts (contactables):
        yield it
    for it in iterate_group_o_contacts (contactables):
        yield it

def iterate_group_p_contacts (contactables):
    c_people = contactables.filter (type = Contactable.PERSON)
    c_people = c_people.order_by ('person__last_name')

    for it in c_people:
        org_name = ''
        c = Contact.objects.filter (obj = it)
        if c:
            c = c[0]
            ctype = 'person'
        else:
            member = Member.objects.filter (person = it)
            if member:
                member = member[0]
                org_name = member.organisation.name
                c = Contact.objects.filter (obj = member)
                if c:
                    c = c[0]
                    ctype = 'member'
                else:
                    c = Contact.objects.filter (obj = member.organisation)
                    if c:
                        c = c[0]
                        ctype = 'org'
        if c:
            yield ExportContact (it.person, ctype, org_name, c)

def iterate_group_o_contacts (contactables):
    c_orgs = contactables.filter (type = Contactable.ORGANISATION)
    c_orgs = c_orgs.order_by ('organisation__name')

    for it in c_orgs:
        c = Contact.objects.filter (obj = it)
        p = None
        if c:
            c = c[0]
            c_type = 'org'
        else:
            member = Member.objects.filter (organisation = it)
            if member:
                member = member[0]
                c = Contact.objects.filter (obj = member)
                if c:
                    p = member.person
                    c = c[0]
                    c_type = 'member'
                else:
                    c = Contact.objects.filter (obj = member.person)
                    if c:
                        p = member.person
                        c = c[0]
                        c_type = 'person'
        if c:
            yield ExportContact (p, c_type, it.organisation.name, c)
