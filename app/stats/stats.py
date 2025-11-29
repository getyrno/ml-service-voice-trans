import time
from collections import defaultdict

stats = {
    "total_requests": 0,
    "success": 0,
    "errors": 0,
    "invalid_type": 0,
    "empty_files": 0,
    "avg_processing_time": 0.0,
}

processing_times = []
