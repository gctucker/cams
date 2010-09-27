from datetime import datetime, date
from django.db import models
from django.db.models import (CharField, TextField, EmailField, URLField,
                              IntegerField, PositiveIntegerField, BooleanField,
                              PositiveSmallIntegerField, DecimalField,
                              DateField, TimeField, DateTimeField,
                              ImageField,
                              ForeignKey, OneToOneField, ManyToManyField)
from django.db.models.query import Q
from django.contrib.auth.models import User
from libcams import get_first_words

def get_user_email (u):
    if u.email:
        return u.email
    else:
        player = Player.objects.get (user = u)
        p = player.person
        contacts = Contact.objects.filter (obj = p)
        for c in contacts:
            if c.email:
                return c.email
    return None

class Record (models.Model):
    NEW = 0
    ACTIVE = 1
    DISABLED = 2

    xstatus = ((NEW, 'new'), (ACTIVE, 'active'), (DISABLED, 'disabled'))

    status = PositiveSmallIntegerField (choices = xstatus, default = ACTIVE)
    created = DateTimeField (auto_now_add = True)

    def status_str (self):
        return Record.xstatus[self.status][1]

    class Meta:
        abstract = True


# -----------------------------------------------------------------------------
# address book

class Contactable (Record):
    PERSON = 0
    ORGANISATION = 1
    MEMBER = 2

    xtype = ((PERSON, 'person'), (ORGANISATION, 'organisation'),
             (MEMBER, 'member'))

    type = PositiveSmallIntegerField (choices = xtype, editable = False)

    # ToDo: create special tag instead ?
    @property
    def contact (self):
        if self.contact_set.count ():
            return self.contact_set.all ()[0]
        else:
            return None

    class Meta:
        db_table = 'cams_abook_contactable'


class Person (Contactable):
    MR = 0
    MISS = 1
    MS = 2
    MRS = 3
    DR = 4
    PROF = 5
    SIR = 6
    LORD = 7
    LADY = 8
    REV = 9

    titles = ((MR, 'Mr'), (MISS, 'Miss'), (MS, 'Ms'), (MRS, 'Mrs'), (DR, 'Dr'),
              (PROF, 'Prof'), (SIR, 'Sir'), (LORD, 'Lord'), (LADY, 'Lady'),
              (REV, 'Rev'))

    title = PositiveSmallIntegerField (choices = titles, blank = True,
                                       null = True)
    first_name = CharField (max_length = 127)
    middle_name = CharField (max_length = 31, blank = True)
    last_name = CharField (max_length = 127)
    nickname = CharField (max_length = 31, blank = True)
    alter = ManyToManyField ('self', blank = True, null = True, help_text =
                             "People who can be contacted instead.")

    def __unicode__ (self):
        name = self.first_name
        if self.middle_name:
            name += ' ' + self.middle_name
        if self.last_name:
            name += ' ' + self.last_name
        if self.nickname:
            name += ' (' + self.nickname + ')'
        return name

    def save (self, *args, **kwargs):
        self.type = Contactable.PERSON
        super (Contactable, self).save (args, kwargs)

    def title_str (self):
        if self.title != None:
            return Person.titles[self.title][1]
        else:
            return ''

#    ToDo: create a proxy model and add this in the 'extra' app
#    def get_absolute_url (self):
#        return URL_PREFIX + "abook/person/%i" % self.id

    def current_groups (self):
        groups_str = ''
        if self.group_set:
            groups = self.group_set.filter (Q (fair__current = True)
                                            | Q (fair__isnull = True))
            for g in groups:
                if groups_str:
                    groups_str += ', '
                groups_str += g.name

        return groups_str

    class Meta:
        ordering = ['first_name', 'last_name']
        verbose_name_plural = 'people'
        db_table = 'cams_abook_person'


class Organisation (Contactable):
    name = CharField (max_length = 127, unique = True)
    nickname = CharField (max_length = 31, blank = True)
    members = ManyToManyField (Person, through = 'Member')

    def __unicode__ (self):
        return self.name

    def save (self, *args, **kwargs):
        self.type = Contactable.ORGANISATION
        super (Contactable, self).save (args, kwargs)

#    def get_absolute_url (self):
#        return URL_PREFIX + "abook/org/%i" % self.id

    class Meta:
        ordering = ['name']
        db_table = 'cams_abook_organisation'


class Member (Contactable):
    title = CharField (max_length = 63, blank = True, help_text =
                       "Role of that person within the organisation.")
    organisation = ForeignKey ('Organisation', related_name = 'member_org')
    person = ForeignKey (Person)

    def __unicode__ (self):
        return (self.person.__unicode__ () + ", member of " +
                self.organisation.__unicode__ ())

    def save (self, *args, **kwargs):
        self.type = Contactable.MEMBER
        super (Contactable, self).save (args, kwargs)

    class Meta:
        unique_together = (('organisation', 'person'))
        db_table = 'cams_abook_member'


