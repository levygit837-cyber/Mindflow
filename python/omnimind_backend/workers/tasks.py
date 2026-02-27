from omnimind_backend.mind.supervisor import session_supervisor


def run_session_supervisor_job(job_id: str) -> None:
    session_supervisor.run_now(job_id)
