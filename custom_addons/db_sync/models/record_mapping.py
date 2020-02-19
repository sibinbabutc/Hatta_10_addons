from odoo import models, fields, api
from odoo.exceptions import ValidationError


class RecordMapping(models.Model):
    _name = 'record.mapping'

    model_id = fields.Char()
    ext_db_name = fields.Char()
    ext_record_id = fields.Integer()
    int_record_id = fields.Integer()

    def get_internal_record_id(self, ext_db_name, model_id, ext_record_id):
        if type(ext_record_id) is int:
            ext_record_id = [ext_record_id]
        records = self.search([('ext_db_name', '=', ext_db_name), ('model_id', '=', model_id),
                               ('ext_record_id', 'in', ext_record_id)])
        return records
