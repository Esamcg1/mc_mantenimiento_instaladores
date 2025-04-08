# -*- coding: utf-8 -*-

import io
import xlsxwriter                                        #
import base64
from odoo import models, fields, api
import string

#Herencia al modelo sale.order y hacer el calculo de los dos tipos de productos
class McSaleOrder(models.Model):
    _inherit = 'sale.order'
    _description = 'sale.order'

    # Campos para el instalador
    x_total_productos_instalacion = fields.Float(string="Total Productos Instalación", compute="_compute_totales_productos")
    x_total_productos_no_instalacion = fields.Float(string="Total Productos No Instalación", compute="_compute_totales_productos")
    x_total_productos = fields.Float(string="Total Productos", compute="_compute_totales_productos")

    #logica para sumar los tipos de productos (instalacion y no instalacion)
    @api.depends('order_line.product_id', 'order_line.price_total')
    def _compute_totales_productos(self):
        for order in self:
            total_instalacion = 0.0
            total_no_instalacion = 0.0

            for line in order.order_line:
                if line.product_id.instalation_product:
                    total_instalacion += line.price_total
                else:
                    total_no_instalacion += line.price_total

            order.x_total_productos_instalacion = total_instalacion
            order.x_total_productos_no_instalacion = total_no_instalacion
            order.x_total_productos = total_instalacion + total_no_instalacion

#Herencia para campos en los productos
class mc_mantenimiento_instaladores(models.Model):
    _inherit = 'product.template'
    _description = 'product.template'

    comision_porcentaje = fields.Float(string="Porcentaje de comisión", default=0.0)
    instalation_product = fields.Boolean(string="Producto de instalación", default=False)

#Herencia para campo en el encabezado de factura
class McMantenimientoInstaladoresAccountMove(models.Model):
    _inherit = 'account.move'
    _description = 'account.move'

    instalador = fields.Many2one(string="Instalador", comodel_name='hr.employee')
    albaran_numeros = fields.Char(string='Números de Albaranes', compute='_compute_albaran_numeros')

    @api.depends('invoice_origin')
    def _compute_albaran_numeros(self):
        for move in self:
            albaranes = self.env['stock.picking'].search([('origin', '=', move.invoice_origin)])
            move.albaran_numeros = ', '.join(albaranes.mapped('name'))

    @api.onchange('instalador')
    def _onchange_instalador(self):
        """Actualizar las líneas de factura cuando se cambie el instalador en el encabezado."""
        for line in self.invoice_line_ids:
            if line.product_id and line.product_id.instalation_product:
                line.instalador = self.instalador

#Herencia para el campo en lineas de factura
class McMantenimientoInstaladoresAccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    _description = 'account.move.line'

    #Campos en account.move.line
    instalador = fields.Many2one(string="Instalador", comodel_name='hr.employee')
    move_name = fields.Char(related='move_id.name', string="Nombre de factura", store=True)
    invoice_date = fields.Date(related="move_id.invoice_date", string="Fecha de Factura", store=True)
    comision_porcentaje = fields.Float(string="Porcentaje comisión", compute="_compute_comision_porcentaje")
    comision = fields.Float(string="Comisión", compute="_compute_comision", store=True)
    albaran_numeros = fields.Char(string='Números de Albaranes', related='move_id.albaran_numeros', store=True)

    #Mostrar el campo comision_porcentaje en account.move y el notebook de mc_consulta_instaladores
    @api.depends('product_id')
    def _compute_comision_porcentaje(self):
        for line in self:
            line.comision_porcentaje = line.product_id.product_tmpl_id.comision_porcentaje if line.product_id else 0.0

    #Calcular la comision en base al porcentaje de comision de un producto
    @api.depends('price_total', 'comision_porcentaje')
    def _compute_comision(self):
        for line in self:
            line.comision = (line.price_total * line.comision_porcentaje) / 100 if line.comision_porcentaje else 0.0

