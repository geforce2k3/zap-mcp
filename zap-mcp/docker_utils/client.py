"""
Docker 命令執行客戶端
"""
import subprocess
import json
from typing import Optional, List, Tuple

from core.config import SHARED_VOLUME_NAME, SCAN_CONTAINER_NAME, REPORTER_IMAGE, ZAP_IMAGE
from core.logging_config import logger


class DockerClient:
    """Docker 命令執行封裝類"""

    @staticmethod
    def run_command(cmd: List[str], check: bool = False) -> Tuple[int, str, str]:
        """
        執行 Docker 命令

        Args:
            cmd: 命令列表
            check: 是否檢查返回碼

        Returns:
            Tuple[returncode, stdout, stderr]
        """
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=check)
            return result.returncode, result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            return e.returncode, e.stdout or "", e.stderr or ""

    @staticmethod
    def is_container_running(container_name: str = SCAN_CONTAINER_NAME) -> bool:
        """檢查容器是否正在運行"""
        cmd = ["docker", "ps", "-q", "-f", f"name={container_name}"]
        returncode, stdout, _ = DockerClient.run_command(cmd)
        return bool(stdout.strip())

    @staticmethod
    def remove_container(container_name: str = SCAN_CONTAINER_NAME) -> bool:
        """強制移除容器"""
        cmd = ["docker", "rm", "-f", container_name]
        returncode, _, _ = DockerClient.run_command(cmd)
        return returncode == 0

    @staticmethod
    def get_container_logs(container_name: str, tail: int = 20) -> str:
        """取得容器日誌"""
        cmd = ["docker", "logs", "--tail", str(tail), container_name]
        _, stdout, stderr = DockerClient.run_command(cmd)
        return stdout + stderr

    @staticmethod
    def run_zap_scan(
        target_url: str,
        scan_type: str = "baseline",
        aggressive: bool = False,
        zap_configs: Optional[List[str]] = None
    ) -> Tuple[bool, str]:
        """
        啟動 ZAP 掃描容器

        Args:
            target_url: 掃描目標 URL
            scan_type: 掃描類型 (baseline/full)
            aggressive: 是否使用積極模式
            zap_configs: 額外的 ZAP 配置

        Returns:
            Tuple[成功與否, 訊息]
        """
        script_name = "zap-full-scan.py" if scan_type == "full" else "zap-baseline.py"

        cmd = [
            "docker", "run", "-d",
            "--name", SCAN_CONTAINER_NAME,
            "-u", "0",
            "--dns", "8.8.8.8",
            "-v", f"{SHARED_VOLUME_NAME}:/zap/wrk:rw",
            "-t", ZAP_IMAGE,
            script_name,
            "-t", target_url,
            "-J", "ZAP-Report.json",
            "-I"
        ]

        if aggressive:
            cmd.extend(["-j", "-a"])

        if zap_configs:
            cmd.extend(["-z", " ".join(zap_configs)])

        logger.info(f"執行 ZAP 掃描命令: {' '.join(cmd[:10])}...")
        returncode, stdout, stderr = DockerClient.run_command(cmd)

        if returncode != 0:
            return False, f"啟動失敗: {stderr}"

        return True, "掃描任務已啟動"

    @staticmethod
    def run_reporter() -> Tuple[bool, str]:
        """執行報告生成器容器"""
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{SHARED_VOLUME_NAME}:/app/data",
            REPORTER_IMAGE
        ]

        logger.info("啟動 Reporter 容器...")
        returncode, stdout, stderr = DockerClient.run_command(cmd, check=False)

        if returncode != 0:
            return False, f"報告生成失敗: {stderr}"

        return True, "報告生成完成"

    @staticmethod
    def read_file_from_volume(filename: str) -> Optional[str]:
        """從共用 Volume 讀取檔案內容"""
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{SHARED_VOLUME_NAME}:/data",
            "alpine", "cat", f"/data/{filename}"
        ]

        returncode, stdout, stderr = DockerClient.run_command(cmd)

        if returncode != 0:
            logger.error(f"讀取檔案失敗: {filename} - {stderr}")
            return None

        return stdout

    @staticmethod
    def read_json_from_volume(filename: str) -> Optional[dict]:
        """從共用 Volume 讀取 JSON 檔案"""
        content = DockerClient.read_file_from_volume(filename)
        if content is None:
            return None

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失敗: {filename} - {e}")
            return None
