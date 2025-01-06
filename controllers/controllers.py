# -*- coding: utf-8 -*-
# from odoo import http


# class McMantenimientoInstaladores(http.Controller):
#     @http.route('/mc_mantenimiento_instaladores/mc_mantenimiento_instaladores', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/mc_mantenimiento_instaladores/mc_mantenimiento_instaladores/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('mc_mantenimiento_instaladores.listing', {
#             'root': '/mc_mantenimiento_instaladores/mc_mantenimiento_instaladores',
#             'objects': http.request.env['mc_mantenimiento_instaladores.mc_mantenimiento_instaladores'].search([]),
#         })

#     @http.route('/mc_mantenimiento_instaladores/mc_mantenimiento_instaladores/objects/<model("mc_mantenimiento_instaladores.mc_mantenimiento_instaladores"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('mc_mantenimiento_instaladores.object', {
#             'object': obj
#         })

