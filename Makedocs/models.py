from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Client(db.Model):
    __tablename__ = 'clients'

    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(50), unique=True, nullable=False)
    full_name = db.Column(db.String(500), nullable=False)
    short_name = db.Column(db.String(200))
    inn = db.Column(db.String(12), nullable=False)
    ogrn = db.Column(db.String(15))
    address = db.Column(db.Text)
    position = db.Column(db.String(200))
    position_genitive = db.Column(db.String(200))
    representative_name = db.Column(db.String(200))
    representative_name_genitive = db.Column(db.String(200))
    basis = db.Column(db.String(500))
    bank_details = db.Column(db.Text)
    phone = db.Column(db.String(50))
    email = db.Column(db.String(100))
    website = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Organization(db.Model):
    __tablename__ = 'organizations'

    id = db.Column(db.Integer, primary_key=True)
    signatory_position = db.Column(db.String(200), nullable=False)
    signatory_name = db.Column(db.String(200), nullable=False)
    signatory_power_of_attorney = db.Column(db.String(500))
    executor_position = db.Column(db.String(200), nullable=False)
    executor_name = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ContractTemplate(db.Model):
    __tablename__ = 'contract_templates'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Связь с файлами шаблонов
    files = db.relationship('TemplateFile', backref='template', lazy=True, cascade='all, delete-orphan')


class TemplateFile(db.Model):
    __tablename__ = 'template_files'

    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('contract_templates.id'), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    original_filename = db.Column(db.String(200), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)