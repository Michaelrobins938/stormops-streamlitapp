"""
CRM Integration Layer
Handles ServiceTitan/JobNimbus API calls for lead creation, job updates, and route pushes.
"""

import requests
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
import psycopg2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CRMIntegration:
    """
    Integrates with ServiceTitan/JobNimbus CRM.
    """
    
    def __init__(self, crm_type: str = 'servicetitan', api_key: str = '', api_url: str = ''):
        """
        Initialize CRM integration.
        
        Args:
            crm_type: 'servicetitan' or 'jobnimbus'
            api_key: CRM API key
            api_url: CRM API base URL
        """
        self.crm_type = crm_type
        self.api_key = api_key
        self.api_url = api_url
        self.session = requests.Session()
        self.session.headers.update({'Authorization': f'Bearer {api_key}'})
    
    def create_lead(
        self,
        first_name: str,
        last_name: str,
        phone: str,
        email: str,
        address: str,
        zip_code: str,
        sii_score: float,
        hail_intensity_mm: float,
        event_id: str,
    ) -> Optional[str]:
        """
        Create a lead in the CRM.
        
        Args:
            first_name: Customer first name
            last_name: Customer last name
            phone: Phone number
            email: Email address
            address: Property address
            zip_code: ZIP code
            sii_score: StormOps Impact Index score
            hail_intensity_mm: Hail intensity in mm
            event_id: Event ID
        
        Returns:
            CRM lead ID if successful, None otherwise
        """
        
        try:
            if self.crm_type == 'servicetitan':
                return self._create_lead_servicetitan(
                    first_name, last_name, phone, email, address, zip_code,
                    sii_score, hail_intensity_mm, event_id
                )
            elif self.crm_type == 'jobnimbus':
                return self._create_lead_jobnimbus(
                    first_name, last_name, phone, email, address, zip_code,
                    sii_score, hail_intensity_mm, event_id
                )
        except Exception as e:
            logger.error(f"Error creating lead: {e}")
            return None
    
    def _create_lead_servicetitan(
        self,
        first_name: str,
        last_name: str,
        phone: str,
        email: str,
        address: str,
        zip_code: str,
        sii_score: float,
        hail_intensity_mm: float,
        event_id: str,
    ) -> Optional[str]:
        """Create lead in ServiceTitan."""
        
        payload = {
            'firstName': first_name,
            'lastName': last_name,
            'phone': phone,
            'email': email,
            'address': address,
            'zipCode': zip_code,
            'customFields': {
                'siiScore': sii_score,
                'hailIntensity': hail_intensity_mm,
                'eventId': event_id,
                'source': 'StormOps',
            },
        }
        
        response = self.session.post(
            f'{self.api_url}/leads',
            json=payload,
        )
        
        if response.status_code == 201:
            lead_id = response.json().get('id')
            logger.info(f"Created ServiceTitan lead: {lead_id}")
            return lead_id
        else:
            logger.error(f"ServiceTitan API error: {response.status_code} {response.text}")
            return None
    
    def _create_lead_jobnimbus(
        self,
        first_name: str,
        last_name: str,
        phone: str,
        email: str,
        address: str,
        zip_code: str,
        sii_score: float,
        hail_intensity_mm: float,
        event_id: str,
    ) -> Optional[str]:
        """Create lead in JobNimbus."""
        
        payload = {
            'firstName': first_name,
            'lastName': last_name,
            'phone': phone,
            'email': email,
            'address': address,
            'zipCode': zip_code,
            'customData': {
                'siiScore': sii_score,
                'hailIntensity': hail_intensity_mm,
                'eventId': event_id,
            },
        }
        
        response = self.session.post(
            f'{self.api_url}/contacts',
            json=payload,
        )
        
        if response.status_code == 201:
            lead_id = response.json().get('id')
            logger.info(f"Created JobNimbus lead: {lead_id}")
            return lead_id
        else:
            logger.error(f"JobNimbus API error: {response.status_code} {response.text}")
            return None
    
    def send_sms(self, phone: str, message: str) -> bool:
        """
        Send SMS to customer.
        
        Args:
            phone: Phone number
            message: SMS message
        
        Returns:
            True if successful
        """
        
        try:
            payload = {
                'phone': phone,
                'message': message,
            }
            
            response = self.session.post(
                f'{self.api_url}/sms/send',
                json=payload,
            )
            
            if response.status_code == 200:
                logger.info(f"Sent SMS to {phone}")
                return True
            else:
                logger.error(f"SMS API error: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error sending SMS: {e}")
            return False
    
    def push_route(self, route_id: str, rep_id: str, route_data: Dict) -> bool:
        """
        Push route to field rep device.
        
        Args:
            route_id: Route ID
            rep_id: Field rep ID
            route_data: Route data (parcels, sequence, etc.)
        
        Returns:
            True if successful
        """
        
        try:
            payload = {
                'routeId': route_id,
                'repId': rep_id,
                'routeData': route_data,
            }
            
            response = self.session.post(
                f'{self.api_url}/routes/push',
                json=payload,
            )
            
            if response.status_code == 200:
                logger.info(f"Pushed route {route_id} to rep {rep_id}")
                return True
            else:
                logger.error(f"Route push error: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error pushing route: {e}")
            return False


class MockCRMIntegration(CRMIntegration):
    """Mock CRM for testing (no actual API calls)."""
    
    def __init__(self):
        super().__init__()
        self.created_leads = []
        self.sent_sms = []
        self.pushed_routes = []
    
    def create_lead(
        self,
        first_name: str,
        last_name: str,
        phone: str,
        email: str,
        address: str,
        zip_code: str,
        sii_score: float,
        hail_intensity_mm: float,
        event_id: str,
    ) -> Optional[str]:
        """Mock lead creation."""
        
        lead_id = f"mock-lead-{len(self.created_leads)}"
        self.created_leads.append({
            'id': lead_id,
            'firstName': first_name,
            'lastName': last_name,
            'phone': phone,
            'email': email,
            'address': address,
            'zipCode': zip_code,
            'siiScore': sii_score,
            'hailIntensity': hail_intensity_mm,
            'eventId': event_id,
            'createdAt': datetime.now().isoformat(),
        })
        logger.info(f"Mock: Created lead {lead_id}")
        return lead_id
    
    def send_sms(self, phone: str, message: str) -> bool:
        """Mock SMS sending."""
        
        self.sent_sms.append({
            'phone': phone,
            'message': message,
            'sentAt': datetime.now().isoformat(),
        })
        logger.info(f"Mock: Sent SMS to {phone}")
        return True
    
    def push_route(self, route_id: str, rep_id: str, route_data: Dict) -> bool:
        """Mock route push."""
        
        self.pushed_routes.append({
            'routeId': route_id,
            'repId': rep_id,
            'routeData': route_data,
            'pushedAt': datetime.now().isoformat(),
        })
        logger.info(f"Mock: Pushed route {route_id} to rep {rep_id}")
        return True
