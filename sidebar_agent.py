"""
Agentic Sidebar Controller
AI-driven action queue with executable proposals
"""

import uuid
from typing import Dict, List, Optional
from sqlalchemy import create_engine, text
from datetime import datetime
import json

class SidebarAgent:
    """
    AI agent that proposes and executes actions via the sidebar
    """
    
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
    
    def propose_action(self, tenant_id: uuid.UUID, storm_id: uuid.UUID,
                      action_type: str, ai_confidence: float,
                      ai_reasoning: str, action_params: Dict) -> uuid.UUID:
        """
        AI proposes an action to the user
        Returns action_id
        """
        action_id = uuid.uuid4()
        
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO sidebar_actions (
                    action_id, tenant_id, storm_id, action_type,
                    action_status, ai_confidence, ai_reasoning, action_params
                ) VALUES (
                    :action_id, :tenant_id, :storm_id, :action_type,
                    'proposed', :confidence, :reasoning, :params
                )
            """), {
                "action_id": str(action_id),
                "tenant_id": str(tenant_id),
                "storm_id": str(storm_id),
                "action_type": action_type,
                "confidence": ai_confidence,
                "reasoning": ai_reasoning,
                "params": json.dumps(action_params)
            })
            conn.commit()
        
        return action_id
    
    def approve_action(self, action_id: uuid.UUID, approved_by: str) -> bool:
        """User approves an AI proposal"""
        from datetime import datetime
        with self.engine.connect() as conn:
            conn.execute(text("""
                UPDATE sidebar_actions
                SET action_status = 'approved',
                    approved_at = :approved_at,
                    approved_by = :approved_by
                WHERE action_id = :action_id
                  AND action_status = 'proposed'
            """), {
                "action_id": str(action_id),
                "approved_by": approved_by,
                "approved_at": datetime.now()
            })
            conn.commit()

        return True
    
    def reject_action(self, action_id: uuid.UUID) -> bool:
        """User rejects an AI proposal"""
        with self.engine.connect() as conn:
            conn.execute(text("""
                UPDATE sidebar_actions
                SET action_status = 'rejected'
                WHERE action_id = :action_id
                  AND action_status = 'proposed'
            """), {"action_id": str(action_id)})
            conn.commit()
        
        return True
    
    def execute_action(self, action_id: uuid.UUID) -> Dict:
        """
        Execute an approved action
        Returns result summary
        """
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT action_type, action_params, tenant_id, storm_id
                FROM sidebar_actions
                WHERE action_id = :action_id
                  AND action_status = 'approved'
            """), {"action_id": str(action_id)})
            
            row = result.fetchone()
            if not row:
                return {"error": "Action not found or not approved"}
            
            action_type = row[0]
            params = json.loads(row[1])
            tenant_id = uuid.UUID(row[2])
            storm_id = uuid.UUID(row[3])
            
            # Mark as executing
            from datetime import datetime
            conn.execute(text("""
                UPDATE sidebar_actions
                SET action_status = 'executing',
                    executed_at = :executed_at
                WHERE action_id = :action_id
            """), {"action_id": str(action_id), "executed_at": datetime.now()})
            conn.commit()
        
        # Execute based on type
        try:
            if action_type == 'load_swath':
                result = self._execute_load_swath(tenant_id, storm_id, params)
            elif action_type == 'generate_routes':
                result = self._execute_generate_routes(tenant_id, storm_id, params)
            elif action_type == 'launch_sms':
                result = self._execute_launch_sms(tenant_id, storm_id, params)
            elif action_type == 'calculate_tam':
                result = self._execute_calculate_tam(tenant_id, storm_id, params)
            else:
                result = {"error": f"Unknown action type: {action_type}"}
            
            # Mark as completed
            from datetime import datetime
            with self.engine.connect() as conn:
                conn.execute(text("""
                    UPDATE sidebar_actions
                    SET action_status = 'completed',
                        completed_at = :completed_at,
                        result_summary = :result
                    WHERE action_id = :action_id
                """), {
                    "action_id": str(action_id),
                    "result": json.dumps(result),
                    "completed_at": datetime.now()
                })
                conn.commit()
            
            return result
        
        except Exception as e:
            # Mark as failed
            with self.engine.connect() as conn:
                conn.execute(text("""
                    UPDATE sidebar_actions
                    SET action_status = 'failed',
                        error_message = :error
                    WHERE action_id = :action_id
                """), {
                    "action_id": str(action_id),
                    "error": str(e)
                })
                conn.commit()
            
            return {"error": str(e)}
    
    def _execute_load_swath(self, tenant_id: uuid.UUID, storm_id: uuid.UUID, 
                           params: Dict) -> Dict:
        """Execute Earth-2 swath loading"""
        from earth2_integration import Earth2Ingestion
        
        ingestion = Earth2Ingestion(str(self.engine.url))
        
        zones = ingestion.ingest_storm_swath(
            tenant_id, storm_id,
            params.get('center_lat', 32.7767),
            params.get('center_lon', -96.7970),
            params.get('radius_km', 50)
        )
        
        enriched = ingestion.enrich_properties_with_damage(tenant_id, storm_id)
        
        return {
            "zones_created": zones,
            "properties_enriched": enriched
        }
    
    def _execute_generate_routes(self, tenant_id: uuid.UUID, storm_id: uuid.UUID,
                                params: Dict) -> Dict:
        """Execute route generation"""
        from route_builder import RouteBuilder
        
        builder = RouteBuilder(str(tenant_id), str(storm_id))
        routes = builder.generate_routes(
            params.get('max_per_route', 50),
            params.get('zip_filter')
        )
        
        return {
            "routes_created": len(routes),
            "route_ids": [str(r['route_id']) for r in routes]
        }
    
    def _execute_launch_sms(self, tenant_id: uuid.UUID, storm_id: uuid.UUID,
                           params: Dict) -> Dict:
        """Execute SMS campaign launch"""
        # Placeholder - integrate with Twilio/etc
        return {
            "messages_queued": params.get('recipient_count', 0),
            "campaign_id": str(uuid.uuid4())
        }
    
    def _execute_calculate_tam(self, tenant_id: uuid.UUID, storm_id: uuid.UUID,
                              params: Dict) -> Dict:
        """Execute TAM calculation"""
        from markov_engine import MarkovEngine
        
        engine = MarkovEngine(str(self.engine.url))
        
        zip_code = params.get('zip_code')
        tam = engine.calculate_tam(tenant_id, storm_id, zip_code)
        
        return {
            "zip_code": zip_code,
            "tam_usd": tam
        }
    
    def get_action_queue(self, tenant_id: uuid.UUID, storm_id: uuid.UUID,
                        limit: int = 10) -> List[Dict]:
        """
        Get pending actions for sidebar display
        Sorted by AI confidence
        """
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    action_id,
                    action_type,
                    action_status,
                    ai_confidence,
                    ai_reasoning,
                    action_params,
                    proposed_at
                FROM sidebar_actions
                WHERE tenant_id = :tenant_id
                  AND storm_id = :storm_id
                  AND action_status IN ('proposed', 'approved', 'executing')
                ORDER BY ai_confidence DESC, proposed_at ASC
                LIMIT :limit
            """), {
                "tenant_id": str(tenant_id),
                "storm_id": str(storm_id),
                "limit": limit
            })
            
            return [dict(row._mapping) for row in result.fetchall()]
    
    def auto_propose_from_markov(self, tenant_id: uuid.UUID, storm_id: uuid.UUID) -> List[uuid.UUID]:
        """
        Automatically propose actions based on Markov state transitions
        """
        from markov_engine import MarkovEngine
        
        markov = MarkovEngine(str(self.engine.url))
        top_zips = markov.get_top_opportunity_zips(tenant_id, storm_id, limit=5)
        
        action_ids = []
        
        for zip_data in top_zips:
            if zip_data['current_state'] == 'recovery':
                # Propose route generation
                action_id = self.propose_action(
                    tenant_id, storm_id,
                    action_type='generate_routes',
                    ai_confidence=0.85,
                    ai_reasoning=f"ZIP {zip_data['zip_code']} entered recovery window with ${zip_data['estimated_tam_usd']:,.0f} TAM. High-value canvassing opportunity.",
                    action_params={
                        'zip_filter': [zip_data['zip_code']],
                        'max_per_route': 50
                    }
                )
                action_ids.append(action_id)
        
        return action_ids


if __name__ == "__main__":
    # Demo
    agent = SidebarAgent("postgresql://stormops:password@localhost:5432/stormops")
    
    tenant_id = uuid.uuid4()
    storm_id = uuid.uuid4()
    
    # AI proposes loading Earth-2 data
    action_id = agent.propose_action(
        tenant_id, storm_id,
        action_type='load_swath',
        ai_confidence=0.92,
        ai_reasoning="Earth-2 detected 2.5\" hail in DFW. Loading high-resolution damage swath.",
        action_params={
            'center_lat': 32.7767,
            'center_lon': -96.7970,
            'radius_km': 50
        }
    )
    
    print(f"✅ AI proposed action: {action_id}")
    
    # User approves
    agent.approve_action(action_id, approved_by="crew_chief")
    print(f"✅ Action approved")
    
    # Execute
    result = agent.execute_action(action_id)
    print(f"✅ Execution result: {result}")
    
    # Get queue
    queue = agent.get_action_queue(tenant_id, storm_id)
    print(f"✅ Action queue: {len(queue)} items")
