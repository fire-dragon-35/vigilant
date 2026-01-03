# uninstall.py

import sys
import subprocess
from logger import setup_logger
import ctypes

logger = setup_logger()


class Uninstaller:
    def __init__(self) -> None:
        self.task_name: str = "VigilantAgent"

    def _check_admin(self) -> bool:
        logger.info("Checking administrator privileges")
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()

        if not is_admin:
            logger.error("Must run as Administrator")
            return False
        return True

    def _stop_task(self) -> bool:
        logger.info("Stopping scheduled task")

        result = subprocess.run(
            ["schtasks", "/End", "/TN", self.task_name], capture_output=True
        )

        if result.returncode == 0:
            logger.info("Task stopped")
        else:
            logger.info("Task not running")

        return True

    def _delete_task(self) -> bool:
        logger.info("Removing scheduled task")

        result = subprocess.run(
            ["schtasks", "/Delete", "/TN", self.task_name, "/F"], capture_output=True
        )

        if result.returncode == 0:
            logger.info("Task removed")
            return True
        else:
            logger.warning("Task not found (may already be removed)")
            return True

    def _verify_cleanup(self) -> bool:
        logger.info("Verifying cleanup")

        result = subprocess.run(
            ["schtasks", "/Query", "/TN", self.task_name], capture_output=True
        )

        if result.returncode != 0:
            logger.info("Task successfully removed")
            return True
        else:
            logger.warning("Task still exists")
            return False

    def _print_summary(self) -> None:
        logger.info("=" * 60)
        logger.info("Uninstallation Complete")
        logger.info("=" * 60)
        logger.info("Scheduled task removed")
        logger.info("Agent files remain in current directory")
        logger.info("Delete manually if needed")
        logger.info("=" * 60)

    def uninstall(self) -> bool:
        logger.info("=" * 60)
        logger.info("Vigilant Agent Uninstaller")
        logger.info("=" * 60)
        logger.info("")

        if not self._check_admin():
            return False

        self._stop_task()
        self._delete_task()
        self._verify_cleanup()

        logger.info("")
        self._print_summary()
        return True


def main():
    uninstaller = Uninstaller()
    success = uninstaller.uninstall()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("")
        logger.info("Uninstallation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Uninstallation failed\n{e}")
        sys.exit(1)
