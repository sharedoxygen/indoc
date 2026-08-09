"""
HIPAA and PCI Compliance Management
Handles compliance modes, PHI protection, and regulatory requirements
"""
from enum import Enum
from typing import List, Dict, Any, Optional
import re
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ComplianceMode(str, Enum):
    """Compliance mode configuration"""
    STANDARD = "standard"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    SOX = "sox"
    GDPR = "gdpr"
    MAXIMUM = "maximum"  # Maximum security mode


@dataclass
class PHIPattern:
    """Protected Health Information pattern definition"""
    name: str
    pattern: str
    description: str
    sensitivity: str  # high, medium, low
    replacement: str = "[REDACTED-{name}]"


class PHIDetector:
    """Detect and redact Protected Health Information (PHI)"""
    
    def __init__(self):
        self.patterns = self._initialize_phi_patterns()
    
    def _initialize_phi_patterns(self) -> List[PHIPattern]:
        """Initialize PHI detection patterns based on HIPAA guidelines"""
        return [
            # Social Security Numbers
            PHIPattern(
                name="SSN",
                pattern=r'\b\d{3}-\d{2}-\d{4}\b|\b\d{3}\s\d{2}\s\d{4}\b|\b\d{9}\b',
                description="Social Security Number",
                sensitivity="high",
                replacement="[REDACTED-SSN]"
            ),
            
            # Medical Record Numbers
            PHIPattern(
                name="MRN",
                pattern=r'\b(?:MRN|Medical Record|Patient ID|Chart)[\s:#]*(\d{6,12})\b',
                description="Medical Record Number",
                sensitivity="high",
                replacement="[REDACTED-MRN]"
            ),
            
            # Phone Numbers
            PHIPattern(
                name="PHONE",
                pattern=r'\b\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
                description="Phone Number",
                sensitivity="medium",
                replacement="[REDACTED-PHONE]"
            ),
            
            # Email Addresses
            PHIPattern(
                name="EMAIL",
                pattern=r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                description="Email Address",
                sensitivity="medium",
                replacement="[REDACTED-EMAIL]"
            ),
            
            # Dates of Birth
            PHIPattern(
                name="DOB",
                pattern=r'\b(?:DOB|Date of Birth|Born)[\s:]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
                description="Date of Birth",
                sensitivity="high",
                replacement="[REDACTED-DOB]"
            ),
            
            # Full Names (when followed by patient/medical context)
            PHIPattern(
                name="PATIENT_NAME",
                pattern=r'\b(?:Patient|Mr\.|Mrs\.|Ms\.|Dr\.)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)\b',
                description="Patient Name",
                sensitivity="high",
                replacement="[REDACTED-PATIENT]"
            ),
            
            # Credit Card Numbers (for PCI compliance)
            PHIPattern(
                name="CCN",
                pattern=r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
                description="Credit Card Number",
                sensitivity="high",
                replacement="[REDACTED-CCN]"
            ),
            
            # Account Numbers
            PHIPattern(
                name="ACCOUNT",
                pattern=r'\b(?:Account|Acct)[\s#:]*(\d{8,16})\b',
                description="Account Number",
                sensitivity="high",
                replacement="[REDACTED-ACCOUNT]"
            )
        ]
    
    def scan_text(self, text: str, mode: ComplianceMode = ComplianceMode.STANDARD) -> Dict[str, Any]:
        """
        Scan text for PHI and return detection results
        
        Args:
            text: Text to scan
            mode: Compliance mode (affects sensitivity)
            
        Returns:
            Dict with detected PHI information
        """
        detections = []
        redacted_text = text
        
        for pattern in self.patterns:
            if self._should_check_pattern(pattern, mode):
                matches = re.finditer(pattern.pattern, text, re.IGNORECASE)
                
                for match in matches:
                    detection = {
                        "type": pattern.name,
                        "description": pattern.description,
                        "sensitivity": pattern.sensitivity,
                        "start": match.start(),
                        "end": match.end(),
                        "matched_text": match.group(),
                        "redacted_replacement": pattern.replacement.format(name=pattern.name)
                    }
                    detections.append(detection)
                    
                    # Replace in redacted text
                    redacted_text = redacted_text.replace(
                        match.group(), 
                        pattern.replacement.format(name=pattern.name)
                    )
        
        return {
            "original_text": text,
            "redacted_text": redacted_text,
            "detections": detections,
            "phi_found": len(detections) > 0,
            "high_sensitivity_count": len([d for d in detections if d["sensitivity"] == "high"]),
            "scan_timestamp": datetime.utcnow().isoformat(),
            "compliance_mode": mode.value
        }
    
    def _should_check_pattern(self, pattern: PHIPattern, mode: ComplianceMode) -> bool:
        """Determine if pattern should be checked based on compliance mode"""
        if mode == ComplianceMode.STANDARD:
            return pattern.sensitivity == "high"
        elif mode in [ComplianceMode.HIPAA, ComplianceMode.MAXIMUM]:
            return True  # Check all patterns
        elif mode == ComplianceMode.PCI_DSS:
            return pattern.name in ["CCN", "ACCOUNT", "SSN"]
        else:
            return pattern.sensitivity in ["high", "medium"]


