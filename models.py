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

class Record (models.Model):
    status_choice = ((0, 'new'), (1, 'active'), (2, 'disabled'))
    status = PositiveSmallIntegerField (choices = status_choice, default = 1)
    created = DateTimeField (auto_now_add = True)

    class Meta:
        abstract = True


# -----------------------------------------------------------------------------
# address book

class Person (Record):
    titles = ((0, 'Mr'), (1, 'Miss'), (2, 'Ms'), (3, 'Mrs'), (4, 'Dr'),
              (5, 'Prof'), (6, 'Sir'), (7, 'Lord'), (8, 'Lady'), (9, 'Rev'))

    title = PositiveSmallIntegerField (choices = titles, blank = True,
                                       null = True)
    first_name = CharField (max_length = 127)
    middle_name = CharField (max_length = 31, blank = True)
    last_name = CharField (max_length = 127, blank = True)
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

#    ToDo: create a proxy model and add this in the 'extra' app
#    def get_absolute_url (self):
#        return URL_PREFIX + "abook/person/%i" % self.id

    class Meta:
        ordering = ['first_name']
        verbose_name_plural = 'people'


class Organisation (Record):
    name = CharField (max_length = 127, unique = True)
    nickname = CharField (max_length = 31, blank = True)
    members = ManyToManyField (Person, through = 'Member')

    def __unicode__ (self):
        return self.name

#    def get_absolute_url (self):
#        return URL_PREFIX + "abook/org/%i" % self.id

    class Meta:
        ordering = ['name']


class Member (Record):
    title = CharField (max_length = 63, blank = True, help_text =
                       "Role of that person within the organisation.")
    organisation = ForeignKey (Organisation)
    person = ForeignKey (Person)

    def __unicode__ (self):
        return (self.person.__unicode__ () + ", member of " +
                self.organisation.__unicode__ ())

    class Meta:
        unique_together = (('organisation', 'person'))


class Contact (Record):
    line_1 = CharField (max_length = 63, blank = True)
    line_2 = CharField (max_length = 63, blank = True)
    line_3 = CharField (max_length = 63, blank = True)
    town = CharField (max_length = 63, blank = True)
    postcode = CharField (max_length = 15, blank = True)
    country = CharField (max_length = 63, blank = True)
    email = EmailField (blank = True, max_length = 127)
    website = URLField (max_length = 255, verify_exists = False, blank = True)
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
            else:
                contact = str (self.id)

        return contact

    class Meta:
        abstract = True


class PersonContact (Contact):
    person = ForeignKey (Person)

    class Meta:
        db_table = 'cams_p_contact'


class OrganisationContact (Contact):
    org = ForeignKey (Organisation)

    class Meta:
        db_table = 'cams_o_contact'


class MemberContact (Contact):
    member = ForeignKey (Member)

    class Meta:
        db_table = 'cams_m_contact'

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


class Participant (Record):
    person = OneToOneField (Person, blank = False, null = False)
    user = OneToOneField (User, blank = True, null = True)

    def __unicode__ (self):
        return self.person.__unicode__ ()

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


class Item (Record):
    name = CharField (max_length = 63)
    description = TextField (blank = True)
    owner = ForeignKey (Participant)
    fair = ForeignKey (Fair, blank = True, null = True)

    def __unicode__ (self):
        return self.name

    class Meta:
        abstract = True


class Event (Item):
    team = ManyToManyField (Participant, related_name = 'event_team',
                            through = 'Actor')
    date = DateField ()
    time = TimeField (blank = True, null = True)
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
    participant = ForeignKey (Participant)
    event = ForeignKey (Event, related_name = 'event_actor')
    role = CharField (max_length = 127, blank = True)

    def __unicode__ (self):
        title = self.participant.person.__unicode__ ()

        if self.role:
            title += ', ' + self.role

        return title + ' for ' + self.event.name

    def date (self):
        return self.event.date


class Group (models.Model):
    name = CharField (max_length = 31, blank = False, null = False)
    fair = ForeignKey (Fair, blank = True, null = True)
    description = CharField (max_length = 255, blank = True)
    members = ManyToManyField (Participant, through = 'Role')

    def __unicode__ (self):
        if self.fair:
            return "%s (%s)" % (self.name, self.fair.__unicode__ ())
        else:
            return self.name

    class Meta:
        unique_together = (('name', 'fair'), )
        ordering = ['name']


class Role (models.Model):
    participant = ForeignKey (Participant)
    group = ForeignKey (Group)
    role = CharField (max_length = 63, blank = True)

    def __unicode__ (self):
        return self.role


class Comment (Record):
    author = ForeignKey (User)
    time = DateTimeField (auto_now = True)
    text = TextField ()

    def __unicode__ (self):
        try:
            p = Participant.objects.get (user = self.author)
            name = p.person.__unicode__ ()
        except Participant.DoesNotExist:
            name = self.author.__unicode__ ()

        return get_first_words (self.text)

    class Meta:
        abstract = True


class EventComment (Comment):
    event = ForeignKey (Event)


class ApplicationType (models.Model):
    name = CharField (max_length = 63)
    listeners = ManyToManyField (Participant, blank = True, related_name =
                                 "%(app_label)s_%(class)s_related")

    def __unicode__ (self):
        return self.name


class Application (models.Model):
    status_choices = ((0, 'Unread'), (1, 'Read'), (2, 'Accepted'),
                      (3, 'Rejected'))
    participant = ForeignKey (Participant, related_name = 'appli_part')
    atype = ForeignKey (ApplicationType, verbose_name = "Application type",
                        blank = True, null = True)
    status = PositiveSmallIntegerField (choices = status_choices, default = 0)
    created = DateTimeField (auto_now_add = True)

    class Meta:
        abstract = True


class EventApplication (Application):
    event = ForeignKey (Event)

    def __unicode__ (self):
        return "%s for %s" % (self.participant, self.event)
