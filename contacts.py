from cams.models import Record, Contactable, Contact, Member, Role

# -----------------------------------------------------------------------------
# contacts

class ExportContact (object):
    def __init__(self, person, ctype, org_name, contact):
        self.p = person
        self.ctype = ctype
        self.org_name = org_name
        self.c = contact

def iterate_group_contacts (group): # ToDo: move into group model ?
    roles = Role.objects.filter (group = group)
    roles = roles.filter (contactable__status = Record.ACTIVE)
    for it, role in iterate_group_p_contacts (roles):
        yield it, role
    for it, role in iterate_group_o_contacts (roles):
        yield it, role

def iterate_group_p_contacts (roles):
    roles_people = roles.filter (contactable__type = Contactable.PERSON)
    roles_people = roles_people.order_by ('contactable__person__last_name')

    for role in roles_people:
        it = role.contactable
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
            yield ExportContact (it.person, ctype, org_name, c), role

def iterate_group_o_contacts (roles):
    roles_orgs = roles.filter (contactable__type = Contactable.ORGANISATION)
    roles_orgs = roles_orgs.order_by ('contactable__organisation__name')

    for role in roles_orgs:
        it = role.contactable
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
            yield ExportContact (p, c_type, it.organisation.name, c), role
