"""
Billing and Monetization Framework
Usage tracking, pricing tiers, and invoice generation
"""

from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
from typing import Dict, List
import uuid
import json

# Pricing tiers
PRICING_TIERS = {
    'trial': {
        'name': 'Trial',
        'monthly_base': 0,
        'included_storms': 1,
        'included_properties': 500,
        'included_model_calls': 1000,
        'overage_storm': 0,
        'overage_property': 0,
        'overage_model_call': 0,
        'features': ['basic_uplift', 'basic_attribution']
    },
    'standard': {
        'name': 'Standard',
        'monthly_base': 500,
        'included_storms': 5,
        'included_properties': 5000,
        'included_model_calls': 10000,
        'overage_storm': 100,
        'overage_property': 0.10,
        'overage_model_call': 0.01,
        'features': ['basic_uplift', 'basic_attribution', 'policy_control', 'experiments']
    },
    'enterprise': {
        'name': 'Enterprise',
        'monthly_base': 2000,
        'included_storms': 999,
        'included_properties': 999999,
        'included_model_calls': 999999,
        'overage_storm': 0,
        'overage_property': 0,
        'overage_model_call': 0,
        'features': ['all']
    }
}

class BillingManager:
    """Manage tenant billing and usage."""
    
    def __init__(self, db_url: str = 'postgresql://stormops:password@localhost:5432/stormops'):
        self.engine = create_engine(db_url)
        self._init_tables()
    
    def _init_tables(self):
        """Create billing tables."""
        with self.engine.begin() as conn:
            # Usage events
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS usage_events (
                    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
                    event_type TEXT NOT NULL,
                    quantity FLOAT NOT NULL DEFAULT 1,
                    metadata JSONB,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """))
            
            # Invoices
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS invoices (
                    invoice_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
                    period_start DATE NOT NULL,
                    period_end DATE NOT NULL,
                    base_amount FLOAT NOT NULL,
                    overage_amount FLOAT NOT NULL,
                    total_amount FLOAT NOT NULL,
                    usage_summary JSONB NOT NULL,
                    status TEXT NOT NULL DEFAULT 'draft',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """))
            
            # Feature flags
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS tenant_features (
                    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
                    feature_name TEXT NOT NULL,
                    enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    PRIMARY KEY (tenant_id, feature_name)
                )
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_usage_events_tenant_time 
                ON usage_events(tenant_id, timestamp)
            """))
    
    def log_usage(self, tenant_id: uuid.UUID, event_type: str, quantity: float = 1, metadata: Dict = None):
        """Log a usage event."""
        
        with self.engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO usage_events (tenant_id, event_type, quantity, metadata)
                VALUES (:tid, :type, :qty, :meta)
            """), {
                'tid': tenant_id,
                'type': event_type,
                'qty': quantity,
                'meta': json.dumps(metadata) if metadata else None
            })
    
    def get_usage_summary(self, tenant_id: uuid.UUID, start_date: datetime, end_date: datetime) -> Dict:
        """Get usage summary for billing period."""
        
        with self.engine.connect() as conn:
            usage = conn.execute(text("""
                SELECT 
                    event_type,
                    SUM(quantity) as total
                FROM usage_events
                WHERE tenant_id = :tid
                  AND timestamp >= :start
                  AND timestamp < :end
                GROUP BY event_type
            """), {
                'tid': tenant_id,
                'start': start_date,
                'end': end_date
            }).fetchall()
        
        return {u[0]: u[1] for u in usage}
    
    def calculate_invoice(self, tenant_id: uuid.UUID, period_start: datetime, period_end: datetime) -> Dict:
        """Calculate invoice for billing period."""
        
        # Get tenant tier
        with self.engine.connect() as conn:
            tier_name = conn.execute(text("""
                SELECT tier FROM tenants WHERE tenant_id = :tid
            """), {'tid': tenant_id}).scalar()
        
        tier = PRICING_TIERS.get(tier_name, PRICING_TIERS['standard'])
        
        # Get usage
        usage = self.get_usage_summary(tenant_id, period_start, period_end)
        
        # Calculate base
        base_amount = tier['monthly_base']
        
        # Calculate overages
        overages = {}
        overage_amount = 0
        
        # Storms
        storms = usage.get('storm_created', 0)
        if storms > tier['included_storms']:
            storm_overage = (storms - tier['included_storms']) * tier['overage_storm']
            overages['storms'] = storm_overage
            overage_amount += storm_overage
        
        # Properties
        properties = usage.get('property_created', 0)
        if properties > tier['included_properties']:
            prop_overage = (properties - tier['included_properties']) * tier['overage_property']
            overages['properties'] = prop_overage
            overage_amount += prop_overage
        
        # Model calls
        model_calls = usage.get('model_call', 0)
        if model_calls > tier['included_model_calls']:
            model_overage = (model_calls - tier['included_model_calls']) * tier['overage_model_call']
            overages['model_calls'] = model_overage
            overage_amount += model_overage
        
        total_amount = base_amount + overage_amount
        
        return {
            'tenant_id': str(tenant_id),
            'tier': tier_name,
            'period_start': period_start.isoformat(),
            'period_end': period_end.isoformat(),
            'base_amount': base_amount,
            'overage_amount': overage_amount,
            'total_amount': total_amount,
            'usage': usage,
            'overages': overages,
            'included': {
                'storms': tier['included_storms'],
                'properties': tier['included_properties'],
                'model_calls': tier['included_model_calls']
            }
        }
    
    def create_invoice(self, tenant_id: uuid.UUID, period_start: datetime, period_end: datetime) -> uuid.UUID:
        """Create an invoice."""
        
        invoice_data = self.calculate_invoice(tenant_id, period_start, period_end)
        invoice_id = uuid.uuid4()
        
        with self.engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO invoices 
                (invoice_id, tenant_id, period_start, period_end, 
                 base_amount, overage_amount, total_amount, usage_summary, status)
                VALUES (:iid, :tid, :start, :end, :base, :overage, :total, :summary, 'draft')
            """), {
                'iid': invoice_id,
                'tid': tenant_id,
                'start': period_start,
                'end': period_end,
                'base': invoice_data['base_amount'],
                'overage': invoice_data['overage_amount'],
                'total': invoice_data['total_amount'],
                'summary': json.dumps(invoice_data)
            })
        
        return invoice_id
    
    def enable_feature(self, tenant_id: uuid.UUID, feature_name: str):
        """Enable a feature for tenant."""
        
        with self.engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO tenant_features (tenant_id, feature_name, enabled)
                VALUES (:tid, :feature, TRUE)
                ON CONFLICT (tenant_id, feature_name) 
                DO UPDATE SET enabled = TRUE
            """), {'tid': tenant_id, 'feature': feature_name})
    
    def has_feature(self, tenant_id: uuid.UUID, feature_name: str) -> bool:
        """Check if tenant has feature enabled."""
        
        with self.engine.connect() as conn:
            # Check tier features
            tier_name = conn.execute(text("""
                SELECT tier FROM tenants WHERE tenant_id = :tid
            """), {'tid': tenant_id}).scalar()
            
            tier = PRICING_TIERS.get(tier_name, PRICING_TIERS['standard'])
            if 'all' in tier['features'] or feature_name in tier['features']:
                return True
            
            # Check explicit feature flags
            enabled = conn.execute(text("""
                SELECT enabled FROM tenant_features
                WHERE tenant_id = :tid AND feature_name = :feature
            """), {'tid': tenant_id, 'feature': feature_name}).scalar()
            
            return enabled or False
    
    def get_billing_dashboard(self, tenant_id: uuid.UUID) -> Dict:
        """Get billing dashboard for tenant."""
        
        # Current month
        now = datetime.now()
        period_start = datetime(now.year, now.month, 1)
        period_end = (period_start + timedelta(days=32)).replace(day=1)
        
        # Calculate current invoice
        invoice = self.calculate_invoice(tenant_id, period_start, period_end)
        
        # Get tier info
        with self.engine.connect() as conn:
            tier_name = conn.execute(text("""
                SELECT tier FROM tenants WHERE tenant_id = :tid
            """), {'tid': tenant_id}).scalar()
        
        tier = PRICING_TIERS.get(tier_name, PRICING_TIERS['standard'])
        
        return {
            'tenant_id': str(tenant_id),
            'tier': tier_name,
            'current_period': {
                'start': period_start.isoformat(),
                'end': period_end.isoformat(),
                'base_amount': invoice['base_amount'],
                'overage_amount': invoice['overage_amount'],
                'total_amount': invoice['total_amount']
            },
            'usage': invoice['usage'],
            'included': invoice['included'],
            'overages': invoice['overages'],
            'features': tier['features']
        }


