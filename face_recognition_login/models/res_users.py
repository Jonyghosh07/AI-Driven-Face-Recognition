# File: models/face_recognition.py

from odoo import models, fields, api
import base64
from io import BytesIO
import numpy as np
from scipy.spatial.distance import cosine
import logging
import json

_logger = logging.getLogger(__name__)

try:
    from PIL import Image
    import face_recognition
    HAS_FACE_LIBS = True
except ImportError:
    HAS_FACE_LIBS = False
    _logger.warning("face_recognition library not installed. Run: pip install face_recognition")


class ResUsersFace(models.Model):
    _name = 'res.users.face'
    _description = 'User Face Recognition Data'

    user_id = fields.Many2one('res.users', string='User', required=True, ondelete='cascade')
    face_descriptor = fields.Text(string='Face Descriptor', help='JSON encoded face descriptor array')
    active = fields.Boolean(default=True)
    last_updated = fields.Datetime(string='Last Updated', default=fields.Datetime.now)
    
    @api.model
    def generate_face_descriptor(self, user_id):
        """Generate face descriptor from user's image_1920 field"""
        if not HAS_FACE_LIBS:
            _logger.error("Required libraries not installed")
            return False
        
        user = self.env['res.users'].sudo().browse(user_id)
        
        if not user or not user.image_1920:
            _logger.warning(f"User {user_id} has no image")
            return False
            
        try:
            # Convert base64 image to numpy array using PIL
            image_data = base64.b64decode(user.image_1920)
            image = Image.open(BytesIO(image_data))
            
            # Convert to RGB if needed (in case of RGBA)
            if image.mode != 'RGB':
                image = image.convert('RGB')
                
            # Convert to numpy array for face_recognition library
            image_array = np.array(image)
            
            # Use face_recognition library to find face and generate descriptor
            face_locations = face_recognition.face_locations(image_array)
            
            if not face_locations:
                _logger.warning(f"No face found in image for user {user_id}")
                return False
                
            # Use the first face found
            face_encoding = face_recognition.face_encodings(image_array, [face_locations[0]])[0]
            
            # Convert numpy array to list for JSON serialization
            descriptor = face_encoding.tolist()
            
            # Create or update face descriptor record
            existing = self.search([('user_id', '=', user_id)], limit=1)
            if existing:
                existing.write({
                    'face_descriptor': json.dumps(descriptor),
                    'last_updated': fields.Datetime.now()
                })
                _logger.info(f"Updated face descriptor for user {user_id}")
            else:
                self.create({
                    'user_id': user_id,
                    'face_descriptor': json.dumps(descriptor),
                })
                _logger.info(f"Created face descriptor for user {user_id}")
                
            return True
            
        except Exception as e:
            _logger.error(f"Error generating face descriptor: {str(e)}")
            return False
    
    @api.model
    def verify_face(self, descriptor, threshold=0.4):
        """Verify face descriptor against stored descriptors"""
        if not isinstance(descriptor, list) or len(descriptor) != 128:
            return False
            
        input_descriptor = np.array(descriptor)
        best_match = None
        best_distance = float('inf')
        
        # Get all active face descriptors
        face_records = self.search([('active', '=', True)])
        
        for record in face_records:
            try:
                stored_descriptor = json.loads(record.face_descriptor)
                stored_array = np.array(stored_descriptor)
                
                # Calculate similarity
                distance = cosine(input_descriptor, stored_array)
                _logger.info(f"Face comparison for user {record.user_id.id}, distance: {distance}")
                
                if distance < best_distance:
                    best_distance = distance
                    best_match = record
                    
            except Exception as e:
                _logger.error(f"Error comparing face descriptors: {str(e)}")
                continue
        
        # Check if the best match is good enough
        if best_match and best_distance < threshold:
            return best_match.user_id.id
        
        return False


class ResUsers(models.Model):
    _inherit = 'res.users'
    
    face_recognition_data = fields.One2many('res.users.face', 'user_id', string='Face Recognition Data')
    
    @api.model
    def create(self, vals):
        """Override create to generate face descriptor after user creation"""
        record = super(ResUsers, self).create(vals)
        if record.image_1920:
            record.generate_face_descriptor()
        return record

    def write(self, vals):
        """Override write to generate face descriptor if image changes"""
        result = super(ResUsers, self).write(vals)
        if 'image_1920' in vals and vals['image_1920']:
            self.filtered(lambda r: r.id and not isinstance(r.id, models.NewId)).generate_face_descriptor()
        return result
    
    def generate_face_descriptor(self):
        """Generate face descriptor from user's image"""
        if not self.id or not isinstance(self.id, int):
            print(f"Cannot generate descriptor - invalid ID: {self.id}, type: {type(self.id)}")
            return False
        
        FaceModel = self.env['res.users.face'].sudo()
        return FaceModel.generate_face_descriptor(self.id)
    

    # Override the _check_credentials method to support face recognition
    def _check_credentials(self, credential, user_agent_env):
        """Check credentials for face-based authentication"""
        # If this is a face-based authentication
        if isinstance(credential, dict) and credential.get('auth_type') == 'face_recognition':
            # The face has already been verified in the controller
            # We just need to return without error
            _logger.info(f"Face recognition auth for user {self.login}")
            return True
        
        # Not a face auth, proceed with standard authentication
        return super()._check_credentials(credential, user_agent_env)