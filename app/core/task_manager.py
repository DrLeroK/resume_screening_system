"""
Background task management for async processing
"""

import asyncio
from typing import Dict, Any, Callable, Optional
from datetime import datetime
from uuid import uuid4
from loguru import logger
import traceback

from ..config import settings
from ..models.enums import ResumeStatus

class TaskManager:
    """
    Manages background tasks for resume processing and matching
    """
    
    def __init__(self):
        self.tasks: Dict[str, Dict] = {}
        self.task_queue = asyncio.Queue()
        self.workers = []
        self.running = False
    
    async def start(self):
        """Start task workers"""
        if self.running:
            logger.warning("Task manager already running")
            return
        
        self.running = True
        
        # Create worker pool
        for i in range(settings.background_workers):
            worker = asyncio.create_task(self._worker(i))
            self.workers.append(worker)
            logger.info(f"Started task worker {i}")
    
    async def stop(self):
        """Stop all workers"""
        self.running = False
        
        # Wait for queue to empty
        await self.task_queue.join()
        
        # Cancel workers
        for worker in self.workers:
            worker.cancel()
        
        await asyncio.gather(*self.workers, return_exceptions=True)
        logger.info("All task workers stopped")
    
    def add_task(
        self,
        task_id: str,
        task_type: str,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None
    ):
        """
        Add a task to the queue
        
        Args:
            task_id: Unique identifier for the task
            task_type: Type of task (parse, match, bias)
            func: Async function to execute
            args: Positional arguments
            kwargs: Keyword arguments
        """
        if kwargs is None:
            kwargs = {}
        
        task = {
            'id': task_id,
            'type': task_type,
            'func': func,
            'args': args,
            'kwargs': kwargs,
            'status': 'pending',
            'created_at': datetime.now(),
            'started_at': None,
            'completed_at': None,
            'error': None
        }
        
        self.tasks[task_id] = task
        self.task_queue.put_nowait(task)
        logger.info(f"Task {task_id} ({task_type}) added to queue")
    
    async def _worker(self, worker_id: int):
        """Worker process that consumes tasks from queue"""
        logger.info(f"Worker {worker_id} started")
        
        while self.running:
            try:
                # Get task from queue (with timeout)
                task = await asyncio.wait_for(
                    self.task_queue.get(), 
                    timeout=1.0
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            
            try:
                # Update task status
                task['status'] = 'processing'
                task['started_at'] = datetime.now()
                
                logger.info(f"Worker {worker_id} processing task {task['id']}")
                
                # Execute task
                await task['func'](*task['args'], **task['kwargs'])
                
                # Update completion status
                task['status'] = 'completed'
                task['completed_at'] = datetime.now()
                
                logger.info(f"Worker {worker_id} completed task {task['id']}")
                
            except Exception as e:
                # Handle error
                task['status'] = 'failed'
                task['completed_at'] = datetime.now()
                task['error'] = {
                    'message': str(e),
                    'traceback': traceback.format_exc()
                }
                
                logger.error(f"Worker {worker_id} failed task {task['id']}: {str(e)}")
            
            finally:
                self.task_queue.task_done()
        
        logger.info(f"Worker {worker_id} stopped")
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get status of a specific task"""
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        
        return {
            'id': task['id'],
            'type': task['type'],
            'status': task['status'],
            'created_at': task['created_at'].isoformat(),
            'started_at': task['started_at'].isoformat() if task['started_at'] else None,
            'completed_at': task['completed_at'].isoformat() if task['completed_at'] else None,
            'error': task['error']
        }
    
    def get_queue_size(self) -> int:
        """Get number of pending tasks"""
        return self.task_queue.qsize()
    
    def get_stats(self) -> Dict:
        """Get task manager statistics"""
        total = len(self.tasks)
        completed = sum(1 for t in self.tasks.values() if t['status'] == 'completed')
        failed = sum(1 for t in self.tasks.values() if t['status'] == 'failed')
        pending = sum(1 for t in self.tasks.values() if t['status'] == 'pending')
        processing = sum(1 for t in self.tasks.values() if t['status'] == 'processing')
        
        return {
            'total_tasks': total,
            'completed': completed,
            'failed': failed,
            'pending': pending,
            'processing': processing,
            'queue_size': self.get_queue_size(),
            'workers': len(self.workers),
            'running': self.running
        }

# Global task manager instance
task_manager = TaskManager()