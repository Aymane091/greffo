import logging

logger = logging.getLogger("greffo.audit")


async def log_action(action: str, resource_type: str, resource_id: str, org_id: str) -> None:
    # TODO: persist to audit_logs table (migration pending)
    logger.info(
        "%s %s:%s org=%s",
        action,
        resource_type,
        resource_id,
        org_id,
    )
