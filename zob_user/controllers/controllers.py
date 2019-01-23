# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
_logger = logging.getLogger(__name__)

from odoo import http
from odoo.http import request
from odoo.service import security

from odoo import SUPERUSER_ID, registry, api

class Model(object):

    @classmethod
    def create(self,obj, vals):
        return obj.create(vlas)

    @classmethod
    def search_read(cls,obj, domain=None, fields=None,
                         offset=0, limit=None, order=None, *args, **kwargs):
        recs = obj.search(domain or [],offset=offset, limit=limit, order=order)
        if not fields:
            fields = []
        return cls._return_for_read(recs,fields)

    @classmethod
    def read(cls,obj,ids,fields=None,*args, **kwargs):
        recs = obj.browse(ids)
        if not fields:
            fields = []
        return cls._return_for_read(recs,fields)

    @classmethod
    def _return_for_read(cls,recs,fields):
        def fn1(field):
            if isinstance(field, str):
                return field
            elif isinstance(field, list):
                return field[0]

        new_fields = [ fn1(field) for field in fields if isinstance(field,(str,list)) ]

        #ret_recs = recs.read(new_fields)
        # fn2 be copy from odoo.models.search_read(), 2018-8-13
        def fn2(records, fields11):
            result = records.read(fields11)
            if len(result) <= 1:
                return result

            # reorder read
            index = {vals['id']: vals for vals in result}
            return [index[record.id] for record in records if record.id in index]

        ret_recs = fn2(recs, new_fields)

        for ret_rec in ret_recs:
            for field in fields:
                if isinstance(field, list):
                    child_fname = field[0]
                    child_fields = field[1]
                    rid = ret_rec['id']
                    rec = recs.filtered(lambda r: r.id == rid )
                    child_recs = getattr(rec, child_fname)
                    ret_rec[ field[0] ] = cls._return_for_read(child_recs, child_fields)

        return ret_recs


class JsonApi(http.Controller):
    @http.route('/json/test1',type='json', auth='none',cors='*',csrf=False)
    def test1(self,**kw):
        print('hello')
        return "hello!"

    @http.route('/json/api',type='json', auth='user',cors='*',csrf=False)
    def json_api(self,model,method, args,kwargs,sudo=None):
        _logger.info('model %s call %s with %s, %s, %s', model,method, args,kwargs,sudo)
        
        odoo_model = request.env[model]
        if sudo:
            odoo_model = odoo_model.sudo(sudo)

        if method not in ['read2','search_read2']:
            return api.call_kw(odoo_model,method,args,kwargs)

        ret = {
            'read2':        Model.read,
            'search_read2': Model.search_read,
            'create2':      Model.create
        }[method](odoo_model, *args, **kwargs)

        return ret

    @http.route('/json/user/login',type='json', auth='none', cors='*', csrf=False )
    def login(self,db,login,password, **kw):
        _logger.info('call login with %s, %s, %s', db,login,password )
        
        request.session.authenticate(db, login, password)
        request.session.rotate = False
        return request.env['ir.http'].session_info()

    @http.route('/json/user/register',type='json', auth='none', cors='*', csrf=False )
    def register(self,db,login,password):
        with registry(db).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            return env['res.users'].register(login,password)

    @http.route('/json/user/reset/password',type='json', auth='none', cors='*', csrf=False )
    def reset_psw(self,db,login,password):
        with registry(db).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            return env['res.users'].reset_new_password(login,password)