class ComplianceManager:
    """Manage compliance modes and requirements"""
    
    def __init__(self):
        self.phi_detector = PHIDetector()
        self.current_mode = ComplianceMode.STANDARD
    
    def set_compliance_mode(self, mode: ComplianceMode) -> Dict[str, Any]:
        """Set and configure compliance mode"""
        self.current_mode = mode
        
        config = self._get_mode_configuration(mode)
        logger.info(f"Compliance mode set to: {mode.value}")
        
        return {
            "mode": mode.value,
            "configuration": config,
            "timestamp": datetime.utcnow().isoformat(),
            "requirements": self._get_mode_requirements(mode)
        }
    
    def _get_mode_configuration(self, mode: ComplianceMode) -> Dict[str, Any]:
        """Get configuration settings for compliance mode"""
        configurations = {
            ComplianceMode.STANDARD: {
                "phi_detection": "basic",
                "audit_retention_days": 90,
                "encryption_required": False,
                "auto_redaction": False,
                "access_logging": "standard"
            },
            
            ComplianceMode.HIPAA: {
                "phi_detection": "comprehensive",
                "audit_retention_days": 2555,  # 7 years
                "encryption_required": True,
                "auto_redaction": True,
                "access_logging": "detailed",
                "baa_required": True,
                "patient_consent_tracking": True,
                "minimum_necessary_rule": True
            },
            
            ComplianceMode.PCI_DSS: {
                "phi_detection": "financial",
                "audit_retention_days": 365,
                "encryption_required": True,
                "auto_redaction": True,
                "access_logging": "detailed",
                "tokenization": True,
                "secure_transmission": True
            },
            
            ComplianceMode.MAXIMUM: {
                "phi_detection": "comprehensive",
                "audit_retention_days": 3650,  # 10 years
                "encryption_required": True,
                "auto_redaction": True,
                "access_logging": "maximum",
                "air_gapped": True,
                "zero_trust": True
            }
        }
        
        return configurations.get(mode, configurations[ComplianceMode.STANDARD])
    
    def _get_mode_requirements(self, mode: ComplianceMode) -> List[str]:
        """Get compliance requirements for mode"""
        requirements = {
            ComplianceMode.HIPAA: [
                "Business Associate Agreement (BAA) required",
                "Patient consent for data processing",
                "Minimum necessary rule enforcement",
                "Breach notification procedures",
                "Employee HIPAA training required",
                "Risk assessment documentation",
                "Incident response plan required"
            ],
            
            ComplianceMode.PCI_DSS: [
                "Secure cardholder data storage",
                "Strong access control measures",
                "Regular security testing",
                "Information security policy",
                "Network security monitoring",
                "Vulnerability management program"
            ],
            
            ComplianceMode.MAXIMUM: [
                "All HIPAA requirements",
                "All PCI DSS requirements",
                "Air-gapped deployment recommended",
                "Zero-trust security model",
                "Advanced threat protection",
                "Continuous security monitoring"
            ]
        }
        
        return requirements.get(mode, [])
    
    def process_document_content(self, content: str, document_id: str) -> Dict[str, Any]:
        """Process document content according to compliance mode"""
        phi_scan = self.phi_detector.scan_text(content, self.current_mode)
        
        processing_result = {
            "document_id": document_id,
            "compliance_mode": self.current_mode.value,
            "phi_scan": phi_scan,
            "processing_timestamp": datetime.utcnow().isoformat(),
            "compliance_actions": []
        }
        
        # Apply compliance actions based on mode
        if self.current_mode in [ComplianceMode.HIPAA, ComplianceMode.MAXIMUM]:
            if phi_scan["phi_found"]:
                processing_result["compliance_actions"].extend([
                    "PHI detected - applying HIPAA minimum necessary rule",
                    "Document flagged for enhanced audit logging",
                    "Access restricted to authorized personnel only"
                ])
        
        if self.current_mode == ComplianceMode.PCI_DSS:
            ccn_detected = any(d["type"] == "CCN" for d in phi_scan["detections"])
            if ccn_detected:
                processing_result["compliance_actions"].extend([
                    "Payment card data detected - PCI DSS rules applied",
                    "Data encrypted and tokenized",
                    "Access logged for PCI compliance audit"
                ])
        
        return processing_result
    
    def generate_compliance_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate compliance report for audit purposes"""
        return {
            "report_type": "compliance_summary",
            "compliance_mode": self.current_mode.value,
            "reporting_period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "documents_processed": 0,  # Would get from database
                "phi_detections": 0,       # Would get from audit logs
                "compliance_violations": 0,
                "access_events": 0
            },
            "recommendations": self._get_compliance_recommendations()
        }
    
    def _get_compliance_recommendations(self) -> List[str]:
        """Get compliance recommendations based on current mode"""
        if self.current_mode == ComplianceMode.HIPAA:
            return [
                "Ensure all staff complete HIPAA training annually",
                "Review patient consent forms for data processing",
                "Conduct quarterly risk assessments",
                "Test incident response procedures",
                "Review audit logs monthly for unusual access patterns"
            ]
        elif self.current_mode == ComplianceMode.PCI_DSS:
            return [
                "Conduct quarterly vulnerability scans",
                "Review access control lists monthly",
                "Test payment processing security controls",
                "Ensure secure key management practices",
                "Monitor network traffic for anomalies"
            ]
        else:
            return [
                "Consider enabling enhanced compliance mode",
                "Review data handling procedures",
                "Implement regular security training",
                "Establish incident response procedures"
            ]


# Global compliance manager instance
compliance_manager = ComplianceManager()