class Contact (Record):
    email_help_text = "A valid e-mail looks like myself@whatever.com"
    website_help_text = "A valid URL looks like http://site.com"

    obj = ForeignKey (Contactable, editable = False)
    line_1 = CharField (max_length = 63, blank = True)
    line_2 = CharField (max_length = 63, blank = True)
    line_3 = CharField (max_length = 63, blank = True)
    town = CharField (max_length = 63, blank = True)
    postcode = CharField (max_length = 15, blank = True)
    country = CharField (max_length = 63, blank = True)
    email = EmailField (blank = True, max_length = 127, help_text =
                        email_help_text, verbose_name = "E-mail")
    website = URLField (max_length = 255, verify_exists = False, blank = True,
                        help_text = website_help_text)
    telephone = CharField (max_length = 127, blank = True)
    mobile = CharField (max_length = 127, blank = True)
    fax = CharField (max_length = 31, blank = True)
    addr_order = IntegerField ("Order", blank = True, default = 0, help_text =
                               "Order of the premises on Mill Road.")
    addr_suborder = IntegerField ("Sub-order", blank = True, default = 0,
                                  help_text =
                     "Order of the premises on side streets around Mill Road.")

    def __unicode__ (self):
        contact = ''
        if self.line_1:
            contact = self.line_1
            if self.line_2:
                contact += ', ' + self.line_2
                if self.line_3:
                    contact += ', ' + self.line_3

        if self.town:
            if contact:
                contact += ', '
            contact += self.town
        elif self.postcode:
            if contact:
                contact += ', '
            contact += self.postcode

        if not contact:
            if self.email:
                contact = self.email
            elif self.website:
                contact = self.website
            elif self.telephone:
                contact = str (self.telephone)
            elif self.mobile:
                contact = str (self.mobile)
            else:
                contact = '[empty contact]'

        return contact

    class Meta:
        db_table = 'cams_abook_contact'

# -----------------------------------------------------------------------------
# management

# ToDo: call this a Project with a name instead of a date
class Fair (models.Model):
    date = DateField (unique = True)
    description = TextField (blank = True)
    current = BooleanField (help_text =
                            "There must be one and only one current fair.")

    def __unicode__ (self):
        return str (self.date.year)

    def short_desc (self):
        return get_first_words (self.description)

    def save (self, *args, **kwargs):
        if self.current == True:
            super (Fair, self).save (*args, **kwargs)

            for f in Fair.objects.all ():
                if f.current == True and f != self:
                    f.current = False
                    # ToDo: force save without test for uniqueness
                    # (add a keyword to the call)
                    f.save ()
        else:
            found = False

            for f in Fair.objects.all ():
                if f.current == True and f != self:
                    found = True
                    break

            if found == False:
                self.current = True

            super (Fair, self).save (*args, **kwargs)

    class Meta:
        ordering = ['-date']


class Player (Record):
    person = OneToOneField (Person)
    user = OneToOneField (User)

    def __unicode__ (self):
        return self.person.__unicode__ ()

    class Meta:
        ordering = ['person__first_name', 'person__last_name']


class Item (Record):
    name = CharField (max_length = 63)
    description = TextField (blank = True)
    owner = ForeignKey (Person)
    fair = ForeignKey (Fair, blank = True, null = True)

    def __unicode__ (self):
        return self.name

    class Meta:
        abstract = True


class Event (Item):
    team = ManyToManyField (Person, related_name = 'event_team',
                            through = 'Actor')
    date = DateField ()
    time = TimeField (blank = True, null = True, verbose_name = "start time")
    end_date = DateField (blank = True, null = True)
    end_time = TimeField (blank = True, null = True)
    org = ForeignKey (Organisation, blank = True, null = True,
                      verbose_name = "Organisation")
    location = CharField (max_length = 63, blank = True,
                          help_text = "Extra location indications")

    def date_time (self):
        if self.time:
            when = datetime (self.date.year, self.date.month, self.date.day,
                             self.time.hour, self.time.minute,
                             self.time.second)
        else:
            when = date (self.date.year, self.date.month, self.date.day)

        return str (when)


class Actor (Record):
    person = ForeignKey (Person)
    event = ForeignKey (Event, related_name = 'event_actor')
    role = CharField (max_length = 127, blank = True)

    def __unicode__ (self):
        title = self.person.__unicode__ ()

        if self.role:
            title += ', ' + self.role

        return title + ' for ' + self.event.name

    def date (self):
        return self.event.date


class Group (models.Model):
    name = CharField (max_length = 31, blank = False, null = False)
    fair = ForeignKey (Fair, blank = True, null = True)
    description = CharField (max_length = 255, blank = True)
    members = ManyToManyField (Person, through = 'Role')

    def __unicode__ (self):
        if self.fair:
            return "%s (%s)" % (self.name, self.fair.__unicode__ ())
        else:
            return self.name

    class Meta:
        unique_together = (('name', 'fair'), )
        ordering = ['name']


class Role (models.Model):
    person = ForeignKey (Person)
    group = ForeignKey (Group)
    role = CharField (max_length = 63, blank = True)

    def __unicode__ (self):
        return self.role


class Comment (Record):
    author = ForeignKey (Player)
    text = TextField ()

    def __unicode__ (self):
        try:
            p = Player.objects.get (user = self.author)
            name = p.person.__unicode__ ()
        except Player.DoesNotExist:
            name = self.author.__unicode__ ()

        return get_first_words (self.text)

    class Meta:
        abstract = True


class EventComment (Comment):
    event = ForeignKey (Event)


class Application (models.Model):
    PENDING = 0
    ACCEPTED = 1
    REJECTED = 2

    xstatus = ((PENDING, 'Pending'),
               (ACCEPTED, 'Accepted'),
               (REJECTED, 'Rejected'))

    person = ForeignKey (Person, related_name = 'appli_person')
    status = PositiveSmallIntegerField (choices = xstatus, default = PENDING)
    created = DateTimeField (auto_now_add = True)

    def status_str (self):
        return Application.xstatus[self.status][1]

    class Meta:
        abstract = True


class EventApplication (Application):
    event = ForeignKey (Event)

    def __unicode__ (self):
        return "%s for %s" % (self.person, self.event)
