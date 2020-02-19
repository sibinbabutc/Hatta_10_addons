from odoo.addons.web.controllers.main import Reports, serialize_exception
from odoo.addons.report.controllers.main import ReportController
import urllib
from odoo.http import Controller, route, request


class WebPdfReports(ReportController):

    @route(['/report/preview/<reportname>'], type='http', auth="user")
    def report_download(self, reportname, data, token):
        result = super(WebPdfReports, self).report_download(data, token)
        result.headers['Content-Disposition'] = result.headers['Content-Disposition'].replace('attachment', 'inline')
        return result


class PreviewReports(Reports):

    @route('/web/report', type='http', auth="user")
    @serialize_exception
    def index(self, action, token):
        result = super(PreviewReports, self).index(action, token)
        result.headers['Content-Disposition'] = result.headers['Content-Disposition'].replace('attachment', 'inline')
        return result