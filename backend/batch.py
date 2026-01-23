"""Batch processing for multiple questions through the council."""

import json
import os
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from .council import run_full_council
from .config import DATA_DIR

# Batch jobs directory
BATCH_DIR = os.path.join(DATA_DIR, "batch_jobs")


def ensure_batch_dir():
    """Ensure the batch jobs directory exists."""
    Path(BATCH_DIR).mkdir(parents=True, exist_ok=True)


def get_batch_job_path(job_id: str) -> str:
    """Get the file path for a batch job."""
    return os.path.join(BATCH_DIR, f"{job_id}.json")


class BatchJob:
    """Represents a batch processing job."""

    def __init__(self, job_id: str, questions: List[str]):
        """
        Initialize a batch job.

        Args:
            job_id: Unique identifier for the job
            questions: List of questions to process
        """
        self.job_id = job_id
        self.questions = questions
        self.total = len(questions)
        self.completed = 0
        self.status = "pending"  # pending, running, completed, failed, cancelled
        self.results = []
        self.created_at = datetime.utcnow().isoformat()
        self.started_at = None
        self.completed_at = None
        self.error = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert batch job to dictionary."""
        return {
            "job_id": self.job_id,
            "questions": self.questions,
            "total": self.total,
            "completed": self.completed,
            "status": self.status,
            "results": self.results,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "progress_percentage": (self.completed / self.total * 100) if self.total > 0 else 0
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BatchJob":
        """Create BatchJob from dictionary."""
        job = cls(data["job_id"], data["questions"])
        job.total = data["total"]
        job.completed = data["completed"]
        job.status = data["status"]
        job.results = data["results"]
        job.created_at = data["created_at"]
        job.started_at = data.get("started_at")
        job.completed_at = data.get("completed_at")
        job.error = data.get("error")
        return job

    def save(self):
        """Save batch job to disk."""
        ensure_batch_dir()
        path = get_batch_job_path(self.job_id)
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, job_id: str) -> Optional["BatchJob"]:
        """Load batch job from disk."""
        path = get_batch_job_path(job_id)
        if not os.path.exists(path):
            return None

        with open(path, 'r') as f:
            data = json.load(f)
            return cls.from_dict(data)

    async def process(self):
        """
        Process all questions in the batch job.

        This runs the full council deliberation for each question sequentially
        and stores all results.
        """
        try:
            self.status = "running"
            self.started_at = datetime.utcnow().isoformat()
            self.save()

            for i, question in enumerate(self.questions):
                # Check if job was cancelled
                if self.status == "cancelled":
                    break

                try:
                    # Run full council for this question
                    result = await run_full_council(question)

                    # Store the result
                    self.results.append({
                        "question": question,
                        "question_index": i,
                        "stage1": result["stage1"],
                        "stage2": result["stage2"],
                        "stage3": result["stage3"],
                        "metadata": result.get("metadata", {}),
                        "processed_at": datetime.utcnow().isoformat(),
                        "success": True,
                        "error": None
                    })

                    self.completed += 1

                except Exception as e:
                    # Store error but continue processing other questions
                    self.results.append({
                        "question": question,
                        "question_index": i,
                        "stage1": [],
                        "stage2": [],
                        "stage3": {},
                        "metadata": {},
                        "processed_at": datetime.utcnow().isoformat(),
                        "success": False,
                        "error": str(e)
                    })

                    self.completed += 1

                # Save progress after each question
                self.save()

            # Mark as completed if not cancelled
            if self.status != "cancelled":
                self.status = "completed"
                self.completed_at = datetime.utcnow().isoformat()

            self.save()

        except Exception as e:
            # Job-level error
            self.status = "failed"
            self.error = str(e)
            self.completed_at = datetime.utcnow().isoformat()
            self.save()

    def cancel(self):
        """Cancel the batch job."""
        if self.status in ["pending", "running"]:
            self.status = "cancelled"
            self.completed_at = datetime.utcnow().isoformat()
            self.save()


def create_batch_job(job_id: str, questions: List[str]) -> BatchJob:
    """
    Create a new batch job.

    Args:
        job_id: Unique identifier for the job
        questions: List of questions to process

    Returns:
        BatchJob instance
    """
    job = BatchJob(job_id, questions)
    job.save()
    return job


def list_batch_jobs() -> List[Dict[str, Any]]:
    """
    List all batch jobs.

    Returns:
        List of batch job metadata dicts
    """
    ensure_batch_dir()

    jobs = []
    for filename in os.listdir(BATCH_DIR):
        if filename.endswith('.json'):
            job_id = filename[:-5]  # Remove .json extension
            job = BatchJob.load(job_id)
            if job:
                jobs.append(job.to_dict())

    # Sort by creation time, newest first
    jobs.sort(key=lambda x: x["created_at"], reverse=True)

    return jobs


def delete_batch_job(job_id: str) -> bool:
    """
    Delete a batch job.

    Args:
        job_id: Batch job identifier

    Returns:
        True if deleted, False if not found
    """
    path = get_batch_job_path(job_id)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False


async def run_batch_job(job_id: str):
    """
    Run a batch job asynchronously.

    Args:
        job_id: Batch job identifier
    """
    job = BatchJob.load(job_id)
    if job:
        await job.process()
