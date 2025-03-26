from config import MODULES
from docker import DockerClient
from docker.errors import APIError
import json

MODULE_NAME = "docker_stats"

def __mod_init__():
    return DockerStats()

class DockerStats:
    def __init__(self):
        self.url = MODULES['MODULES_CONFIG']['docker_stats']['url']
        self.docker_client = DockerClient(base_url=self.url)

    def container_status(self, name: str, all: bool):
        container = self.docker_client.containers.list(all=all, filters={'name': name})
        try:
            data = container[0].stats(decode=None, stream=False)
            cpu_stats = data['cpu_stats']
            precpu_stats = data['precpu_stats']
            cpu_delta = cpu_stats['cpu_usage']['total_usage'] - precpu_stats['cpu_usage']['total_usage']
            system_cpu_delta = cpu_stats['system_cpu_usage'] - precpu_stats['system_cpu_usage']
            actual_cpu_usage = (cpu_delta / system_cpu_delta) * cpu_stats['online_cpus'] * 100.0
            used_memory = data['memory_stats']['usage']
            available_memory = data['memory_stats']['limit']
            mem_usage = (used_memory / available_memory) * 100.0
            return {'mem': mem_usage, 'cpu': actual_cpu_usage}
        except APIError as e:
            return e.explanation
