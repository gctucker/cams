from django.contrib import admin
from cams.models import (Person, Organisation, Member,
                         PersonContact, OrganisationContact, MemberContact,
                         Participant, Group, Actor, Event, Fair, Role,
                         Comment, EventComment, Application, EventApplication)

# -----------------------------------------------------------------------------
# address book

class ContactInline (admin.StackedInline):
    extra = 0
    fieldsets = [('Address',
                  {'fields': ('line_1', 'line_2', 'line_3',
                              ('town', 'postcode'))}),
                 ('Extra',
                  {'fields': (('telephone', 'mobile', 'fax'),
                              ('email', 'website'))}),
                 ('Order',
                  {'fields': (('addr_order', 'addr_suborder'), )})]


class PersonContactInline (ContactInline):
    model = PersonContact


class OrgContactInline (ContactInline):
    model = OrganisationContact


class MemberContactInline (ContactInline):
    model = MemberContact
    max_num = 1


class MemberInline (admin.TabularInline):
    model = Organisation.members.through
    fields = ['person', 'title']
    raw_id_fields = ['person']
    extra = 3


class RecordAdmin (admin.ModelAdmin):
    list_filter = ['status']
    date_hierarchy = 'created'
    list_display = ['created', 'status']


class PersonAdmin (RecordAdmin):
    list_per_page = 50
    search_fields = ['first_name', 'middle_name', 'last_name', 'nickname']
    list_display = ['first_name', 'last_name'] + RecordAdmin.list_display
    fieldsets = [(None,
                  {'fields': ('title',
                              ('first_name', 'last_name'),
                              ('middle_name', 'nickname'),
                              'status')}),
                 ('Friends and relatives',
                  {'classes': ('collapse', ),
                   'fields': ('alter', )})]
    radio_fields = {'title': admin.HORIZONTAL}
    filter_horizontal = ['alter']
    inlines = [PersonContactInline]


class OrganisationAdmin (RecordAdmin):
    list_display = ['name'] + RecordAdmin.list_display
    list_per_page = 50
    search_fields = ['name', 'nickname']
    fieldsets = [(None, {'fields': (('name', 'nickname'), 'status')})]
    inlines = [OrgContactInline, MemberInline]


class MemberAdmin (RecordAdmin):
    list_display = ['person', 'organisation', 'title'] \
                   + RecordAdmin.list_display
    ordering = ('person', )
    list_per_page = 50
    search_fields = ['person__first_name', 'person__middle_name',
                     'person__last_name', 'person__nickname',
                     'organisation__name', 'organisation__nickname']
    inlines = [MemberContactInline]
    raw_id_fields = ['person', 'organisation']

# -----------------------------------------------------------------------------
# management

class GroupInline (admin.TabularInline):
    model = Group
    extra = 3


class RoleInline (admin.TabularInline):
    model = Role
    raw_id_fields = ['group']


class GroupAdmin (admin.ModelAdmin):
    list_display = ['__unicode__', 'description']
    search_fields = ['name', 'fair__date']
    list_filter = ['fair']


class FairAdmin (admin.ModelAdmin):
    list_display = ['date', 'description', 'current']
    ordering = ('-date', )


class ParticipantAdmin (RecordAdmin):
    search_fields = ['person__first_name', 'person__middle_name',
                     'person__last_name', 'person__nickname']
    list_display = ['person', 'current_groups'] + RecordAdmin.list_display
    list_per_page = 30
    inlines = [RoleInline]


class EventAdmin (RecordAdmin):
    search_fields = ['name', 'org__name']
    list_display = ['__unicode__', 'date', 'time', 'org', 'owner'] \
                   + RecordAdmin.list_display
    list_display_links = ['__unicode__']
    list_per_page = 30
    ordering = ('-date', '-time')
    list_filter = RecordAdmin.list_filter + ['fair']


class ActorAdmin (RecordAdmin):
    search_fields = ['event__name', 'participant__person__first_name',
                     'participant__person__middle_name',
                     'participant__person__last_name',
                     'participant__person__nickname']
    list_display = ['date', '__unicode__'] + RecordAdmin.list_display
    list_display_links = ['date', '__unicode__']
    list_per_page = 30
    ordering = ('-event__date', )
    raw_id_fields = ['event', 'participant']


class CommentAdmin (RecordAdmin):
    list_display = ['created', 'author', '__unicode__'] \
                   + RecordAdmin.list_display
    ordering = ('-created', )
    raw_id_fields = ['author']


class EventCommentAdmin (CommentAdmin):
    raw_id_fields = CommentAdmin.raw_id_fields + ['event']


class ApplicationAdmin (admin.ModelAdmin):
    raw_id_fields = ['participant']


class EventApplicationAdmin (ApplicationAdmin):
    list_display = ['participant', 'event'] + RecordAdmin.list_display
    raw_id_fields = ApplicationAdmin.raw_id_fields + ['event']
