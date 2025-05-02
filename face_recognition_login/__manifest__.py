{
    'name': 'AI Driven Face Recognition Login',
    'version': '1.0',
    'category': 'Extra Tools',
    'summary': 'Authenticate users with facial recognition',
    'description': """
        This module adds facial recognition capabilities to Odoo login.
        Features:
        - Face enrollment for users
        - Face authentication during login
        - Fallback to password authentication
    """,
    'author': 'Metamorphosis Ltd',
    'website': 'https://metamoprphosis.com.bd',
    'depends': ['base', 'web', 'auth_signup'],
    'data': [
        'security/ir.model.access.csv',
        'views/face_login_template.xml',
        'views/face_id_page.xml',
        'views/res_user_view.xml',
    ],
    'assets': {
        'assets': {
            'web.assets_frontend': [
                'face_recognition_login/static/src/**/*',
            ],
        },
    },
    'images': ['static/description/icon.png'],
    'application': False,
    'price': 125.00,
    'currency':'EUR',
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}