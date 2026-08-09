"""
Virus scanning service for uploaded files
"""
import logging
import subprocess
import hashlib
import time
from typing import Dict, Any, Optional, List
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class VirusScanner:
    """Service for scanning uploaded files for viruses and malicious content"""
    
    def __init__(self):
        self.enabled = True  # Enable by default for production
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.max_file_size = 100 * 1024 * 1024  # 100MB
        self.scan_timeout = 30  # 30 seconds
        
        # Known malicious file signatures (basic examples)
        self.malicious_signatures = {
            # EICAR test string
            "68e656c6a5b397d532e9cab817a9b808": "EICAR-Test-File",
            # Empty file (suspicious in some contexts)
            "d41d8cd98f00b204e9800998ecf8427e": "Empty-File-Suspicious"
        }
        
        # Dangerous file extensions that should be blocked
        self.dangerous_extensions = {
            '.exe', '.scr', '.bat', '.cmd', '.com', '.pif', '.vbs', '.js', 
            '.jar', '.app', '.deb', '.pkg', '.dmg', '.msi', '.reg'
        }
    
    async def scan_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Scan a file for viruses and malicious content
        
        Args:
            file_path: Path to the file to scan
            
        Returns:
            Dictionary containing scan results
        """
        start_time = time.time()
        
        if not self.enabled:
            return {
                "status": "skipped",
                "clean": True,
                "threats": [],
                "scan_time": 0.0,
                "message": "Virus scanning disabled"
            }
        
        try:
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Check file size
            file_size = file_path.stat().st_size
            if file_size > self.max_file_size:
                return {
                    "status": "error",
                    "clean": False,
                    "threats": ["File too large for scanning"],
                    "scan_time": time.time() - start_time,
                    "error": f"File size {file_size} exceeds maximum {self.max_file_size}"
                }
            
            # Run scan in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(self.executor, self._scan_file_sync, file_path),
                timeout=self.scan_timeout
            )
            
            result["scan_time"] = time.time() - start_time
            logger.info(f"File scanned: {file_path.name} - Status: {result['status']}")
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"Virus scan timeout for file: {file_path}")
            return {
                "status": "error",
                "clean": False,
                "threats": ["Scan timeout"],
                "scan_time": time.time() - start_time,
                "error": "Scan timeout exceeded"
            }
        except Exception as e:
            logger.error(f"Error scanning file {file_path}: {str(e)}")
            return {
                "status": "error",
                "clean": False,
                "threats": [],
                "scan_time": time.time() - start_time,
                "error": str(e)
            }
    
    def _scan_file_sync(self, file_path: Path) -> Dict[str, Any]:
        """Synchronous file scanning (runs in thread pool)"""
        threats_found = []
        
        # 1. Check file extension
        if file_path.suffix.lower() in self.dangerous_extensions:
            threats_found.append(f"Dangerous file extension: {file_path.suffix}")
        
        # 2. Check file hash against known malicious signatures
        file_hash = self._calculate_md5(file_path)
        if file_hash in self.malicious_signatures:
            threats_found.append(f"Known malicious file: {self.malicious_signatures[file_hash]}")
        
        # 3. Basic content analysis
        content_threats = self._analyze_file_content(file_path)
        threats_found.extend(content_threats)
        
        # 4. Try ClamAV if available
        clamav_result = self._scan_with_clamav(file_path)
        if clamav_result and clamav_result.get("threats"):
            threats_found.extend(clamav_result["threats"])
        
        # Determine overall status
        if threats_found:
            status = "infected"
            clean = False
        else:
            status = "clean"
            clean = True
        
        return {
            "status": status,
            "clean": clean,
            "threats": threats_found,
            "file_hash": file_hash
        }
    
    def _calculate_md5(self, file_path: Path) -> str:
        """Calculate MD5 hash of file"""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
        except Exception as e:
            logger.error(f"Error calculating hash for {file_path}: {e}")
            return "error"
        return hash_md5.hexdigest()
    
    def _analyze_file_content(self, file_path: Path) -> List[str]:
        """Basic content analysis for suspicious patterns"""
        threats = []
        
        try:
            # Read first 1KB of file for analysis
            with open(file_path, 'rb') as f:
                content = f.read(1024)
            
            # Convert to string for pattern matching
            try:
                content_str = content.decode('utf-8', errors='ignore').lower()
            except:
                content_str = str(content).lower()
            
            # Check for suspicious patterns
            suspicious_patterns = [
                'eval(',
                'exec(',
                'system(',
                'shell_exec(',
                'powershell',
                'cmd.exe',
                'wscript',
                'cscript'
            ]
            
            for pattern in suspicious_patterns:
                if pattern in content_str:
                    threats.append(f"Suspicious pattern: {pattern}")
            
            # Check for executable signatures
            if content.startswith(b'MZ'):  # PE/DOS executable
                threats.append("Executable file (PE/DOS)")
            elif content.startswith(b'\x7fELF'):  # ELF executable
                threats.append("Executable file (ELF)")
            
        except Exception as e:
            logger.warning(f"Error analyzing file content for {file_path}: {e}")
        
        return threats
    
    def _scan_with_clamav(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Attempt to scan with ClamAV if available"""
        try:
            # Check if clamscan is available
            result = subprocess.run(
                ['clamscan', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                return None
            
            # Run actual scan
            result = subprocess.run(
                ['clamscan', '--no-summary', str(file_path)],
                capture_output=True,
                text=True,
                timeout=self.scan_timeout
            )
            
            threats = []
            if result.returncode == 1:  # Virus found
                # Parse output for threat names
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'FOUND' in line:
                        threat_name = line.split(':')[-1].strip()
                        threats.append(f"ClamAV: {threat_name}")
            
            return {
                "engine": "ClamAV",
                "threats": threats
            }
            
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            # ClamAV not available or error occurred
            return None
    
    def is_file_safe(self, file_path: Path) -> bool:
        """Quick synchronous check if file appears safe"""
        try:
            # Check extension
            if file_path.suffix.lower() in self.dangerous_extensions:
                return False
            
            # Check hash
            file_hash = self._calculate_md5(file_path)
            if file_hash in self.malicious_signatures:
                return False
            
            # Basic size check
            if file_path.stat().st_size > self.max_file_size:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking file safety for {file_path}: {e}")
            return False
    
    def scan_file_sync(self, file_path: Path) -> Dict[str, Any]:
        """Synchronous version for Celery tasks"""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.scan_file(file_path))
        finally:
            loop.close()