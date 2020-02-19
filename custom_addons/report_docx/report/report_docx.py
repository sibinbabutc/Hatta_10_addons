import os
from cStringIO import StringIO

from odoo.report.report_sxw import report_sxw
from odoo.api import Environment
import time
import random
import tempfile

import logging
_logger = logging.getLogger(__name__)

try:
    from docx import Document
except ImportError:
    _logger.debug('Cannot import document.')


class ReportDocx(report_sxw):

    def create(self, cr, uid, ids, data, context=None):
        self.env = Environment(cr, uid, context)
        report_obj = self.env['ir.actions.report.xml']
        report = report_obj.search([('report_name', '=', self.name[7:])])
        if report.ids:
            self.title = report.name
            if report.report_type == 'docx':
                return self.create_docx_report(ids, data, report)
        return super(ReportDocx, self).create(cr, uid, ids, data, context)

    def create_docx_report(self, ids, data, report):
        self.parser_instance = self.parser(
            self.env.cr, self.env.uid, self.name2, self.env.context)
        objs = self.getObjects(
            self.env.cr, self.env.uid, ids, self.env.context)
        self.parser_instance.set_context(objs, data, ids, 'docx')
        file_data = StringIO()
        document = Document()
        self.generate_docx_report(document, data, objs)
        path = '%s/report_%s%s.docx' % (tempfile.gettempdir(), str(int(time.time())), str(int(1000 + random.random() * 1000)))
        document.save(path)
        # file_data.seek(0)
        input_stream = open(path, 'r')
        try:
            report_data = input_stream.read()
        finally:
            input_stream.close()
            os.system('rm %s' % path)
        return (report_data, 'docx')

    def generate_docx_report(self, workbook, data, objs):
        raise NotImplementedError()
