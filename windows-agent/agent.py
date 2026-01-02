# agent.py

import json
import requests
import psutil
import socket
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any
import sys
from logger import setup_logger

CONFIG_PATH = Path(__file__).parent / "config.json"

logger = setup_logger()


class Agent:
    def __init__(self, config_path: Path = CONFIG_PATH) -> None:
        self.config = self._load_config(config_path)
        self._validate_config()
        self.server_url: str = self.config["server_url"]
        self.api_key: str = self.config["api_key"]
        self.rig_id: str = self.config["rig_id"]
        self.metadata: Dict[str, Any] = self.config.get("metadata", {})

    def _load_config(self, config_path: Path) -> Dict[str, Any]:
        logger.info(f"Loading configuration from {config_path}")
        with open(config_path, "r") as f:
            return json.load(f)

    def _collect_system_status(self) -> Dict[str, Any]:
        logger.info("Collecting system status")
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_used_gb": round(psutil.virtual_memory().used / (1024**3), 2),
            "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "disk_percent": psutil.disk_usage("C:\\").percent,
            "disk_free_gb": round(psutil.disk_usage("C:\\").free / (1024**3), 2),
            "uptime_hours": round(
                (datetime.now() - boot_time).total_seconds() / 3600, 1
            ),
        }

    def _check_processes(self) -> Dict[str, str]:
        result = {}
        logger.info("Checking running processes")
        config_process_names = self.config.get("process_names", [])
        if not config_process_names:
            logger.warning("Nothing configured to check")
            return {}

        for process in psutil.process_iter(["name"]):
            try:
                process_name = process.info["name"]
                result[process_name] = "not running"
                if process_name in config_process_names:
                    logger.info(f"{process_name} is running")
                    result[process_name] = "running"
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return result

    def _get_network_info(self) -> Dict[str, str]:
        logger.info("Collecting network information")
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        return {
            "hostname": hostname,
            "ip_address": ip_address,
        }

    def collect_status(self) -> Dict[str, Any]:
        running_processes = self._check_processes()
        network_info = self._get_network_info()
        system_status = self._collect_system_status()

        status = {
            "rig_id": self.rig_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **running_processes,
            **network_info,
            **system_status,
            **self.metadata,
            "agent_version": "1.0.0",
            "os": platform.platform(),
        }

        return status

    def send_status(self, status: Dict[str, Any]):
        logger.info(f"Sending rig status to server at {self.server_url}")
        response = requests.post(
            f"{self.server_url}/api/heartbeat",
            json=status,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=15,
        )

        if response.status_code != 200:
            logger.error(
                f"Server returned status {response.status_code}\n{response.text}"
            )

    def run(self) -> None:
        logger.info(f"Agent run at {datetime.now(timezone.utc).isoformat()}")
        status = self.collect_status()
        self.send_status(status)


if __name__ == "__main__":
    try:
        agent = Agent()
        agent.run()
    except Exception as e:
        logger.error(f"Fatal error\n{e}")
        sys.exit(1)
