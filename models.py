# CAMS - models.py
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

from datetime import datetime, date
from django.db import models
from django.db.models import (CharField, TextField, EmailField, URLField,
                              IntegerField, BooleanField,
                              PositiveSmallIntegerField, DecimalField,
                              DateField, TimeField, DateTimeField,
                              ForeignKey, OneToOneField, ManyToManyField)
from django.db.models.query import Q
from django.contrib.auth.models import User
from libcams import get_first_words, get_obj_address

class Record(models.Model):
    NEW = 0
    ACTIVE = 1
    DISABLED = 2

    xstatus = ((NEW, 'new'), (ACTIVE, 'active'), (DISABLED, 'disabled'))

    status = PositiveSmallIntegerField(choices=xstatus, default=ACTIVE)
    created = DateTimeField(auto_now_add=True)

    @property
    def status_str(self):
        return Record.xstatus[self.status][1]

    class Meta(object):
        abstract = True


class PinBoard(models.Model):
    OPEN = 0
    LOCKED = 1

    xstatus = ((OPEN, 'open'), (LOCKED, 'locked'))

    status = PositiveSmallIntegerField(choices=xstatus, default=OPEN)
    name = CharField(max_length=128)
    description = TextField(blank=True)

    @property
    def status_str(self):
        return PinBoard.xstatus[self.status][1]

    def __unicode__(self):
        return self.name


