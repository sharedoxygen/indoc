"""
Modern virus scanning service with multiple detection layers
Optimized for SaaS performance and accuracy
"""
import hashlib
import mimetypes
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
import asyncio
import aiofiles
import yara
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class ModernVirusScanner:
    """
    Multi-layered virus scanning optimized for SaaS:
    1. Fast local checks (extension, magic bytes, patterns)
    2. YARA rules for known threats
    3. Optional cloud API for deep scanning
    """
    
    def __init__(self):
        from app.core.config import settings
        self.settings = settings
        
        # Layer 1: Fast local checks
        self.setup_fast_checks()
        
        # Layer 2: YARA rules (if available)
        self.yara_rules = self.load_yara_rules()
        
        # Layer 3: Cloud APIs (configurable)
        self.enable_virustotal = settings.ENABLE_VIRUSTOTAL if hasattr(settings, 'ENABLE_VIRUSTOTAL') else False
        self.virustotal_api_key = settings.VIRUSTOTAL_API_KEY if hasattr(settings, 'VIRUSTOTAL_API_KEY') else None
        
    def setup_fast_checks(self):
        """Initialize fast local security checks"""
        # Dangerous extensions
        self.dangerous_extensions = {
            '.exe', '.dll', '.scr', '.bat', '.cmd', '.com', '.pif',
            '.vbs', '.js', '.jar', '.zip', '.rar', '.7z',
            '.msi', '.app', '.deb', '.rpm'
        }
        
        # File magic bytes (file signatures)
        self.magic_bytes = {
            b'MZ': 'Windows executable',
            b'\x7fELF': 'Linux executable',
            b'PK\x03\x04': 'ZIP archive (potential malware container)',
            b'Rar!': 'RAR archive',
            b'\xca\xfe\xba\xbe': 'MacOS executable',
            b'\xfe\xed\xfa': 'MacOS executable (32-bit)',
            b'\xce\xfa\xed\xfe': 'MacOS executable (reversed)',
        }
        
        # Suspicious patterns in documents
        self.suspicious_patterns = [
            # Macro indicators
            rb'(?i)(autoopen|workbook_open|document_open)',
            rb'(?i)(shell|cmd|powershell|wscript)',
            rb'(?i)(eval|exec|system|passthru)',
            # Embedded executables
            rb'(?i)(This program cannot be run in DOS mode)',
            # Suspicious URLs
            rb'(?i)(bit\.ly|tinyurl|short\.link)',
        ]
        
        # Known malware hashes (simplified - in production, use a proper database)
        self.malware_hashes = {
            "44d88612fea8a8f36de82e1278abb02f": "EICAR test file",
            # Add more hashes from threat intelligence feeds
        }
    
    def load_yara_rules(self) -> Optional[yara.Rules]:
        """Load YARA rules if available"""
        try:
            rules_path = Path(__file__).parent.parent / "security" / "yara_rules.yar"
            if rules_path.exists():
                return yara.compile(filepath=str(rules_path))
            logger.info("YARA rules not found, skipping YARA scanning")
        except ImportError:
            logger.info("YARA not installed, skipping YARA scanning")
        except Exception as e:
            logger.warning(f"Failed to load YARA rules: {e}")
        return None
    
    async def scan_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Perform multi-layered virus scan
        Returns: {
            'status': 'clean' | 'suspicious' | 'infected',
            'threats': [],
            'details': {},
            'confidence': 0-100
        }
        """
        result = {
            'status': 'clean',
            'threats': [],
            'details': {},
            'confidence': 100,
            'scan_time': datetime.utcnow().isoformat()
        }
        
        # Layer 1: Fast local checks (milliseconds)
        local_threats = await self._fast_local_scan(file_path)
        if local_threats:
            result['threats'].extend(local_threats)
            result['details']['local_scan'] = local_threats
            
        # Layer 2: YARA scanning (seconds)
        if self.yara_rules:
            yara_threats = await self._yara_scan(file_path)
            if yara_threats:
                result['threats'].extend(yara_threats)
                result['details']['yara_scan'] = yara_threats
        
        # Layer 3: Cloud API scanning (optional, async)
        if self.enable_virustotal and self.virustotal_api_key:
            # Non-blocking: queue for background scanning
            asyncio.create_task(self._queue_cloud_scan(file_path))
            result['details']['cloud_scan'] = 'queued'
        
        # Determine overall status
        if result['threats']:
            threat_count = len(result['threats'])
            if threat_count >= 2 or any('executable' in t.lower() for t in result['threats']):
                result['status'] = 'infected'
                result['confidence'] = 95
            else:
                result['status'] = 'suspicious'
                result['confidence'] = 70
        
        return result
    
    async def _fast_local_scan(self, file_path: Path) -> List[str]:
        """Perform fast local security checks"""
        threats = []
        
        # Check extension
        if file_path.suffix.lower() in self.dangerous_extensions:
            threats.append(f"Dangerous file type: {file_path.suffix}")
        
        # Check file hash against known malware
        async with aiofiles.open(file_path, 'rb') as f:
            content = await f.read()
            file_hash = hashlib.md5(content).hexdigest()
            
            if file_hash in self.malware_hashes:
                threats.append(f"Known malware: {self.malware_hashes[file_hash]}")
            
            # Check magic bytes
            for magic, description in self.magic_bytes.items():
                if content.startswith(magic):
                    threats.append(f"Suspicious file signature: {description}")
                    break
            
            # Check for suspicious patterns (limit to first 1MB for performance)
            scan_content = content[:1024*1024]
            for pattern in self.suspicious_patterns:
                if re.search(pattern, scan_content):
                    threats.append(f"Suspicious pattern detected")
                    break
        
        return threats
    
    async def _yara_scan(self, file_path: Path) -> List[str]:
        """Scan file with YARA rules"""
        threats = []
        try:
            matches = self.yara_rules.match(str(file_path))
            for match in matches:
                threats.append(f"YARA match: {match.rule}")
        except Exception as e:
            logger.warning(f"YARA scan failed: {e}")
        return threats
    
    async def _queue_cloud_scan(self, file_path: Path):
        """Queue file for background cloud scanning"""
        # This would integrate with VirusTotal or other APIs
        # Implementation depends on your chosen service
        logger.info(f"Queued {file_path.name} for cloud scanning")
        # In production: save to queue, process asynchronously
        pass


# Example YARA rules file (save as app/security/yara_rules.yar)
EXAMPLE_YARA_RULES = """
rule suspicious_macro {
    meta:
        description = "Detects suspicious macros in documents"
    strings:
        $auto = "AutoOpen" nocase
        $shell = "Shell" nocase
        $cmd = "cmd.exe" nocase
    condition:
        any of them
}

rule embedded_executable {
    meta:
        description = "Detects embedded executables"
    strings:
        $mz = { 4D 5A }  // MZ header
        $elf = { 7F 45 4C 46 }  // ELF header
    condition:
        $mz or $elf
}

rule phishing_indicators {
    meta:
        description = "Common phishing patterns"
    strings:
        $urgent = "urgent action required" nocase
        $verify = "verify your account" nocase
        $suspended = "account suspended" nocase
        $bitcoin = "bitcoin" nocase
        $lottery = "lottery winner" nocase
    condition:
        2 of them
}
"""

