import json
import csv
import operator

from cStringIO import StringIO
from odoo.http import content_disposition,request

from odoo import http
from odoo.addons.web.controllers import main


class SIFExportFormat(object):
    raw_data = False

    def base(self, data, token):
        params = json.loads(data)
        model, datarecord = operator.itemgetter('model', 'datarecord')(params)

        Model = request.env[model].with_context(**params.get('context', {}))
        records = Model.browse(datarecord['id'])

        import_data = records.export_data_sif()
        file_name = records.get_sif_file_name()
        return request.make_response(self.from_data(import_data),
                                     headers=[('Content-Disposition',
                                               content_disposition(file_name)),
                                              ('Content-Type', self.content_type)],
                                     cookies={'fileToken': token})


class SIFExport(SIFExportFormat, http.Controller):

    @http.route('/web/export/sif', type='http', auth="user")
    @main.serialize_exception
    def index(self, data, token):
        return self.base(data, token)

    @property
    def content_type(self):
        return 'text/csv;charset=utf8'

    # def filename(self, base):
    #     return base + '.sif'

    def from_data(self, rows):
        fp = StringIO()
        writer = csv.writer(fp)

        for data in rows:
            row = []
            for d in data:
                if isinstance(d, unicode):
                    try:
                        d = d.encode('utf-8')
                    except UnicodeError:
                        pass
                if d is False: d = None

                # Spreadsheet apps tend to detect formulas on leading =, + and -
                if type(d) is str and d.startswith(('=', '-', '+')):
                    d = "'" + d

                row.append(d)
            writer.writerow(row)

        fp.seek(0)
        data = fp.read()
        fp.close()
        return data