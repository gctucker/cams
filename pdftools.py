from copy import deepcopy
from cams.models import (Record, Contactable, Contact, Person, Organisation,
                         Member)
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Table,
                                TableStyle, Spacer)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT
from reportlab.lib import colors

def append_org_form(org, flow, page_size):
    styles = getSampleStyleSheet()
    width, height = page_size
    border = inch/2
    w = width - 2*border
    space = inch/4

    title_style = deepcopy(styles["Normal"])
    title_style.fontSize = 13
    title = Paragraph(org.name, title_style)
    flow.append(title)
    flow.append(Spacer(0, space))

    c = Contact.objects.filter(obj=org)
    if len(c) == 0:
        return

    c = c[0]
    addr = c.line_1
    if c.line_2:
        addr += ', ' + c.line_2
    if c.line_3:
        addr += ', ' + c.line_3

    table_width = w
    title_width = 0.8*inch
    value_width = table_width - title_width
    widths = (title_width, value_width)

    LIST_STYLE = TableStyle(
        [('LINEBELOW', (0, 0), (-1, -2), 0.25, colors.black),
         ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
         ('ALIGN', (1, 0), (1, -1), 'LEFT'),
         ('LINEAFTER', (0, 0), (0, -1), 0.25, colors.black),
         ])

    table = Table((('Address', addr),
                   ('Postcode', c.postcode),
                   ('Town', c.town),
                   ('E-mail', c.email),
                   ('Website', c.website),
                   ('Telephone', c.telephone),
                   ('Mobile', c.mobile),
                   ('Fax', c.fax),
                   ), style=LIST_STYLE, colWidths=widths)
    flow.append(table)

    BOX_STYLE = TableStyle(
        [('LINEBELOW', (0, 0), (-1, 0), 1.0, colors.black),
         ('ALIGNMENT', (0, 0), (-1, 0), 'CENTRE'),
         ('LINEBELOW', (0, 1), (-1, -1), 0.25, colors.black),
         ])
    m_data = (('Name', 'Telephone', 'E-mail'), )
    widths = (w*0.30, w*0.25, w*0.45)

    txt_style = deepcopy(styles["Normal"])
    txt_style.fontSize = 10
    txt_style.alignment = TA_LEFT
    flow.append(Spacer(0, space))
    flow.append(Paragraph('List of people who can be contacted:', txt_style))

    members = Member.objects.filter(organisation=org)
    for m in members[:10]:
        c = Contact.objects.filter(obj=m)
        if not c:
            c = Contact.objects.filter(obj=m.person)
        if c:
            c = c[0]
            tel = c.telephone
            if not tel:
                tel = c.mobile
            email = c.email
        else:
            tel = ''
            email = ''
        m_data += ((m.person.__unicode__(), tel, email), )

    for i in range(len(members), 10):
        m_data += (('', '', ''), )

    table = Table(m_data, style=BOX_STYLE, colWidths=widths)
    flow.append(Spacer(0, space))
    flow.append(table)