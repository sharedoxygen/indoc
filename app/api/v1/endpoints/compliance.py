"""
Compliance management API endpoints
HIPAA, PCI DSS, and other regulatory compliance features
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.core.compliance import compliance_manager, ComplianceMode, PHIDetector
from app.core.security import require_admin, require_compliance

router = APIRouter()


class ComplianceModeRequest(BaseModel):
    """Request to set compliance mode"""
    mode: ComplianceMode = Field(..., description="Compliance mode to activate")
    justification: Optional[str] = Field(None, description="Reason for changing compliance mode")


class ComplianceModeResponse(BaseModel):
    """Response for compliance mode operations"""
    mode: str
    configuration: Dict[str, Any]
    requirements: List[str]
    timestamp: str
    changed_by: Optional[str] = None


class PHIScanRequest(BaseModel):
    """Request to scan text for PHI"""
    text: str = Field(..., description="Text to scan for PHI")
    mode: Optional[ComplianceMode] = Field(ComplianceMode.STANDARD, description="Compliance mode for scanning")


class PHIScanResponse(BaseModel):
    """Response from PHI scanning"""
    phi_found: bool
    detections: List[Dict[str, Any]]
    redacted_text: str
    high_sensitivity_count: int
    scan_timestamp: str
    compliance_mode: str


class ComplianceReportRequest(BaseModel):
    """Request for compliance report"""
    start_date: datetime = Field(..., description="Report start date")
    end_date: datetime = Field(..., description="Report end date")
    report_type: Optional[str] = Field("summary", description="Type of report to generate")


@router.get("/mode", response_model=ComplianceModeResponse)
async def get_compliance_mode(
    current_user: User = Depends(get_current_user)
):
    """Get current compliance mode and configuration"""
    
    config = compliance_manager._get_mode_configuration(compliance_manager.current_mode)
    requirements = compliance_manager._get_mode_requirements(compliance_manager.current_mode)
    
    return ComplianceModeResponse(
        mode=compliance_manager.current_mode.value,
        configuration=config,
        requirements=requirements,
        timestamp=datetime.utcnow().isoformat()
    )


@router.post("/mode", response_model=ComplianceModeResponse)
async def set_compliance_mode(
    request: ComplianceModeRequest,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_admin)  # Only admins can change compliance mode
):
    """Set compliance mode for the system"""
    
    try:
        # Set the compliance mode
        result = compliance_manager.set_compliance_mode(request.mode)
        
        # Log the change for audit purposes
        # In a real implementation, this would go to audit logs
        print(f"Compliance mode changed to {request.mode.value} by user {current_user.email}")
        if request.justification:
            print(f"Justification: {request.justification}")
        
        return ComplianceModeResponse(
            mode=result["mode"],
            configuration=result["configuration"],
            requirements=result["requirements"],
            timestamp=result["timestamp"],
            changed_by=current_user.email
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set compliance mode: {str(e)}"
        )


@router.post("/scan-phi", response_model=PHIScanResponse)
async def scan_text_for_phi(
    request: PHIScanRequest,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_compliance)  # Compliance users can scan for PHI
):
    """Scan text for Protected Health Information (PHI)"""
    
    try:
        phi_detector = PHIDetector()
        scan_result = phi_detector.scan_text(request.text, request.mode)
        
        return PHIScanResponse(
            phi_found=scan_result["phi_found"],
            detections=scan_result["detections"],
            redacted_text=scan_result["redacted_text"],
            high_sensitivity_count=scan_result["high_sensitivity_count"],
            scan_timestamp=scan_result["scan_timestamp"],
            compliance_mode=scan_result["compliance_mode"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PHI scan failed: {str(e)}"
        )


@router.get("/modes", response_model=List[Dict[str, Any]])
async def get_available_compliance_modes(
    current_user: User = Depends(get_current_user)
):
    """Get all available compliance modes and their descriptions"""
    
    modes = []
    for mode in ComplianceMode:
        config = compliance_manager._get_mode_configuration(mode)
        requirements = compliance_manager._get_mode_requirements(mode)
        
        mode_info = {
            "mode": mode.value,
            "name": mode.value.replace("_", " ").title(),
            "description": get_mode_description(mode),
            "features": config,
            "requirements": requirements,
            "recommended_for": get_mode_recommendations(mode)
        }
        modes.append(mode_info)
    
    return modes


@router.post("/report", response_model=Dict[str, Any])
async def generate_compliance_report(
    request: ComplianceReportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_compliance)
):
    """Generate compliance report for audit purposes"""
    
    try:
        report = compliance_manager.generate_compliance_report(
            request.start_date,
            request.end_date
        )
        
        # Add user context
        report["requested_by"] = current_user.email
        report["user_role"] = current_user.role.value
        
        # In a real implementation, you would:
        # 1. Query actual data from audit logs
        # 2. Calculate real metrics
        # 3. Generate actionable insights
        
        return report
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate compliance report: {str(e)}"
        )


@router.get("/status", response_model=Dict[str, Any])
async def get_compliance_status(
    current_user: User = Depends(get_current_user)
):
    """Get overall compliance status and health"""
    
    current_config = compliance_manager._get_mode_configuration(compliance_manager.current_mode)
    
    status_info = {
        "current_mode": compliance_manager.current_mode.value,
        "configuration": current_config,
        "health_checks": {
            "encryption_enabled": current_config.get("encryption_required", False),
            "audit_logging": current_config.get("access_logging", "standard"),
            "phi_detection": current_config.get("phi_detection", "basic"),
            "auto_redaction": current_config.get("auto_redaction", False)
        },
        "recommendations": compliance_manager._get_compliance_recommendations(),
        "last_updated": datetime.utcnow().isoformat()
    }
    
    # Add alerts based on configuration
    alerts = []
    if compliance_manager.current_mode == ComplianceMode.STANDARD:
        alerts.append({
            "level": "info",
            "message": "Consider enabling enhanced compliance mode for better security"
        })
    
    if not current_config.get("encryption_required", False):
        alerts.append({
            "level": "warning", 
            "message": "Encryption not required in current mode"
        })
    
    status_info["alerts"] = alerts
    
    return status_info


@router.post("/validate-document", response_model=Dict[str, Any])
async def validate_document_compliance(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_compliance)
):
    """Validate a document for compliance issues"""
    
    # This would integrate with the document processing pipeline
    # For now, return a mock validation result
    
    validation_result = {
        "document_id": document_id,
        "compliance_mode": compliance_manager.current_mode.value,
        "validation_timestamp": datetime.utcnow().isoformat(),
        "validated_by": current_user.email,
        "status": "compliant",  # or "non_compliant", "needs_review"
        "issues": [],
        "recommendations": [],
        "phi_detected": False,
        "redactions_required": 0
    }
    
    return validation_result


def get_mode_description(mode: ComplianceMode) -> str:
    """Get user-friendly description for compliance mode"""
    descriptions = {
        ComplianceMode.STANDARD: "Basic security with standard audit logging",
        ComplianceMode.HIPAA: "Healthcare compliance with PHI protection and comprehensive audit trails",
        ComplianceMode.PCI_DSS: "Payment card industry compliance with secure cardholder data handling",
        ComplianceMode.SOX: "Sarbanes-Oxley compliance for financial reporting",
        ComplianceMode.GDPR: "European privacy regulation compliance with data protection",
        ComplianceMode.MAXIMUM: "Maximum security mode with all compliance features enabled"
    }
    return descriptions.get(mode, "Custom compliance configuration")


def get_mode_recommendations(mode: ComplianceMode) -> List[str]:
    """Get recommendations for when to use each mode"""
    recommendations = {
        ComplianceMode.STANDARD: ["General business documents", "Internal communications", "Non-sensitive data"],
        ComplianceMode.HIPAA: ["Healthcare organizations", "Patient records", "Medical research", "Health insurance"],
        ComplianceMode.PCI_DSS: ["Payment processing", "E-commerce", "Financial services", "Credit card data"],
        ComplianceMode.SOX: ["Public companies", "Financial reporting", "Audit documentation"],
        ComplianceMode.GDPR: ["EU operations", "Personal data processing", "Privacy-focused organizations"],
        ComplianceMode.MAXIMUM: ["Government agencies", "Defense contractors", "Highly regulated industries"]
    }
    return recommendations.get(mode, [])
