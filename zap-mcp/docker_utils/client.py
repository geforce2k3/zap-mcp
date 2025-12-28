"""
Docker 命令執行客戶端 (Async + Fix)
"""
import subprocess
import json
from typing import Optional, List, Tuple

from core.config import SHARED_VOLUME_NAME, SCAN_CONTAINER_NAME, REPORTER_IMAGE, ZAP_IMAGE
from core.logging_config import logger

REPORTER_CONTAINER_NAME = "zap-reporter-job"

class DockerClient:
    """Docker 命令執行封裝類"""

    @staticmethod
    def run_command(cmd: List[str], check: bool = False) -> Tuple[int, str, str]:
        """執行 Docker 命令"""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=check)
            return result.returncode, result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            return e.returncode, e.stdout or "", e.stderr or ""

    @staticmethod
    def is_container_running(container_name: str) -> bool:
        """檢查指定名稱的容器是否正在運行"""
        cmd = ["docker", "ps", "-q", "-f", f"name={container_name}"]
        returncode, stdout, _ = DockerClient.run_command(cmd)
        return bool(stdout.strip())

    @staticmethod
    def remove_container(container_name: str) -> bool:
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
    def run_zap_scan(target_url: str, scan_type: str = "baseline", aggressive: bool = False, zap_configs: Optional[List[str]] = None) -> Tuple[bool, str]:
        """啟動 ZAP 掃描 (背景執行)"""
        script_name = "zap-full-scan.py" if scan_type == "full" else "zap-baseline.py"
        cmd = [
            "docker", "run", "-d",
            "--name", SCAN_CONTAINER_NAME,
            "-u", "0",
            "--dns", "8.8.8.8",
            "-v", f"{SHARED_VOLUME_NAME}:/zap/wrk:rw",
            "-t", ZAP_IMAGE,
            script_name, "-t", target_url, "-J", "ZAP-Report.json", "-I"
        ]
        if aggressive: cmd.extend(["-j", "-a"])
        if zap_configs: cmd.extend(["-z", " ".join(zap_configs)])

        logger.info(f"執行 ZAP 掃描: {' '.join(cmd[:10])}...")
        returncode, stdout, stderr = DockerClient.run_command(cmd)
        if returncode != 0: return False, f"啟動失敗: {stderr}"
        return True, "掃描任務已啟動"

    @staticmethod
    def run_reporter_detached() -> Tuple[bool, str]:
        """背景啟動報告生成器 (Async Fix)"""
        DockerClient.remove_container(REPORTER_CONTAINER_NAME)
        
        cmd = [
            "docker", "run", "-d",
            "--name", REPORTER_CONTAINER_NAME,
            "-v", f"{SHARED_VOLUME_NAME}:/app/data",
            REPORTER_IMAGE
        ]

        logger.info("背景啟動 Reporter 容器...")
        returncode, stdout, stderr = DockerClient.run_command(cmd)
        if returncode != 0: return False, f"啟動失敗: {stderr}"
        return True, "報告生成任務已在背景啟動"

    @staticmethod
    def check_file_exists(filename_pattern: str) -> bool:
        """檢查 Volume 內是否存在特定檔案 (支援 wildcard)"""
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{SHARED_VOLUME_NAME}:/data",
            "alpine", "sh", "-c", f"ls /data/{filename_pattern}"
        ]
        returncode, _, _ = DockerClient.run_command(cmd)
        return returncode == 0

    @staticmethod
    def read_file_from_volume(filename: str) -> Optional[str]:
        """
        [Missing Method Fixed] 從共用 Volume 讀取檔案內容 (純文字)
        用於讀取 nmap_result.xml 或其他非 JSON 檔案
        """
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
        # 重用上面的 read_file_from_volume 以保持 DRY (Don't Repeat Yourself)
        content = DockerClient.read_file_from_volume(filename)
        if content is None:
            return None
            
        try: 
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失敗: {filename} - {e}")
            return None