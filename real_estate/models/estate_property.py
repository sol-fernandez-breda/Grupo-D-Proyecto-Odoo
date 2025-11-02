from odoo import models, fields, api, Command
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
import random

class EstateProperty(models.Model):
    _name = "estate.property"
    _description = "Propiedades"

    name = fields.Char(string="Título", required=True)
    property_type_id = fields.Many2one(
        comodel_name="estate.property.type",
        string="Tipo Propiedad",
        required=True
    )
    buyer_id = fields.Many2one(
        comodel_name="res.partner",
        string="Comprador",
    )
    salesman_id = fields.Many2one(
        comodel_name="res.users",
        string="Vendedor",
        index=True,
        tracking=True,
        default=lambda self: self.env.user,
        copy=False,
    )
    tag_ids = fields.Many2many(
        comodel_name="estate.property.tag",
        string="Etiquetas"
    )
    offer_ids = fields.One2many(
        comodel_name="estate.property.offer",
        inverse_name="property_id",
        string="Ofertas"
    )

    description = fields.Text(string="Descripción")
    postcode = fields.Char(string="Código Postal")
    date_availability = fields.Date(string="Fecha disponibilidad",default=lambda self: fields.Date.today() + relativedelta(months=3), copy=False)
    expected_price = fields.Float(string="Precio esperado")
    selling_price = fields.Float(string="Precio de venta", copy=False)
    bedrooms = fields.Integer(string="Habitaciones", default=2)
    living_area = fields.Integer(string="Superficie cubierta")
    facades = fields.Integer(string="Fachadas")
    garage = fields.Boolean(string="Garage")
    garden = fields.Boolean(string="Jardín")
    garden_orientation = fields.Selection(
        selection=[
            ("north", "Norte"),
            ("south", "Sur"),
            ("east", "Este"),
            ("west", "Oeste"),
        ],
        string="Orientación del jardín",
        default="north",
    )
    garden_area = fields.Integer(string="Superficie jardín")

    state = fields.Selection(
        selection=[
            ("nuevo", "Nuevo"),
            ("oferta_recibida", "Oferta recibida"),
            ("oferta_aceptada", "Oferta aceptada"),
            ("vendido", "Vendido"),
            ("cancelado", "Cancelado"),
        ],
        string="Estado",
        required=True,
        default="nuevo",
        copy=False
    )
    

    total_area = fields.Integer(
        string="Superficie total",
        compute="_compute_total_area",
        store=True
    )

    @api.depends("living_area", "garden_area")
    def _compute_total_area(self):
        for record in self:
            record.total_area = record.living_area  + record.garden_area

    best_offer = fields.Float(
        string="Mejor oferta",
        compute="_compute_best_offer",
        store=True
    )
    
    @api.depends('offer_ids', 'offer_ids.price')
    def _compute_best_offer(self):
        for record in self:
            offers = record.offer_ids.mapped('price')
            record.best_offer = max(offers) if offers else 0
            
    @api.onchange('garden')
    def _onchange_garden(self):
        if self.garden:
            self.garden_area = 10
        else:
            self.garden_area = 0

    @api.onchange('expected_price')
    def _onchange_expected_price(self):
        if 0 < self.expected_price < 10000:
            raise UserError("El precio ingresado es muy bajo")

    def action_cancel(self):
        for record in self:
            if record.state == "vendido":
                raise UserError("No se puede cancelar una propiedad ya vendida.")
            record.state = "cancelado"

    def action_mark_sold(self):
        for record in self:
            if record.state == "cancelado":
                raise UserError("No se puede vender una propiedad cancelada.")
            record.state = "vendido"

    offer_partner_ids = fields.Many2many(
        comodel_name="res.partner",
        string="Personas que hicieron ofertas",
        compute="_compute_offer_partners",
        store=True
    )

    @api.depends('offer_ids.partner_id')
    def _compute_offer_partners(self):
        for record in self:
            record.offer_partner_ids = record.offer_ids.mapped('partner_id')

    def action_generate_auto_offer(self):
        for prop in self:
            # Contactos activos que no hicieron oferta todavía
            partners_disponibles = self.env['res.partner'].search([
                ('active', '=', True),
                ('id', 'not in', prop.offer_partner_ids.ids)
            ])
            if not partners_disponibles:
                raise UserError("No hay contactos disponibles para generar una oferta automática.")

            # Contacto al azar
            partner = random.choice(partners_disponibles)

            # Precio aleatorio entre -30% y +30%
            if prop.expected_price <= 0:
                raise UserError("La propiedad no tiene un precio esperado válido.")
            precio_aleatorio = prop.expected_price * random.uniform(0.7, 1.3)

            # Se crea la oferta
            self.env['estate.property.offer'].create({
                'price': round(precio_aleatorio, 2),
                'status': 'refused',
                'partner_id': partner.id,
                'property_id': prop.id,
                'validity': 7
            })


    def action_clear_tags(self):
        for record in self:
            record.tag_ids = [Command.clear()]

    
    def action_load_all_tags(self):
        all_tags = self.env["estate.property.tag"].search([])
        if not all_tags:
            raise UserError("No existen etiquetas para cargar.")
        for record in self:
            record.tag_ids = [Command.set(all_tags.ids)]

    def action_add_new_tag(self):
        tag_model = self.env["estate.property.tag"]
        tag = tag_model.search([("name", "=", "A estrenar")], limit=1)

        if not tag:
            tag = tag_model.create({"name": "A estrenar"})

        for record in self:
            if tag.id not in record.tag_ids.ids:
                record.tag_ids = [Command.link(tag.id)]


    @api.ondelete(at_uninstall=False)
    def _unlink_if_new_or_cancelled(self):
        for record in self:
            if record.state not in ('nuevo', 'cancelado'):
                raise UserError("Solo se pueden eliminar propiedades con estado 'Nuevo' o 'Cancelado'")
    
