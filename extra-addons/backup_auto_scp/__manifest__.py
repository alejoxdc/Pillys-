{
    'name': 'Backup Automático SCP',
    'version': '17.0.1.0.0',
    'category': 'Tools',
    'summary': 'Backup automático cada 8 horas usando SCP al servidor remoto',
    'description': """
    Módulo para backup automático de base de datos:
    
    Características:
    - Backup automático cada 8 horas
    - Envío directo por SCP al servidor 5.78.131.185
    - Sin uso de espacio local temporal
    - Interfaz simple de configuración
    - Logs detallados de cada backup
    """,
    'author': 'GT Development',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'data/backup_cron.xml',
        'views/backup_auto_scp_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}