#Modelo para generar la consulta de los instaladores en base al ejemplo del reporte
class McConsultasInstaladores(models.Model):
    _name = "mc_consulta_instaladores.mc_consulta_instaladores"
    _description = "mc_consulta_instaladores.mc_consulta_instaladores"

    #campos
    nombre = fields.Char(string="Nombre del reporte", requiere=True)
    fecha_inicio = fields.Date(string="Fecha de inicio", require=True)
    fecha_fin = fields.Date(string="Fecha de finalización", require=True)
    estado = fields.Selection([('1','Borrador'),
                               ('2','Reporte generado')], 
                               default='1')

    lineas_facturas_ids = fields.Many2many('account.move.line', compute='_compute_lineas_factura', string='Líneas de Factura')

    def exportar_excel(self):
        self.write({'estado': '2'})
        for record in self:
            # Crear un archivo Excel en memoria
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output)
            worksheet = workbook.add_worksheet("Reporte Instaladores")

            # Escribir encabezados
            headers = [
                "No. Factura",
                "Fecha",
                "No. orden de entrega",
                "Producto",
                "Descripción",
                "Instalador",
                "Precio sin IVA",
                "Porcentaje de comisión",
                "Comisión",
            ]
            for col, header in enumerate(headers):
                worksheet.write(0, col, header)

            # Escribir los datos
            row = 1
            for linea in record.lineas_facturas_ids:
                worksheet.write(row, 0, linea.move_id.name or "")
                worksheet.write(row, 1, str(linea.move_id.invoice_date) or "")
                worksheet.write(row, 2, linea.move_id.albaran_numeros or "")
                worksheet.write(row, 3, linea.product_id.display_name or "")
                worksheet.write(row, 4, linea.name or "")
                worksheet.write(row, 5, linea.instalador.name if linea.instalador else " ")
                worksheet.write(row, 6, linea.price_total or 0.0)
                worksheet.write(row, 7, linea.comision_porcentaje or 0.0)
                worksheet.write(row, 8, linea.comision or 0.0)
                row += 1

            workbook.close()
            output.seek(0)

            # Crear un adjunto con el archivo generado
            attachment = self.env['ir.attachment'].create({
                'name': f'Reporte_Instaladores_{record.nombre}.xlsx',
                'type': 'binary',
                'datas': base64.b64encode(output.read()),
                'res_model': self._name,
                'res_id': record.id,
                'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            })

            output.close()

            # Descargar el archivo generado
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'new',
            }


    # @api.depends('fecha_inicio', 'fecha_fin')
    # def _compute_lineas_factura(self):
    #     for record in self:
    #         if record.fecha_inicio and record.fecha_fin:
    #             # Obtener líneas de factura filtradas por las fechas
    #             lineas = self.env['account.move.line'].search([
    #                 ('move_id.invoice_date', '>=', record.fecha_inicio),
    #                 ('move_id.invoice_date', '<=', record.fecha_fin),
    #                 ('move_id.move_type', '=', 'out_invoice'),
    #             ])
    #             record.update({'lineas_facturas_ids': lineas})
    #         else:
    #             record.update({'lineas_facturas_ids': [(5, 0, 0)]})
    @api.depends('fecha_inicio', 'fecha_fin')
    def _compute_lineas_factura(self):
        for record in self:
            if record.fecha_inicio and record.fecha_fin:
                # Obtener líneas de factura filtradas por las fechas y productos de instalación
                lineas = self.env['account.move.line'].search([
                    ('move_id.invoice_date', '>=', record.fecha_inicio),
                    ('move_id.invoice_date', '<=', record.fecha_fin),
                    ('move_id.move_type', '=', 'out_invoice'),
                    ('product_id.product_tmpl_id.instalation_product', '=', True),  # Filtro para productos de instalación
                ])
                record.update({'lineas_facturas_ids': lineas})
            else:
                record.update({'lineas_facturas_ids': [(5, 0, 0)]})

    #Funciones para cambiar el campo estado
    # def exportar_excel(self):
    #     self.write({'estado': '2'})

    def action_cancelar_consulta(self):
        self.write({'estado': '1'})

# :)