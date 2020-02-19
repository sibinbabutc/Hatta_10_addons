import xmlrpclib
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import pickle


class Databases(models.Model):
    _name = 'database.details'
    _description = 'Databases'

    _rec_name = 'db_name'

    url = fields.Char('URL', default='http://', required=True)
    db_name = fields.Char('Database Name', required=True)
    username = fields.Char('Username', required=True)
    password = fields.Char('Password', required=True)

    uid = fields.Integer('User ID', readonly=True)
    state = fields.Selection([('not_connected', 'Not Connected'), ('connected', 'Connected')], default='not_connected')

    to_do_s = fields.Text('To Dos')

    @api.model
    def create(self, vals):
        if 'url' in vals and vals['url'][:4] != 'http':
            vals['url'] = 'http://%s' % vals['url']
        return super(Databases, self).create(vals)

    @api.multi
    def test_connection(self):
        for record in self:
            common = xmlrpclib.ServerProxy('{}/xmlrpc/common'.format(record.url))
            try:
                record.uid = common.login(record.db_name, record.username, record.password)
                record.state = 'connected'
                record.sync_state = 'not_synced'
            except:
                record.state = 'not_connected'

    @api.multi
    def retrieve_data(self, model, args=[]):
        db_con = xmlrpclib.ServerProxy('{}/xmlrpc/object'.format(self.url))
        data = db_con.execute(self.db_name, self.uid, self.password, model,
                              'search_read', args)
        return data

    def create_record_mapping(self, model, vals, ext_record_id,):
        int_record_id = self.env[model].create(vals)
        self.env['record.mapping'].create({
            'model_id': model,
            'ext_db_name': self.db_name,
            'ext_record_id': ext_record_id,
            'int_record_id': int_record_id.id,
        })
        return int_record_id

    @api.multi
    def sync_partner_categories(self):
        p_categ = self.env['res.partner.category']
        categories = self.retrieve_data(p_categ._name)
        for category in categories:
            vals = {
                'name': category['name'],
            }
            self.create_record_mapping(p_categ._name, vals, category['id'])

    @api.multi
    def sync_sale_price_lists(self):
        p_pricelist = self.env['product.pricelist']
        p_pricelist.search([]).unlink()
        pricelists = self.retrieve_data(p_pricelist._name, [('type', '=', 'sale')])
        for pricelist in pricelists:
            vals = {
                'name': pricelist['name'],
            }
            self.create_record_mapping(p_pricelist._name, vals, pricelist['id'])

    @api.multi
    def sync_title(self):
        title_obj = self.env['res.partner.title']
        title_obj.search([]).unlink()
        titles = self.retrieve_data(title_obj._name)
        for title in titles:
            vals = {
                'name': title['name'],
                'shortcut': title['shortcut']
            }
            self.create_record_mapping(title_obj._name, vals, title['id'])

    @api.multi
    def sync_sales_team(self):
        team_obj = self.env['crm.team']
        team_obj.search([]).unlink()
        teams = self.retrieve_data('crm.case.section')
        for team in teams:
            vals = {
                'name': team['name'],
            }
            self.create_record_mapping(team_obj._name, vals, team['id'])

    @api.multi
    def create_customers(self, partner_ids, non_removable_partners_name):
        count = 1
        for partner in partner_ids:
            print count
            count += 1
            if partner['name'] not in non_removable_partners_name:
                tags = self.env['record.mapping'].get_internal_record_id(self.db_name, 'res.partner.category',
                                                                         partner['category_id']).mapped('int_record_id')
                salesperson = self.env['res.users'].search([('name', '=', partner['user_id'][1])]).id if partner['user_id'] else False
                salesteam = self.env['crm.team'].search([('name', '=', partner['section_id'][1])]).id if partner['section_id'] else False
                vals = {
                    'name': partner['name'],
                    'image': partner['image'],
                    'sub_ledger_code': partner['partner_ac_code'],
                    'company_type': 'company' if partner['is_company'] else 'person',
                    'street': partner['street'],
                    'street2': partner['street2'],
                    'city': partner['city'],
                    'state_id': self.env['res.country.state'].search([('name', '=', partner['state_id'][1])]).id if partner['state_id'] else False,
                    'zip': partner['zip'],
                    'country_id': self.env['res.country'].search([('name', '=', partner['country_id'][1])]).id if partner['country_id'] else False,
                    'website': partner['website'],
                    'partner_code': partner['partner_code'],
                    'reviewed': partner['reviewed'],
                    'vat': partner['trn_code'],
                    'upload_invoice_to_customer': partner['upload_invoice'],
                    'partner_abbreviation': partner['partner_nick_name'],
                    'parent_id': self.env['record.mapping'].get_internal_record_id(self.db_name, 'res.partner',
                                                                                   int(partner['parent_id'][0])).int_record_id if partner['parent_id'] else False,
                    'category_id': [(6, 0, tags)] if tags else False,
                    'function': partner['function'],
                    'phone': partner['phone'],
                    'mobile': partner['mobile'],
                    'fax': partner['fax'],
                    'email': partner['email'],
                    'title': self.env['record.mapping'].get_internal_record_id(self.db_name, 'res.partner.title',
                                                                               int(partner['title'][0])).int_record_id if partner['title'] else False,
                    'team_id': salesteam,
                    'user_id': salesperson,
                    'company_id': self.env['res.company'].search([('name', '=', partner['company_id'][1])]).id if partner['company_id'] else False,
                    'ref': partner['ref'],
                    'lang': partner['lang'],
                    'customer': partner['customer'],
                    'supplier': partner['supplier'],
                    'is_manufacturer': partner['is_manufac'],
                    'is_principal_supplier': partner['pric_supplier'],
                    'is_employee': partner['is_employee'],
                    'opt_out': partner['opt_out'],
                    'property_product_pricelist': self.env['record.mapping'].get_internal_record_id(
                        self.db_name, 'product.pricelist', int(partner['property_product_pricelist'][0])).int_record_id if partner['property_product_pricelist'] else False,
                    'property_account_receivable_id': self.env['account.account'].search([('name', '=',
                                                                                           'Accounts Receivable')]).id,
                    'property_account_payable_id': self.env['account.account'].search([('name', '=', 'Payables')]).id

                }
                self.create_record_mapping('res.partner', vals, partner['id'])

    @api.multi
    def sync_customers(self):
        self.sync_partner_categories()
        self.sync_sale_price_lists()
        self.sync_title()
        self.sync_sales_team()
        partner_obj = self.env['res.partner']
        res_user_partners = self.env['res.users'].search([]).mapped('partner_id')
        res_company_partner = self.env['res.company'].search([]).mapped('partner_id')
        partner_obj.search([('id', 'not in', res_user_partners.ids + res_company_partner.ids)]).unlink()

        db_con = xmlrpclib.ServerProxy('{}/xmlrpc/object'.format(self.url))
        non_removable_partners_list = db_con.execute(self.db_name, self.uid, self.password, 'res.users',
                                                     'search', [])
        non_removable_partners = db_con.execute(self.db_name, self.uid, self.password, 'res.users',
                                                'read', non_removable_partners_list, ['name'])
        non_removable_partners_name = [x['name'] for x in non_removable_partners]
        with open("data_dump.pickle", "rb") as data_file:
            data = pickle.load(data_file)
        self.create_customers(data, non_removable_partners_name)