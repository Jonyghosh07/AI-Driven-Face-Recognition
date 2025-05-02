from odoo import http
from odoo.http import request
import numpy as np
import logging
import json
import werkzeug
from werkzeug.exceptions import BadRequest

_logger = logging.getLogger(__name__)

class FaceIDLoginController(http.Controller):

    @http.route('/web/faceid/login', type='http', auth='public', website=True)
    def faceid_login(self, **kwargs):
        """Render face recognition login page"""
        return request.render('face_recognition_login.faceid_login_template')
    
    
    
    @http.route('/web/faceid/verify', type='json', auth='public', csrf=False)
    def faceid_verify(self, **kwargs):
        """Verify face descriptor and log in user if match is found"""
        try:
            # Extract descriptor - using multiple methods to ensure it's found
            descriptor = []
            
            # Try multiple ways to extract the descriptor
            params = kwargs.get('params', {})
            if params and isinstance(params, dict) and 'descriptor' in params:
                descriptor = params.get('descriptor', [])
            elif 'descriptor' in kwargs:
                descriptor = kwargs.get('descriptor', [])
            elif hasattr(request, 'jsonrequest') and request.jsonrequest:
                if 'params' in request.jsonrequest and isinstance(request.jsonrequest['params'], dict):
                    descriptor = request.jsonrequest['params'].get('descriptor', [])
            
            _logger.info(f"Extracted descriptor of length:------------------ {len(descriptor) if descriptor else 0}")
            
            if not descriptor or len(descriptor) != 128:
                _logger.warning(f"Invalid descriptor received: {len(descriptor) if descriptor else 0}")
                return {'success': False, 'error': 'Invalid descriptor format'}

            # Use the model to find a user by face
            FaceModel = request.env['res.users.face'].sudo()
            user_id = FaceModel.verify_face(descriptor)
            
            if user_id:
                try:
                    # Get the user object
                    user = request.env['res.users'].sudo().browse(user_id)
                    _logger.info(f"Face recognized for user {user.login}, setting up session directly")
                    
                    # Import security module for token generation
                    from odoo.service import security
                    
                    # Set up session manually
                    request.session.uid = user_id
                    request.session.login = user.login
                    
                    # Generate and set session token
                    session_token = security.compute_session_token(request.session, request.env)
                    request.session.session_token = session_token
                    
                    # Update environment with the new user
                    request.update_env(user=user_id)
                    
                    # Mark session as modified
                    request.session.modified = True
                    
                    _logger.info(f"Direct session setup completed for user {user.login}")
                    return {'success': True}
                    
                except Exception as session_error:
                    _logger.error(f"Session setup error: {str(session_error)}", exc_info=True)
                    return {'success': False, 'error': f"Session error: {str(session_error)}"}
            
            _logger.info("Face not recognized, login failed")
            return {'success': False, 'error': 'Face not recognized'}
                
        except Exception as e:
            _logger.error(f"Face verification error: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    
    
    
    
    
    @http.route('/web/faceid/register', type='http', auth='user', website=True)
    def faceid_register_page(self, **kwargs):
        """Render face registration page"""
        return request.render('face_recognition_login.faceid_register_page')
    
    
    
    
    
    @http.route('/web/faceid/register/process', type='json', auth='user')
    def faceid_register_process(self, **kwargs):
        """Register user's face using their profile image"""
        try:
            user = request.env.user
            FaceModel = request.env['res.users.face'].sudo()
            
            result = FaceModel.generate_face_descriptor(user.id)
            
            if result:
                return {'success': True}
            else:
                return {'success': False, 'error': 'Could not generate face descriptor. Make sure your profile image has a clear face.'}
                
        except Exception as e:
            _logger.error(f"Face registration error: {str(e)}")
            return {'success': False, 'error': str(e)}