if __name__ == '__main__':
    print("=" * 60)
    print("BILLING MANAGER - SETUP & TEST")
    print("=" * 60)
    
    billing = BillingManager()
    
    # Test tenant
    tenant_id = uuid.UUID('00000000-0000-0000-0000-000000000000')
    
    # Log some usage
    print("\nLogging usage events...")
    billing.log_usage(tenant_id, 'storm_created', 1)
    billing.log_usage(tenant_id, 'property_created', 100)
    billing.log_usage(tenant_id, 'model_call', 500)
    
    # Get dashboard
    print("\nBilling Dashboard:")
    dashboard = billing.get_billing_dashboard(tenant_id)
    
    print(f"  Tier: {dashboard['tier']}")
    print(f"  Current Period: {dashboard['current_period']['start']} to {dashboard['current_period']['end']}")
    print(f"  Base: ${dashboard['current_period']['base_amount']:.2f}")
    print(f"  Overage: ${dashboard['current_period']['overage_amount']:.2f}")
    print(f"  Total: ${dashboard['current_period']['total_amount']:.2f}")
    
    print(f"\n  Usage:")
    for event_type, count in dashboard['usage'].items():
        print(f"    {event_type}: {count}")
    
    print(f"\n  Included:")
    for resource, limit in dashboard['included'].items():
        print(f"    {resource}: {limit}")
    
    # Test feature flags
    print("\nFeature Flags:")
    features = ['basic_uplift', 'policy_control', 'premium_analytics']
    for feature in features:
        enabled = billing.has_feature(tenant_id, feature)
        print(f"  {feature}: {'✅' if enabled else '❌'}")
    
    print("\n✅ Billing manager ready")
