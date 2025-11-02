from odoo import models, fields

class EstatePropertyType(models.Model):
    _name = "estate.property.type"
    _description = "Tipo de Propiedad"

    _sql_constraints = [
        ('unique_tag_name', 'UNIQUE(name)', 'El nombre de la etiqueta debe ser único.')
    ]
    
    name = fields.Char(string="Nombre", required=True)