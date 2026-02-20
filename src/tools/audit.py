import json
import logging
from datetime import datetime
from config.settings import get_settings

settings = get_settings()

def get_audit_logger():
    """Returns a logger that writes purely JSON formatted strings to an append-only file."""
    logger = logging.getLogger("football_gravity_audit")
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    
    if not logger.handlers:
        fh = logging.FileHandler(settings.audit_log_path)
        fh.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(fh)
        
    return logger

def audit_log(event_type: str, agent: str, details: dict):
    """
    Structured zero-trust audit logging. Every graph transition and tool call
    is securely logged with a UTC timestamp.
    """
    logger = get_audit_logger()
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event_type": event_type,
        "agent": agent,
        "details": details
    }
    logger.info(json.dumps(entry))
