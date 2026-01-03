# install.py

import sys
import subprocess
from pathlib import Path
import argparse
import json
from logger import setup_logger
import ctypes

logger = setup_logger()


class Installer:
    def __init__(self, rig_id: str, server_url: str, api_key: str) -> None:
        self.rig_id: str = rig_id
        self.server_url: str = server_url
        self.api_key: str = api_key
        self.agent_dir: Path = Path(__file__).parent.resolve()
        self.task_name: str = "VigilantAgent"

    def _check_admin(self) -> bool:
        # Reundant
        logger.info("Checking administrator privileges")
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()

        if not is_admin:
            logger.error("Must run as Administrator")
            return False
        return True

    def _check_python_version(self) -> bool:
        # Redundant
        logger.info("Checking Python version")
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 9):
            logger.error(f"Python 3.9+ required, found {version.major}.{version.minor}")
            return False

        logger.info(f"Python {version.major}.{version.minor}.{version.micro}")
        return True

    def _install_dependencies(self) -> bool:
        logger.info("Installing Python dependencies")

        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            capture_output=True,
            cwd=str(self.agent_dir),
        )

        if result.returncode != 0:
            logger.error(f"Failed to install dependencies: {result.stderr.decode()}")
            return False
        return True

    def _update_config(self) -> bool:
        config_file = self.agent_dir / "config.json"
        logger.info(f"Trying to update configuration file at {config_file}")
        with open(config_file, "r") as f:
            config = json.load(f)

        config["rig_id"] = self.rig_id
        config["server_url"] = self.server_url
        config["api_key"] = self.api_key

        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)
        return True

    def _test_agent(self) -> bool:
        logger.info("Testing agent")

        result = subprocess.run(
            [sys.executable, "agent.py"],
            cwd=str(self.agent_dir),
            capture_output=True,
            timeout=30,
        )

        if result.returncode != 0:
            logger.error(f"Agent test failed: {result.stderr.decode()}")
            return False
        return True

    def _create_scheduled_task(self) -> bool:
        logger.info("Creating scheduled task")

        # Run silently
        python_exe = sys.executable.replace("python.exe", "pythonw.exe")
        agent_script = self.agent_dir / "agent.py"
        template_file = self.agent_dir / "task_template.xml"

        with open(template_file, "r", encoding="utf-8") as f:
            task_xml = f.read()

        task_xml = task_xml.format(
            rig_id=self.rig_id,
            python_exe=python_exe,
            agent_script=agent_script,
            working_dir=self.agent_dir,
        )

        xml_file = self.agent_dir / "task_temp.xml"
        with open(xml_file, "w", encoding="utf-8") as f:
            f.write(task_xml)

        # Delete task if already exists
        subprocess.run(
            ["schtasks", "/Delete", "/TN", self.task_name, "/F"], capture_output=True
        )

        result = subprocess.run(
            ["schtasks", "/Create", "/XML", str(xml_file), "/TN", self.task_name],
            capture_output=True,
        )

        xml_file.unlink()

        if result.returncode != 0:
            logger.error(f"Failed to create scheduled task: {result.stderr.decode()}")
            return False
        return True

    def _start_task(self) -> bool:
        logger.info("Starting agent task")

        result = subprocess.run(
            ["schtasks", "/Run", "/TN", self.task_name], capture_output=True
        )

        if result.returncode != 0:
            logger.error(f"Failed to start agent: {result.stderr.decode()}")
            return False
        return True

    def _print_summary(self) -> None:
        logger.info("=" * 60)
        logger.info("Installation Complete")
        logger.info("=" * 60)
        logger.info(f"Agent Directory:    {self.agent_dir}")
        logger.info(f"Rig ID:             {self.rig_id}")
        logger.info(f"Server URL:         {self.server_url}")
        logger.info(f"Task Name:          {self.task_name}")
        logger.info(f"Log Files:          {self.agent_dir / 'logs'}")
        logger.info("")
        logger.info("Useful Commands:")
        logger.info("Manual test:   python agent.py")
        logger.info("Check task:    schtasks /Query /TN VigilantAgent /FO LIST")
        logger.info("Uninstall:     python uninstall.py")
        logger.info("=" * 60)

    def install(self) -> bool:
        logger.info("=" * 60)
        logger.info("Vigilant Agent Installer")
        logger.info("=" * 60)
        logger.info(f"Rig ID:      {self.rig_id}")
        logger.info(f"Server URL:  {self.server_url}")
        logger.info(f"API Key:     {'*' * min(len(self.api_key), 20)}")
        logger.info("")

        steps = [
            ("Checking admin rights", self._check_admin),
            ("Checking Python version", self._check_python_version),
            ("Installing dependencies", self._install_dependencies),
            ("Updating configuration", self._update_config),
            ("Testing agent", self._test_agent),
            ("Creating scheduled task", self._create_scheduled_task),
            ("Starting agent", self._start_task),
        ]

        for step_name, step_func in steps:
            if not step_func():
                logger.error(f"Installation failed at: {step_name}")
                logger.error(
                    f"Check logs: {self.agent_dir / 'logs' / 'vigilant-installer.log'}"
                )
                return False

        self._print_summary()
        return True


def main():
    parser = argparse.ArgumentParser(
        description="Install Vigilant Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
            Example:
            py install.py --rig-id Everest --server-url https://server//name --api-key abc123
            """,
    )

    parser.add_argument("--rig-id", required=True)
    parser.add_argument("--server-url", required=True)
    parser.add_argument(
        "--api-key", required=True, help="API key for server authentication"
    )

    args = parser.parse_args()

    installer = Installer(args.rig_id, args.server_url, args.api_key)

    success = installer.install()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Installation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Installation failed: {e}")
        sys.exit(1)