class Pin(models.Model):
    board = ForeignKey(PinBoard, blank=True, null=True,
                       on_delete=models.SET_NULL) # ToDo: Really SET_NULL ?
    parent = ForeignKey('self', blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.board is None or self.board.status == PinBoard.OPEN:
            super(Pin, self).save(*args, **kwargs)
        else:
            raise Exception('Pin board not open')

    def format_pin_name(self, string):
        if self.board:
            return '{0} [{1}]'.format(string, self.board.name)
        else:
            return string

    # Entries must not be pinned down more than once on each board
    def is_on_board(self, board):
        if board == self.board:
            return True
        p = self.parent
        if p:
            return p.is_on_board(board)
        return False

    def get_versions(self):
        vlist = list()
        p = self
        while p is not None:
            vlist.append(p)
            p = p.parent
        del(vlist[0])
        p = self
        while p is not None:
            vlist.insert(0, p)
            res = p.__class__.objects.filter(parent=p)
            if len(res) > 0:
                p = res[0]
            else:
                p = None
        return vlist

    def get_current_version(self):
        return self.get_versions()[0]

    def get_version_for_board(self, board):
        for p in self.get_versions():
            if p.board == board:
                return p
        return None

    def pin_down(self, board):
        pinned = self.__class__.objects.get(pk=self.pk)
        pinned.pk = None
        pinned.board = board
        pinned.save()
        pinned._pin_down_deep_copy(self)
        self.parent = pinned
        self.save()
        return pinned

    def _pin_down_deep_copy(self, current):
        pass

    @classmethod
    def get_boards(cls):
        boards = set()
        for g in cls.objects.all():
            boards.add(g.board)
        return boards

    class Meta(object):
        abstract = True

# -----------------------------------------------------------------------------
# address book

class Contactable(Record):
    PERSON = 0
    ORGANISATION = 1
    MEMBER = 2

    xtype = ((PERSON, 'person'), (ORGANISATION, 'organisation'),
             (MEMBER, 'member'))

    # ToDo: rename to something else as `type' is a built-in function name
    type = PositiveSmallIntegerField(choices=xtype, editable=False)
    basic_name = CharField(max_length=255)

    def __unicode__(self):
        return self.subobj.__unicode__()

    def save(self, *args, **kwargs):
        self._update_basic_name();
        super(Contactable, self).save(*args, **kwargs)
        members = getattr(self, 'members_list', None)
        if members:
            for m in members.all():
                m.update_status()

    def _update_basic_name(self):
        self.basic_name = self.__unicode__()

    @property
    def current_groups(self):
        groups_str = ''
        if self.group_set:
            groups = self.group_set.filter(board__isnull=True)
            for g in groups:
                if groups_str:
                    groups_str += ', '
                groups_str += g.name

        return groups_str

    # ToDo: create special tag instead ?
    @property
    def contact(self):
        if self.contact_set.count():
            return self.contact_set.all()[0]
        else:
            return None

    @property
    def contacts(self):
        c = self.contact_set.all()
        if c.count() == 0:
            m = self.members_list.all()
            if m.count() > 0:
                c = m[0].contact_set.all()
        return c

    @property
    def type_str(self):
        return Contactable.xtype[self.type][1]

    @property
    def subobj(self):
        if self.type == Contactable.PERSON:
            return self.person
        elif self.type == Contactable.ORGANISATION:
            return self.organisation
        elif self.type == Contactable.MEMBER:
            return self.member

    @property
    def current_roles(self):
        roles = Role.objects.filter(contactable=self)
        roles = roles.filter(Q(group__board__isnull=True))
        return roles

    class Meta(object):
        db_table = 'cams_abook_contactable'
        ordering = ['basic_name']
        permissions = (
            ('abook_edit', "Can edit address book entries"),
            ('abook_add', "Can add address book entries"),
            ('abook_delete', "Can delete address book entries"),
        )


class Person(Contactable):
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

    xtitle = ((MR, 'Mr'), (MISS, 'Miss'), (MS, 'Ms'), (MRS, 'Mrs'), (DR, 'Dr'),
              (PROF, 'Prof'), (SIR, 'Sir'), (LORD, 'Lord'), (LADY, 'Lady'),
              (REV, 'Rev'))

    title = PositiveSmallIntegerField(choices=xtitle, blank=True, null=True)
    first_name = CharField(max_length=127)
    middle_name = CharField(max_length=31, blank=True)
    last_name = CharField(max_length=127)
    nickname = CharField(max_length=31, blank=True)
    alter = ManyToManyField('self', blank=True, null=True, help_text=
                            "People who can be contacted instead.")

    def __unicode__(self):
        name = self.first_name
        if self.middle_name:
            name += ' ' + self.middle_name
        return name + ' ' + self.last_name

    def save(self, *args, **kwargs):
        self.type = Contactable.PERSON
        super(Person, self).save(*args, **kwargs)

    @property
    def name_nn(self):
        name = self.__unicode__()
        if self.nickname:
            name += ' (' + self.nickname + ')'
        return name

    @property
    def title_str(self):
        if self.title is None:
            return ''
        return Person.xtitle[self.title][1]

    @property
    def members_list(self):
        return self.member_set

    class Meta(object):
        ordering = ['first_name', 'last_name']
        verbose_name_plural = 'people'
        db_table = 'cams_abook_person'


class Organisation(Contactable):
    name = CharField(max_length=127, unique=True)
    nickname = CharField(max_length=31, blank=True)
    members = ManyToManyField(Person, through='Member')

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.type = Contactable.ORGANISATION
        super(Organisation, self).save(*args, **kwargs)

    @property
    def name_nn(self):
        name = self.name
        if self.nickname:
            name += ' (' + self.nickname + ')'
        return name

    @property
    def members_list(self):
        return Member.objects.filter(organisation=self)

    class Meta(object):
        ordering = ['name']
        db_table = 'cams_abook_organisation'


class Member(Contactable):
    title = CharField(max_length=63, blank=True, help_text=
                      "Role of that person within the organisation.")
    organisation = ForeignKey('Organisation', related_name='member_org')
    person = ForeignKey(Person)

    def __unicode__(self):
        return u'{}, member of {}'.format(self.person.__unicode__(),
                                          self.organisation.__unicode__())

    def save(self, *args, **kwargs):
        self.type = Contactable.MEMBER
        super(Member, self).save(*args, **kwargs)

    def _update_basic_name(self):
        self.basic_name = self.person.basic_name

    def update_status(self):
        old_status = self.status
        if ((self.organisation.status == Record.NEW)
            or (self.person.status == Record.NEW)):
            self.status = Record.NEW
        elif ((self.organisation.status == Record.DISABLED)
            or (self.person.status == Record.DISABLED)):
            self.status = Record.DISABLED
        elif ((self.organisation.status == Record.ACTIVE)
              and (self.person.status == Record.ACTIVE)):
            self.status = Record.ACTIVE
        if self.status != old_status:
            self.save()

    @property
    def name_nn(self):
        return self.person.name_nn

    class Meta(object):
        unique_together = (('organisation', 'person'))
        db_table = 'cams_abook_member'


class Contact(Record):
    email_help_text = "A valid e-mail looks like myself@whatever.com"
    website_help_text = "A valid URL looks like http://site.com"

    obj = ForeignKey(Contactable, editable=False)
    line_1 = CharField(max_length=63, blank=True)
    line_2 = CharField(max_length=63, blank=True)
    line_3 = CharField(max_length=63, blank=True)
    town = CharField(max_length=63, blank=True)
    postcode = CharField(max_length=15, blank=True)
    country = CharField(max_length=63, blank=True)
    email = EmailField(blank=True, max_length=127, help_text =
                       email_help_text, verbose_name="E-mail")
    website = URLField(max_length=255, blank=True, help_text=website_help_text)
    telephone = CharField(max_length=127, blank=True)
    mobile = CharField(max_length=127, blank=True)
    fax = CharField(max_length=31, blank=True)
    addr_order = IntegerField("Order", blank=True, default=0, help_text=
                              "Order of the premises on Mill Road.")
    addr_suborder = IntegerField("Sub-order", blank=True, default=0,help_text=
                     "Order of the premises on side streets around Mill Road.")

    def __unicode__(self):
        contact = self.get_address()

        if not contact:
            if self.email:
                contact = self.email
            elif self.website:
                contact = self.website
            elif self.telephone:
                contact = str(self.telephone)
            elif self.mobile:
                contact = str(self.mobile)
            else:
                contact = '[empty contact]'

        return contact

    def get_address(self, *args):
        return get_obj_address(self, *args)

    class Meta(object):
        db_table = 'cams_abook_contact'

# -----------------------------------------------------------------------------
# management

# ToDo: call this a Project with a name instead of a date
class Fair(models.Model):
    date = DateField(unique=True)
    description = TextField(blank=True)
    current = BooleanField(help_text=
                           "There must be one and only one current fair.")

    def __unicode__(self):
        return str(self.date.year)

    @property
    def short_desc(self):
        return get_first_words(self.description)

    def save(self, *args, **kwargs):
        if self.current == True:
            super(Fair, self).save(*args, **kwargs)

            for f in Fair.objects.all():
                if f.current == True and f != self:
                    f.current = False
                    f.save()
        else:
            found = False

            for f in Fair.objects.all():
                if f.current == True and f != self:
                    found = True
                    break

            if found == False:
                self.current = True

            super(Fair, self).save(*args, **kwargs)

    @classmethod
    def get_current(cls):
        return cls.objects.filter(current=True)[0]

    class Meta(object):
        ordering = ['-date']


class Player(Record):
    person = OneToOneField(Person)
    user = OneToOneField(User)

    def __unicode__(self):
        return self.person.__unicode__()

    class Meta(object):
        ordering = ['person__first_name', 'person__last_name']


class Item(Record):
    # ToDo: remove fair, inherit Record, Pin
    name = CharField(max_length=63)
    description = TextField(blank=True)
    owner = ForeignKey(Person)
    fair = ForeignKey(Fair, blank=True, null=True)

    def __unicode__(self):
        return self.name

    class Meta(object):
        abstract = True


class Event(Item):
    master = ForeignKey('self', blank=True, null=True,
                        help_text="Master event entry")
    team = ManyToManyField(Person, related_name='event_team', through='Actor')
    date = DateField()
    time = TimeField(blank=True, null=True, verbose_name="start time")
    end_date = DateField(blank=True, null=True)
    end_time = TimeField(blank=True, null=True)
    org = ForeignKey(Organisation, blank=True, null=True,
                     verbose_name="Organisation")
    location = CharField(max_length=63, blank=True,
                         help_text="Extra location indications")

    @property
    def date_time(self):
        if self.time:
            when = datetime(self.date.year, self.date.month, self.date.day,
                            self.time.hour, self.time.minute, self.time.second)
        else:
            when = date(self.date.year, self.date.month, self.date.day)

        return str(when)

    @property
    def main_id(self):
        if self.master:
            return self.master.pk
        return self.pk

    # ToDo: generalise and use as a principle for the pinboard feature
    # ToDo: support infinite recursion instead of just one master level ?
    @classmethod
    def get_for_fair(cls, event_id, fair):
        ev = cls.objects.filter(Q(pk=event_id) | Q(master=event_id))
        ev = ev.filter(fair=fair)
        if len(ev):
            return ev[0]
        return None

    class Meta(object):
        ordering = ['name']
        permissions = (
            ('programme_edit', "Can edit the programme"),
            ('programme_add', "Can add events to the programme"),
            ('programme_delete', "Can delete events from the programme"),
        )


class Actor(Record):
    person = ForeignKey(Person)
    event = ForeignKey(Event, related_name='event_actor')
    role = CharField(max_length=127, blank=True)

    def __unicode__(self):
        title = self.person.__unicode__()

        if self.role:
            title += ', ' + self.role

        return title + ' for ' + self.event.name

    @property
    def date(self):
        return self.event.date


class Group(Pin):
    name = CharField(max_length=31, blank=False, null=False)
    description = CharField(max_length=255, blank=True)
    members = ManyToManyField(Contactable, through='Role')

    def __unicode__(self):
        return self.format_pin_name(self.name)

    def _pin_down_deep_copy(self, current):
        for r in Role.objects.filter(group=current):
            r.pk = None
            r.group = self
            r.save()

    class Meta(object):
        ordering = ['name']
        permissions = (
            ('groups_edit', "Can edit groups"),
            ('groups_add', "Can add groups"),
            ('groups_delete', "Can delete groups"),
        )


class Role(models.Model):
    contactable = ForeignKey(Contactable)
    group = ForeignKey(Group)
    role = CharField(max_length=63, blank=True)

    def __unicode__(self):
        name = u' in '.join([self.contactable.__unicode__(),
                             self.group.__unicode__()])
        if self.role:
            name = u' as '.join([name, self.role])
        return name


class Comment(Record):
    author = ForeignKey(Player)
    text = TextField()

    def __unicode__(self):
        try:
            p = Player.objects.get(user=self.author)
            name = p.person.__unicode__()
        except Player.DoesNotExist:
            name = self.author.__unicode__()
        # ToDo: what about name ?
        return get_first_words(self.text)

    class Meta(object):
        abstract = True


class EventComment(Comment):
    event = ForeignKey(Event)


class Application(models.Model):
    PENDING = 0
    ACCEPTED = 1
    REJECTED = 2

    xstatus = ((PENDING, 'Pending'),
               (ACCEPTED, 'Accepted'),
               (REJECTED, 'Rejected'))

    person = ForeignKey(Person, related_name='appli_person')
    status = PositiveSmallIntegerField(choices=xstatus, default=PENDING)
    created = DateTimeField(auto_now_add=True)

    @property
    def status_str(self):
        return Application.xstatus[self.status][1]

    class Meta(object):
        abstract = True


class EventApplication(Application):
    event = ForeignKey(Event)

    def __unicode__(self):
        return u' for '.join([self.person.__unicode__(),
                              self.event.__unicode__()])


class Invoice(models.Model):
    NEW = 0
    SENT = 1
    PAID = 2
    CANCELLED = 3

    xstatus = ((NEW, 'New'), (SENT, 'Sent'), (PAID, 'Paid'),
               (CANCELLED, 'Cancelled'))

    status = PositiveSmallIntegerField(choices=xstatus, default=NEW)
    reference = CharField(max_length=63, blank=True)
    amount = DecimalField(max_digits=8, decimal_places=2)
    created = DateTimeField(auto_now_add=True)
    sent = DateTimeField(null=True, blank=True)
    paid = DateTimeField(null=True, blank=True)
    cancelled = DateTimeField(null=True, blank=True)

    stat_trans_dict = {
        NEW: [SENT, CANCELLED],
        SENT: [PAID, CANCELLED],
        PAID: [],
        CANCELLED: [],
        }

    @property
    def status_str(self):
        return Invoice.xstatus[self.status][1]

    @property
    def stat_trans(self):
        return self.stat_trans_dict[self.status]

    def update_status(self, new_status):
        if new_status not in self.stat_trans:
            raise Exception('invalid invoice status transition: {} -> {}'.
                            format(self.status, new_status))
        self.status = new_status
        now = datetime.now()
        if self.status == Invoice.SENT:
            self.sent = now
        elif self.status == Invoice.PAID:
            self.paid = now
        elif self.status == Invoice.CANCELLED:
            self.cancelled = now

    class Meta(object):
        abstract = True
        permissions = (
            ('invoices_view', "Can view invoices"),
            ('invoices_edit', "Can edit invoices"),
            ('invoices_add', "Can add invoices"),
            ('invoices_delete', "Can delete invoices"),
        )
