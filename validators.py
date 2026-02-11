"""
Data validation for StormOps
"""

from typing import Dict, Tuple


class Validators:
    """Validate input data"""
    
    @staticmethod
    def validate_hail_intensity(hail_mm: float) -> Tuple[bool, str]:
        """Validate hail intensity"""
        if hail_mm < 0 or hail_mm > 200:
            return False, "Hail intensity must be 0-200mm"
        return True, ""
    
    @staticmethod
    def validate_sii_score(sii: float) -> Tuple[bool, str]:
        """Validate SII score"""
        if sii < 0 or sii > 100:
            return False, "SII score must be 0-100"
        return True, ""
    
    @staticmethod
    def validate_roof_material(material: str) -> Tuple[bool, str]:
        """Validate roof material"""
        valid = ['asphalt', 'metal', 'tile', 'wood', 'composite']
        if material.lower() not in valid:
            return False, f"Roof material must be one of: {', '.join(valid)}"
        return True, ""
    
    @staticmethod
    def validate_roof_age(age: int) -> Tuple[bool, str]:
        """Validate roof age"""
        if age < 0 or age > 100:
            return False, "Roof age must be 0-100 years"
        return True, ""
    
    @staticmethod
    def validate_zip_code(zip_code: str) -> Tuple[bool, str]:
        """Validate ZIP code"""
        if not zip_code or len(zip_code) != 5 or not zip_code.isdigit():
            return False, "ZIP code must be 5 digits"
        return True, ""
    
    @staticmethod
    def validate_phone(phone: str) -> Tuple[bool, str]:
        """Validate phone number"""
        digits = ''.join(c for c in phone if c.isdigit())
        if len(digits) < 10:
            return False, "Phone number must have at least 10 digits"
        return True, ""
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, str]:
        """Validate email"""
        if '@' not in email or '.' not in email:
            return False, "Invalid email format"
        return True, ""
    
    @staticmethod
    def validate_proposal_type(proposal_type: str) -> Tuple[bool, str]:
        """Validate proposal type"""
        valid = ['lead_gen', 'route_build', 'sms_campaign', 'impact_report', 'crew_positioning']
        if proposal_type not in valid:
            return False, f"Proposal type must be one of: {', '.join(valid)}"
        return True, ""
    
    @staticmethod
    def validate_forecast_data(forecast: Dict) -> Tuple[bool, str]:
        """Validate forecast data"""
        required = ['day', 'severe_probability', 'hail_probability', 'max_wind_mph']
        for field in required:
            if field not in forecast:
                return False, f"Missing required field: {field}"
        
        if not 0 <= forecast['severe_probability'] <= 1:
            return False, "Severe probability must be 0-1"
        
        if not 0 <= forecast['hail_probability'] <= 1:
            return False, "Hail probability must be 0-1"
        
        if forecast['max_wind_mph'] < 0 or forecast['max_wind_mph'] > 200:
            return False, "Wind speed must be 0-200 mph"
        
        return True, ""
    
    @staticmethod
    def validate_all(data: Dict) -> Tuple[bool, list]:
        """Validate all fields in data dict"""
        errors = []
        
        if 'hail_intensity_mm' in data:
            valid, msg = Validators.validate_hail_intensity(data['hail_intensity_mm'])
            if not valid:
                errors.append(msg)
        
        if 'sii_score' in data:
            valid, msg = Validators.validate_sii_score(data['sii_score'])
            if not valid:
                errors.append(msg)
        
        if 'roof_material' in data:
            valid, msg = Validators.validate_roof_material(data['roof_material'])
            if not valid:
                errors.append(msg)
        
        if 'roof_age_years' in data:
            valid, msg = Validators.validate_roof_age(data['roof_age_years'])
            if not valid:
                errors.append(msg)
        
        if 'zip_code' in data:
            valid, msg = Validators.validate_zip_code(data['zip_code'])
            if not valid:
                errors.append(msg)
        
        if 'phone' in data:
            valid, msg = Validators.validate_phone(data['phone'])
            if not valid:
                errors.append(msg)
        
        if 'email' in data:
            valid, msg = Validators.validate_email(data['email'])
            if not valid:
                errors.append(msg)
        
        if 'proposal_type' in data:
            valid, msg = Validators.validate_proposal_type(data['proposal_type'])
            if not valid:
                errors.append(msg)
        
        return len(errors) == 0, errors
