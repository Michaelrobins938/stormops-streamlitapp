"""
Forecast Monitor
Automated alerts for forecast threshold breaches.
"""

import psycopg2
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ForecastMonitor:
    """
    Monitors forecast data and triggers alerts.
    """
    
    # Alert thresholds
    ALERT_THRESHOLDS = {
        'severe_probability': 0.15,  # 15% severe weather probability
        'hail_probability': 0.20,    # 20% hail probability
        'wind_speed_mph': 50,        # 50 mph wind
    }
    
    def __init__(self, db_host='localhost', db_name='stormops', db_user='postgres', db_password='password'):
        self.db_host = db_host
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password
        self.conn = None
    
    def connect(self):
        """Connect to database."""
        self.conn = psycopg2.connect(
            host=self.db_host,
            database=self.db_name,
            user=self.db_user,
            password=self.db_password,
        )
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
    
    def check_forecast_alerts(self, event_id: str, forecast_data: Dict) -> List[Dict]:
        """
        Check forecast data against alert thresholds.
        
        Args:
            event_id: Event ID
            forecast_data: Dict with forecast metrics
                - day: Day number (1-7)
                - severe_probability: 0-1
                - hail_probability: 0-1
                - max_wind_mph: Wind speed
        
        Returns:
            List of triggered alerts
        """
        
        alerts = []
        
        # Check severe weather probability
        if forecast_data.get('severe_probability', 0) > self.ALERT_THRESHOLDS['severe_probability']:
            alerts.append({
                'type': 'severe_weather',
                'severity': 'high' if forecast_data['severe_probability'] > 0.3 else 'medium',
                'message': f"Severe weather probability: {forecast_data['severe_probability']*100:.0f}% on Day {forecast_data.get('day', '?')}",
                'action': 'pre_position_crews',
                'probability': forecast_data['severe_probability'],
            })
        
        # Check hail probability
        if forecast_data.get('hail_probability', 0) > self.ALERT_THRESHOLDS['hail_probability']:
            alerts.append({
                'type': 'hail_threat',
                'severity': 'high' if forecast_data['hail_probability'] > 0.4 else 'medium',
                'message': f"Hail probability: {forecast_data['hail_probability']*100:.0f}% on Day {forecast_data.get('day', '?')}",
                'action': 'activate_lead_gen',
                'probability': forecast_data['hail_probability'],
            })
        
        # Check wind speed
        if forecast_data.get('max_wind_mph', 0) > self.ALERT_THRESHOLDS['wind_speed_mph']:
            alerts.append({
                'type': 'high_wind',
                'severity': 'high' if forecast_data['max_wind_mph'] > 60 else 'medium',
                'message': f"High wind: {forecast_data['max_wind_mph']} mph on Day {forecast_data.get('day', '?')}",
                'action': 'activate_lead_gen',
                'wind_speed': forecast_data['max_wind_mph'],
            })
        
        # Log alerts
        for alert in alerts:
            logger.warning(f"Alert: {alert['message']}")
        
        return alerts
    
    def trigger_proposal_from_alert(
        self,
        event_id: str,
        alert: Dict,
        zip_code: str,
    ) -> Optional[str]:
        """
        Trigger a Proposal based on an alert.
        
        Args:
            event_id: Event ID
            alert: Alert dict
            zip_code: Target ZIP code
        
        Returns:
            Proposal ID if created
        """
        
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        
        try:
            action = alert.get('action')
            
            if action == 'pre_position_crews':
                # Create a "Pre-Position Crews" proposal
                proposal_type = 'crew_positioning'
                expected_leads = 0
                expected_value = 50000  # Operational cost
            elif action == 'activate_lead_gen':
                # Create a lead gen proposal
                proposal_type = 'lead_gen'
                expected_leads = 500
                expected_value = 2500000
            else:
                return None
            
            proposal_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO proposals (
                    id, event_id, proposal_type, target_zip,
                    expected_leads, expected_value_usd, blast_radius, status, created_by
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                proposal_id,
                event_id,
                proposal_type,
                zip_code,
                expected_leads,
                expected_value,
                1000,
                'pending',
                'forecast_monitor',
            ))
            
            self.conn.commit()
            logger.info(f"Created proposal from alert: {proposal_id}")
            return proposal_id
        
        except Exception as e:
            logger.error(f"Error triggering proposal: {e}")
            self.conn.rollback()
            return None
        finally:
            cursor.close()
    
    def get_7day_forecast_summary(self, forecast_data: List[Dict]) -> Dict:
        """
        Summarize 7-day forecast.
        
        Args:
            forecast_data: List of daily forecast dicts
        
        Returns:
            Summary dict
        """
        
        summary = {
            'days_with_severe': 0,
            'days_with_hail': 0,
            'peak_severe_probability': 0,
            'peak_hail_probability': 0,
            'peak_wind_mph': 0,
            'operational_window': None,
        }
        
        for day_forecast in forecast_data:
            if day_forecast.get('severe_probability', 0) > self.ALERT_THRESHOLDS['severe_probability']:
                summary['days_with_severe'] += 1
                summary['peak_severe_probability'] = max(
                    summary['peak_severe_probability'],
                    day_forecast['severe_probability']
                )
            
            if day_forecast.get('hail_probability', 0) > self.ALERT_THRESHOLDS['hail_probability']:
                summary['days_with_hail'] += 1
                summary['peak_hail_probability'] = max(
                    summary['peak_hail_probability'],
                    day_forecast['hail_probability']
                )
            
            summary['peak_wind_mph'] = max(
                summary['peak_wind_mph'],
                day_forecast.get('max_wind_mph', 0)
            )
        
        # Determine operational window
        if summary['days_with_hail'] > 0:
            summary['operational_window'] = f"{summary['days_with_hail']} days with hail threat"
        elif summary['days_with_severe'] > 0:
            summary['operational_window'] = f"{summary['days_with_severe']} days with severe weather"
        else:
            summary['operational_window'] = "No significant threats"
        
        return summary
    
    def get_alert_history(self, event_id: str, limit: int = 100) -> List[Dict]:
        """
        Get alert history for an event.
        
        Args:
            event_id: Event ID
            limit: Max alerts to return
        
        Returns:
            List of alerts
        """
        
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                SELECT id, proposal_type, expected_value_usd, status, created_at
                FROM proposals
                WHERE event_id = %s AND proposal_type IN ('crew_positioning', 'lead_gen')
                ORDER BY created_at DESC
                LIMIT %s
            """, (event_id, limit))
            
            alerts = []
            for row in cursor.fetchall():
                alerts.append({
                    'proposal_id': row[0],
                    'type': row[1],
                    'value': row[2],
                    'status': row[3],
                    'created_at': row[4],
                })
            
            return alerts
        
        except Exception as e:
            logger.error(f"Error getting alert history: {e}")
            return []
        finally:
            cursor.close()


# Example usage
if __name__ == '__main__':
    monitor = ForecastMonitor()
    
    # Mock 7-day forecast
    forecast_data = [
        {'day': 1, 'severe_probability': 0.02, 'hail_probability': 0.01, 'max_wind_mph': 15},
        {'day': 2, 'severe_probability': 0.05, 'hail_probability': 0.03, 'max_wind_mph': 20},
        {'day': 3, 'severe_probability': 0.25, 'hail_probability': 0.30, 'max_wind_mph': 55},  # Alert!
        {'day': 4, 'severe_probability': 0.10, 'hail_probability': 0.08, 'max_wind_mph': 25},
        {'day': 5, 'severe_probability': 0.02, 'hail_probability': 0.01, 'max_wind_mph': 15},
        {'day': 6, 'severe_probability': 0.01, 'hail_probability': 0.00, 'max_wind_mph': 10},
        {'day': 7, 'severe_probability': 0.03, 'hail_probability': 0.02, 'max_wind_mph': 12},
    ]
    
    # Check each day for alerts
    print("Checking 7-day forecast for alerts:\n")
    all_alerts = []
    for day_forecast in forecast_data:
        alerts = monitor.check_forecast_alerts('test-event-1', day_forecast)
        if alerts:
            print(f"Day {day_forecast['day']}:")
            for alert in alerts:
                print(f"  - {alert['message']}")
                all_alerts.extend(alerts)
    
    # Get summary
    summary = monitor.get_7day_forecast_summary(forecast_data)
    print(f"\n7-Day Summary:")
    print(f"  Days with severe: {summary['days_with_severe']}")
    print(f"  Days with hail: {summary['days_with_hail']}")
    print(f"  Peak severe probability: {summary['peak_severe_probability']*100:.0f}%")
    print(f"  Peak hail probability: {summary['peak_hail_probability']*100:.0f}%")
    print(f"  Operational window: {summary['operational_window']}")
