# -*- encoding: utf-8 -*-

from odoo import api, fields, models


class GenerateOtpWiz(models.TransientModel):
    _name = 'generate.otp.wiz'
    
    def generate_otp(self):
        self.env['hatta.login.otp'].search([]).reset_password(manual=True)

