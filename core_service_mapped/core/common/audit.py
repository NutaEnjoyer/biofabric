from sqlalchemy import text
from core.common.logging import log

def write_audit(db, actor_user_id, actor_system, action, resource, resource_id, diff_json, correlation_id):
    sql = text('INSERT INTO audit_log(actor_user_id, actor_system, action, resource, resource_id, diff_json, correlation_id, created_at) VALUES (:u,:s,:a,:r,:rid,:d,:c,NOW())')
    db.execute(sql, {'u': actor_user_id, 's': actor_system, 'a': action, 'r': resource, 'rid': str(resource_id), 'd': diff_json, 'c': correlation_id})
    db.commit()
    log('INFO','audit.write', action=action, resource=resource, resource_id=str(resource_id), actor_user_id=actor_user_id, actor_system=actor_system, correlation_id=correlation_id)
