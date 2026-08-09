#!/usr/bin/env python3
"""
Realistic Seed Data Generator for inDoc

Generates production-like data that demonstrates actual functional capabilities:
- Real document types from actual business scenarios
- Authentic user workflows and interactions
- Realistic metadata and relationships
- Functional search scenarios
- Real compliance and audit patterns
"""

import asyncio
import sys
import os
import logging
import hashlib
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List
import uuid
import tempfile
from faker import Faker

# Add the backend directory to the Python path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.db.session import AsyncSessionLocal
from app.models.user import User, UserRole
from app.models.document import Document
from app.models.conversation import Conversation, Message
from app.models.audit import AuditLog
from app.core.security import get_password_hash
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Faker for realistic data generation
fake = Faker()


class RealisticSeedGenerator:
    """Generate realistic, production-like seed data"""
    
    def __init__(self):
        self.storage_path = Path("../backend/data/storage")
        self.temp_path = Path("../backend/data/temp")
        
        # Ensure directories exist
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.temp_path.mkdir(parents=True, exist_ok=True)
        
        # Real business domains for realistic emails
        self.business_domains = [
            "acmecorp.com", "techsolutions.io", "globalservices.net", 
            "innovatetech.com", "businesspro.org", "enterprise-sys.com"
        ]
        
        # Real document categories with authentic content
        self.document_categories = {
            "legal": {
                "types": ["contract", "agreement", "policy", "compliance", "terms"],
                "templates": self._get_legal_templates()
            },
            "finance": {
                "types": ["report", "budget", "invoice", "statement", "analysis"],
                "templates": self._get_finance_templates()
            },
            "hr": {
                "types": ["handbook", "policy", "procedure", "training", "manual"],
                "templates": self._get_hr_templates()
            },
            "technical": {
                "types": ["specification", "documentation", "guide", "manual", "readme"],
                "templates": self._get_technical_templates()
            },
            "marketing": {
                "types": ["presentation", "proposal", "campaign", "analysis", "report"],
                "templates": self._get_marketing_templates()
            },
            "operations": {
                "types": ["procedure", "checklist", "manual", "guide", "protocol"],
                "templates": self._get_operations_templates()
            },
            "healthcare": {
                "types": ["policy", "procedure", "protocol", "guideline", "record"],
                "templates": self._get_healthcare_templates()
            },
            "real_estate": {
                "types": ["contract", "listing", "appraisal", "inspection", "disclosure"],
                "templates": self._get_real_estate_templates()
            },
            "academic": {
                "types": ["research", "thesis", "curriculum", "syllabus", "policy"],
                "templates": self._get_academic_templates()
            },
            "manufacturing": {
                "types": ["specification", "quality", "safety", "procedure", "manual"],
                "templates": self._get_manufacturing_templates()
            },
            "retail": {
                "types": ["inventory", "policy", "training", "procedure", "manual"],
                "templates": self._get_retail_templates()
            }
        }
    
    def _get_legal_templates(self) -> List[Dict]:
        """Real legal document templates"""
        return [
            {
                "title": "Software License Agreement",
                "content": """SOFTWARE LICENSE AGREEMENT

This Software License Agreement ("Agreement") is entered into as of {date} between {company} ("Licensor") and the end user ("Licensee").

1. GRANT OF LICENSE
Subject to the terms and conditions of this Agreement, Licensor hereby grants to Licensee a non-exclusive, non-transferable license to use the software.

2. RESTRICTIONS
Licensee shall not:
- Reverse engineer, decompile, or disassemble the software
- Distribute, sublicense, or transfer the software
- Remove or modify any proprietary notices

3. TERM AND TERMINATION
This Agreement shall remain in effect until terminated. Either party may terminate this Agreement at any time with written notice.

4. LIMITATION OF LIABILITY
IN NO EVENT SHALL LICENSOR BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES.

5. GOVERNING LAW
This Agreement shall be governed by the laws of {jurisdiction}.

By using this software, you acknowledge that you have read and understood this Agreement.
""",
                "metadata": {"document_type": "license", "legal_category": "software", "requires_signature": True}
            },
            {
                "title": "Data Processing Agreement (GDPR Compliance)",
                "content": """DATA PROCESSING AGREEMENT

In accordance with the General Data Protection Regulation (GDPR), this Data Processing Agreement ("DPA") governs the processing of personal data.

1. DEFINITIONS
- "Personal Data" means any information relating to an identified or identifiable natural person
- "Processing" means any operation performed on personal data
- "Data Subject" means the identified or identifiable natural person

2. DATA PROTECTION PRINCIPLES
The Processor shall:
- Process personal data only on documented instructions from the Controller
- Ensure confidentiality of personal data
- Implement appropriate technical and organizational measures
- Assist the Controller in responding to data subject requests

3. SECURITY MEASURES
- Encryption of personal data in transit and at rest
- Regular security assessments and penetration testing
- Access controls and authentication mechanisms
- Incident response procedures

4. DATA BREACH NOTIFICATION
The Processor shall notify the Controller without undue delay upon becoming aware of a personal data breach.

5. DATA SUBJECT RIGHTS
The Processor shall assist the Controller in ensuring compliance with data subject rights including:
- Right of access
- Right to rectification
- Right to erasure ("right to be forgotten")
- Right to data portability

This DPA is effective as of {date} and shall remain in effect for the duration of the processing activities.
""",
                "metadata": {"document_type": "dpa", "compliance_framework": "gdpr", "review_required": True}
            },
            {
                "title": "Employee Confidentiality Agreement",
                "content": """CONFIDENTIALITY AND NON-DISCLOSURE AGREEMENT

This Confidentiality Agreement ("Agreement") is entered into between {company} and {employee_name}.

1. CONFIDENTIAL INFORMATION
"Confidential Information" includes all non-public information disclosed by the Company, including:
- Technical data, trade secrets, know-how
- Business plans, financial information, customer lists
- Marketing strategies, product development plans
- Any information marked as confidential

2. OBLIGATIONS
Employee agrees to:
- Hold all Confidential Information in strict confidence
- Not disclose Confidential Information to third parties
- Use Confidential Information solely for Company business
- Return all materials containing Confidential Information upon termination

3. EXCEPTIONS
This Agreement does not apply to information that:
- Is publicly available through no breach of this Agreement
- Was known to Employee prior to disclosure
- Is independently developed without use of Confidential Information

4. REMEDIES
Employee acknowledges that breach of this Agreement may cause irreparable harm, and Company may seek injunctive relief.

5. TERM
This Agreement shall survive termination of employment and remain in effect indefinitely.

Employee Signature: ___________________ Date: ___________
""",
                "metadata": {"document_type": "nda", "employee_required": True, "retention_period": "indefinite"}
            }
        ]
    
    def _get_finance_templates(self) -> List[Dict]:
        """Real financial document templates"""
        return [
            {
                "title": "Quarterly Financial Report Q{quarter} {year}",
                "content": """QUARTERLY FINANCIAL REPORT
Period: Q{quarter} {year}
Report Date: {date}

EXECUTIVE SUMMARY
This quarter showed {performance_trend} performance with revenue of ${revenue:,} and net income of ${net_income:,}.

FINANCIAL HIGHLIGHTS
• Revenue: ${revenue:,} ({revenue_change:+.1f}% vs. prior quarter)
• Gross Profit: ${gross_profit:,} ({gross_margin:.1f}% margin)
• Operating Expenses: ${operating_expenses:,}
• Net Income: ${net_income:,} ({net_margin:.1f}% margin)
• EBITDA: ${ebitda:,}

REVENUE BREAKDOWN BY SEGMENT
• Software Licenses: ${software_revenue:,} ({software_percent:.1f}%)
• Professional Services: ${services_revenue:,} ({services_percent:.1f}%)
• Support & Maintenance: ${support_revenue:,} ({support_percent:.1f}%)

BALANCE SHEET HIGHLIGHTS
• Total Assets: ${total_assets:,}
• Cash and Cash Equivalents: ${cash:,}
• Total Liabilities: ${total_liabilities:,}
• Stockholders' Equity: ${equity:,}

KEY METRICS
• Customer Acquisition Cost (CAC): ${cac:,}
• Customer Lifetime Value (LTV): ${ltv:,}
• Monthly Recurring Revenue (MRR): ${mrr:,}
• Churn Rate: {churn_rate:.2f}%

OUTLOOK
{outlook_text}

This report contains forward-looking statements subject to risks and uncertainties.
""",
                "metadata": {"report_type": "quarterly", "financial_period": "Q{quarter} {year}", "confidentiality": "restricted"}
            },
            {
                "title": "Annual Budget Plan {year}",
                "content": """ANNUAL BUDGET PLAN
Fiscal Year: {year}
Prepared: {date}

BUDGET OVERVIEW
Total Planned Revenue: ${total_revenue:,}
Total Planned Expenses: ${total_expenses:,}
Projected Net Income: ${projected_income:,}

REVENUE PROJECTIONS
• Product Sales: ${product_sales:,} ({product_growth:+.1f}% growth)
• Service Revenue: ${service_revenue:,} ({service_growth:+.1f}% growth)
• Recurring Revenue: ${recurring_revenue:,} ({recurring_growth:+.1f}% growth)

DEPARTMENTAL BUDGETS
• Research & Development: ${rd_budget:,} ({rd_percent:.1f}% of revenue)
• Sales & Marketing: ${marketing_budget:,} ({marketing_percent:.1f}% of revenue)
• General & Administrative: ${admin_budget:,} ({admin_percent:.1f}% of revenue)
• Operations: ${operations_budget:,} ({operations_percent:.1f}% of revenue)

CAPITAL EXPENDITURES
• Technology Infrastructure: ${tech_capex:,}
• Office Equipment: ${office_capex:,}
• Software Licenses: ${software_capex:,}

HEADCOUNT PLAN
• Current Employees: {current_headcount}
• Planned Hires: {planned_hires}
• Year-end Target: {target_headcount}

KEY ASSUMPTIONS
• Market growth rate: {market_growth:.1f}%
• Customer retention rate: {retention_rate:.1f}%
• Average selling price increase: {price_increase:.1f}%

RISK FACTORS
• Economic downturn impact
• Competitive market pressures
• Regulatory changes
• Technology disruption

Budget approved by: Finance Committee
Approval Date: {approval_date}
""",
                "metadata": {"budget_year": "{year}", "approval_status": "approved", "department": "finance"}
            }
        ]
    
    def _get_hr_templates(self) -> List[Dict]:
        """Real HR document templates"""
        return [
            {
                "title": "Employee Handbook {year}",
                "content": """EMPLOYEE HANDBOOK
Effective Date: {date}
Version: {version}

WELCOME TO {company}
This handbook provides important information about our company policies, procedures, and benefits.

EMPLOYMENT POLICIES

Equal Employment Opportunity
{company} is committed to providing equal employment opportunities to all employees and applicants.

Anti-Harassment Policy
We maintain a zero-tolerance policy for harassment of any kind. All employees are expected to treat others with respect and dignity.

Code of Conduct
Employees are expected to:
• Act with integrity and honesty in all business dealings
• Protect confidential information
• Comply with all applicable laws and regulations
• Report any violations or concerns to management

WORK ARRANGEMENTS

Working Hours
• Standard business hours: 9:00 AM - 5:00 PM
• Flexible work arrangements available with manager approval
• Remote work policy: Up to 3 days per week

Time Off Policies
• Vacation: {vacation_days} days annually
• Sick Leave: {sick_days} days annually
• Personal Days: {personal_days} days annually
• Holidays: {holiday_count} company holidays

BENEFITS

Health Insurance
• Medical, dental, and vision coverage
• Company contributes {health_contribution}% of premiums
• Coverage begins on first day of employment

Retirement Plan
• 401(k) plan with company matching up to {match_percent}%
• Immediate vesting of employee contributions
• Company match vests over {vesting_years} years

Professional Development
• Annual training budget: ${training_budget:,} per employee
• Conference attendance encouraged
• Tuition reimbursement available

TECHNOLOGY POLICIES

Acceptable Use Policy
• Company equipment for business purposes only
• No personal software installation without IT approval
• Regular security training required

Data Security
• All employees must complete annual security training
• Report security incidents immediately
• Use strong passwords and enable 2FA

This handbook is subject to change. Updates will be communicated to all employees.

Questions? Contact HR at hr@{company_domain}
""",
                "metadata": {"handbook_year": "{year}", "policy_version": "{version}", "mandatory_reading": True}
            },
            {
                "title": "Performance Review Guidelines",
                "content": """PERFORMANCE REVIEW GUIDELINES
Annual Performance Evaluation Process

OVERVIEW
Our performance review process is designed to provide meaningful feedback, recognize achievements, and identify development opportunities.

REVIEW CYCLE
• Annual reviews conducted in {review_month}
• Mid-year check-ins in {midyear_month}
• Ongoing feedback encouraged throughout the year

EVALUATION CRITERIA

Core Competencies (40%)
• Job Knowledge and Skills
• Quality of Work
• Productivity and Efficiency
• Problem Solving and Innovation

Behavioral Competencies (30%)
• Communication and Collaboration
• Leadership and Initiative
• Adaptability and Learning
• Customer Focus

Goal Achievement (30%)
• Achievement of annual objectives
• Project completion and quality
• Contribution to team goals
• Professional development progress

RATING SCALE
5 - Exceptional: Consistently exceeds expectations
4 - Exceeds Expectations: Regularly surpasses requirements
3 - Meets Expectations: Fully satisfies job requirements
2 - Below Expectations: Partially meets requirements
1 - Unsatisfactory: Does not meet basic requirements

REVIEW PROCESS
1. Employee Self-Assessment (due {self_assessment_date})
2. Manager Evaluation (due {manager_evaluation_date})
3. Peer Feedback Collection (optional)
4. Review Meeting Scheduled
5. Development Plan Created
6. Final Review Documentation

DEVELOPMENT PLANNING
Based on the review, employees and managers will:
• Identify strengths and areas for improvement
• Set goals for the upcoming year
• Create a professional development plan
• Discuss career aspirations and opportunities

CALIBRATION PROCESS
Management team conducts calibration sessions to ensure:
• Consistent application of rating standards
• Fair and equitable evaluations across teams
• Identification of high performers and development needs

All performance reviews are confidential and stored securely in the HR system.

For questions about the review process, contact your manager or HR.
""",
                "metadata": {"review_cycle": "annual", "confidentiality": "hr_only", "process_version": "2024.1"}
            }
        ]
    
    def _get_technical_templates(self) -> List[Dict]:
        """Real technical document templates"""
        return [
            {
                "title": "API Integration Guide v{version}",
                "content": """API INTEGRATION GUIDE
Version: {version}
Last Updated: {date}

OVERVIEW
This guide provides comprehensive instructions for integrating with our REST API.

AUTHENTICATION
All API requests require authentication using JWT tokens.

1. Obtain Access Token
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=your_username&password=your_password

Response:
{{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}}

2. Include Token in Requests
Authorization: Bearer <access_token>

CORE ENDPOINTS

Document Management
• GET /api/v1/files - List documents
• POST /api/v1/files - Upload document
• GET /api/v1/files/{{id}} - Get document details
• PUT /api/v1/files/{{id}} - Update document
• DELETE /api/v1/files/{{id}} - Delete document

Search Operations
• POST /api/v1/search/query - Search documents
• GET /api/v1/search/documents/{{id}}/similar - Find similar documents

User Management (Admin only)
• GET /api/v1/users - List users
• POST /api/v1/users - Create user
• PUT /api/v1/users/{{id}} - Update user

RATE LIMITING
• 1000 requests per hour per user
• 100 requests per minute for upload endpoints
• Rate limit headers included in responses

ERROR HANDLING
Standard HTTP status codes:
• 200 - Success
• 400 - Bad Request
• 401 - Unauthorized
• 403 - Forbidden
• 404 - Not Found
• 429 - Rate Limited
• 500 - Internal Server Error

Error Response Format:
{{
  "detail": "Error description",
  "error_code": "SPECIFIC_ERROR_CODE",
  "timestamp": "2024-01-15T10:30:00Z"
}}

PAGINATION
List endpoints support pagination:
• ?skip=0&limit=100 (default)
• Response includes total count and next page info

WEBHOOKS
Configure webhooks for real-time notifications:
• Document uploaded
• Document processed
• User created
• Search performed

SDKS AND EXAMPLES
Python SDK:
pip install indoc-client

Example usage:
```python
from indoc_client import InDocClient

client = InDocClient(api_key="your_api_key")
documents = client.documents.list()
```

For support, contact: api-support@{company_domain}
""",
                "metadata": {"api_version": "{version}", "integration_type": "rest", "audience": "developers"}
            },
            {
                "title": "System Architecture Documentation",
                "content": """SYSTEM ARCHITECTURE DOCUMENTATION
Document Management Platform

ARCHITECTURE OVERVIEW
Our document management system follows a microservices architecture with the following components:

FRONTEND LAYER
• React-based single-page application (SPA)
• TypeScript for type safety
• Redux Toolkit for state management
• Material-UI for consistent design
• Vite for fast development and building

API GATEWAY
• FastAPI framework (Python)
• JWT-based authentication
• Role-based access control (RBAC)
• Request rate limiting
• API versioning support

CORE SERVICES

Document Service
• File upload and storage management
• Metadata extraction and indexing
• Virus scanning integration
• Format conversion capabilities

Search Service
• Elasticsearch for full-text search
• Qdrant for semantic/vector search
• Hybrid search combining both approaches
• Real-time indexing pipeline

User Management Service
• User authentication and authorization
• Role and permission management
• Session management
• Audit logging

Background Processing
• Celery for asynchronous task processing
• Redis as message broker
• Document processing pipeline
• Scheduled maintenance tasks

DATA LAYER

Primary Database (PostgreSQL)
• User accounts and profiles
• Document metadata
• Conversation history
• Audit logs and compliance data

Search Indexes
• Elasticsearch: Full-text search index
• Qdrant: Vector embeddings for semantic search

Cache Layer (Redis)
• Session storage
• Frequently accessed data
• Background job queues

File Storage
• Local filesystem (development)
• S3-compatible storage (production)
• Hierarchical organization by hash

SECURITY ARCHITECTURE

Authentication & Authorization
• JWT tokens with configurable expiration
• Role-based access control (Admin, Reviewer, Uploader, Viewer, Compliance)
• API endpoint protection
• Session management

Data Protection
• Encryption at rest for sensitive fields
• TLS encryption for data in transit
• Field-level encryption for PII
• Secure file upload validation

Audit & Compliance
• Comprehensive audit logging
• Compliance reporting capabilities
• Data retention policies
• GDPR compliance features

DEPLOYMENT ARCHITECTURE

Development Environment
• Local services via Docker Compose
• Hot reloading for development
• Integrated debugging tools

Production Environment
• Kubernetes orchestration
• Horizontal pod autoscaling
• Load balancing and failover
• Monitoring and alerting

MONITORING & OBSERVABILITY

Application Monitoring
• Prometheus metrics collection
• Grafana dashboards
• Custom business metrics
• Performance monitoring

Logging
• Structured logging (JSON format)
• Centralized log aggregation
• Log retention policies
• Security event monitoring

Health Checks
• Service health endpoints
• Database connectivity checks
• External service monitoring
• Automated alerting

SCALABILITY CONSIDERATIONS

Horizontal Scaling
• Stateless API design
• Database read replicas
• Search cluster scaling
• CDN for static assets

Performance Optimization
• Database query optimization
• Caching strategies
• Asynchronous processing
• Connection pooling

For technical questions, contact: architecture@{company_domain}
""",
                "metadata": {"doc_type": "architecture", "audience": "technical", "classification": "internal"}
            }
        ]
    
    def _get_finance_templates(self) -> List[Dict]:
        """Real finance document templates"""
        return [
            {
                "title": "Monthly Financial Dashboard {month} {year}",
                "content": """MONTHLY FINANCIAL DASHBOARD
Period: {month} {year}
Generated: {date}

KEY PERFORMANCE INDICATORS

Revenue Metrics
• Monthly Recurring Revenue (MRR): ${mrr:,}
• Annual Run Rate (ARR): ${arr:,}
• Revenue Growth Rate: {revenue_growth:+.1f}% MoM
• Customer Acquisition Cost (CAC): ${cac:,}
• Customer Lifetime Value (LTV): ${ltv:,}
• LTV/CAC Ratio: {ltv_cac_ratio:.1f}x

Operational Metrics
• Gross Margin: {gross_margin:.1f}%
• Operating Margin: {operating_margin:.1f}%
• EBITDA Margin: {ebitda_margin:.1f}%
• Burn Rate: ${burn_rate:,}/month
• Runway: {runway_months} months

Customer Metrics
• Total Customers: {total_customers:,}
• New Customers: {new_customers:,} ({customer_growth:+.1f}% growth)
• Churn Rate: {churn_rate:.2f}%
• Net Revenue Retention: {nrr:.1f}%

FINANCIAL POSITION

Assets
• Cash and Equivalents: ${cash:,}
• Accounts Receivable: ${ar:,} (DSO: {dso} days)
• Inventory: ${inventory:,}
• Fixed Assets: ${fixed_assets:,}
• Total Assets: ${total_assets:,}

Liabilities & Equity
• Accounts Payable: ${ap:,} (DPO: {dpo} days)
• Accrued Expenses: ${accrued:,}
• Long-term Debt: ${debt:,}
• Total Equity: ${equity:,}

DEPARTMENTAL PERFORMANCE

Sales Performance
• Pipeline Value: ${pipeline:,}
• Conversion Rate: {conversion_rate:.1f}%
• Average Deal Size: ${avg_deal:,}
• Sales Cycle: {sales_cycle} days

Marketing Performance
• Marketing Qualified Leads (MQLs): {mqls:,}
• Cost per Lead: ${cost_per_lead:,}
• Lead to Customer Rate: {lead_conversion:.1f}%
• Marketing ROI: {marketing_roi:.1f}x

VARIANCE ANALYSIS
• Revenue vs. Budget: {revenue_variance:+.1f}%
• Expenses vs. Budget: {expense_variance:+.1f}%
• Key variances explained in detailed report

FORECAST UPDATE
Based on current trends, we are {forecast_direction} our annual targets:
• Revenue Forecast: ${revenue_forecast:,} ({forecast_confidence}% confidence)
• Expense Forecast: ${expense_forecast:,}

Action Items:
{action_items}

Report prepared by: Finance Team
Next update: {next_update}
""",
                "metadata": {"period": "{month} {year}", "dashboard_type": "monthly", "auto_generated": True}
            }
        ]
    
    def _get_hr_templates(self) -> List[Dict]:
        """Real HR document templates"""
        return [
            {
                "title": "Remote Work Policy {year}",
                "content": """REMOTE WORK POLICY
Effective Date: {date}
Policy Version: {version}

PURPOSE
This policy establishes guidelines for remote work arrangements to ensure productivity, security, and work-life balance.

ELIGIBILITY
Remote work is available to employees who:
• Have been employed for at least {min_tenure} months
• Demonstrate strong performance and self-management
• Have roles suitable for remote work
• Meet technology and security requirements

REMOTE WORK ARRANGEMENTS

Hybrid Schedule
• Up to {remote_days} days per week remote
• Core collaboration hours: {core_hours}
• Required in-office days: {required_office_days}

Full Remote
• Available for specific roles and circumstances
• Requires manager and HR approval
• Subject to periodic review

TECHNOLOGY REQUIREMENTS

Equipment Provided
• Company laptop with required software
• Monitor and ergonomic accessories
• High-speed internet stipend: ${internet_stipend}/month
• Mobile phone for business use

Security Requirements
• VPN connection for all work activities
• Multi-factor authentication enabled
• Secure home office environment
• Regular security training completion

PERFORMANCE EXPECTATIONS

Productivity Standards
• Maintain same performance levels as in-office work
• Participate actively in virtual meetings
• Respond to communications within {response_time} hours
• Complete regular check-ins with manager

Communication Guidelines
• Daily standup participation
• Weekly one-on-one meetings
• Quarterly in-person team meetings
• Use company communication tools only

HOME OFFICE REQUIREMENTS

Workspace Setup
• Dedicated, quiet workspace
• Ergonomic setup to prevent injury
• Adequate lighting and ventilation
• Professional background for video calls

Health and Safety
• Regular breaks and movement
• Ergonomic assessments available
• Mental health resources provided
• Work-life balance encouraged

COMPLIANCE AND MONITORING

Data Protection
• Confidential information remains on company devices
• No personal cloud storage for work files
• Secure disposal of printed materials
• Regular security audits

Time Tracking
• Accurate time reporting required
• Project time allocation tracking
• Overtime approval process unchanged

POLICY REVIEW
This policy will be reviewed annually and updated as needed based on:
• Employee feedback
• Business requirements
• Technology changes
• Legal and compliance updates

For questions or requests, contact HR at hr@{company_domain}

Approved by: {approver_name}, Chief Human Resources Officer
Effective Date: {effective_date}
""",
                "metadata": {"policy_type": "remote_work", "approval_level": "executive", "review_frequency": "annual"}
            }
        ]
    
    def _get_marketing_templates(self) -> List[Dict]:
        """Real marketing document templates"""
        return [
            {
                "title": "Product Launch Strategy - {product_name}",
                "content": """PRODUCT LAUNCH STRATEGY
Product: {product_name}
Launch Date: {launch_date}
Strategy Version: {version}

EXECUTIVE SUMMARY
{product_name} represents a significant opportunity to {value_proposition}. This launch strategy outlines our approach to achieve {target_metric} within {timeframe}.

PRODUCT OVERVIEW

Key Features
• {feature_1}: {feature_1_description}
• {feature_2}: {feature_2_description}
• {feature_3}: {feature_3_description}

Competitive Advantages
• {advantage_1}
• {advantage_2}
• {advantage_3}

Target Market
• Primary: {primary_market}
• Secondary: {secondary_market}
• Market Size: ${market_size:,}
• Addressable Market: ${addressable_market:,}

LAUNCH STRATEGY

Pre-Launch Phase ({pre_launch_duration})
• Beta testing with {beta_users} selected customers
• Content creation and marketing asset development
• Sales team training and enablement
• Partner channel preparation

Launch Phase ({launch_duration})
• Coordinated announcement across all channels
• Press release and media outreach
• Product demonstrations and webinars
• Early adopter incentive program

Post-Launch Phase ({post_launch_duration})
• Performance monitoring and optimization
• Customer feedback collection and analysis
• Feature iteration based on user data
• Expansion to additional market segments

MARKETING CHANNELS

Digital Marketing
• Search Engine Marketing (SEM): ${sem_budget:,}
• Social Media Advertising: ${social_budget:,}
• Content Marketing: ${content_budget:,}
• Email Marketing: ${email_budget:,}

Traditional Marketing
• Industry Events: ${events_budget:,}
• Print Advertising: ${print_budget:,}
• Direct Mail: ${direct_mail_budget:,}

Partnership Marketing
• Channel Partner Co-marketing: ${partner_budget:,}
• Industry Analyst Relations
• Strategic Alliance Announcements

SALES ENABLEMENT

Training Program
• Product knowledge sessions
• Competitive positioning
• Demo scenarios and objection handling
• Sales tools and collateral

Sales Materials
• Product datasheets and brochures
• ROI calculators and business cases
• Customer success stories
• Competitive comparison guides

METRICS AND SUCCESS CRITERIA

Launch Metrics
• {metric_1}: {target_1}
• {metric_2}: {target_2}
• {metric_3}: {target_3}

90-Day Targets
• New Customers: {customer_target:,}
• Revenue: ${revenue_target:,}
• Market Share: {market_share_target:.1f}%

Long-term Goals (12 months)
• Total Customers: {annual_customer_target:,}
• Annual Revenue: ${annual_revenue_target:,}
• Customer Satisfaction: {satisfaction_target:.1f}/5.0

RISK MITIGATION

Identified Risks
• Competitive response: {competitive_risk_mitigation}
• Technical issues: {technical_risk_mitigation}
• Market conditions: {market_risk_mitigation}

Contingency Plans
• Alternative launch dates
• Budget reallocation options
• Messaging pivots

BUDGET ALLOCATION
Total Launch Budget: ${total_budget:,}

• Marketing: ${marketing_budget:,} ({marketing_percent:.1f}%)
• Sales: ${sales_budget:,} ({sales_percent:.1f}%)
• Product: ${product_budget:,} ({product_percent:.1f}%)
• Operations: ${operations_budget:,} ({operations_percent:.1f}%)

TIMELINE
{timeline_details}

Prepared by: {author_name}, Product Marketing Manager
Approved by: {approver_name}, VP Marketing
Document Classification: Confidential
""",
                "metadata": {"product": "{product_name}", "launch_phase": "planning", "confidentiality": "internal"}
            }
        ]
    
    def _get_operations_templates(self) -> List[Dict]:
        """Real operations document templates"""
        return [
            {
                "title": "Incident Response Playbook",
                "content": """INCIDENT RESPONSE PLAYBOOK
Emergency Response Procedures

INCIDENT CLASSIFICATION

Severity Levels
• P0 (Critical): Complete service outage, data breach, security incident
• P1 (High): Major functionality impaired, significant customer impact
• P2 (Medium): Minor functionality affected, workaround available
• P3 (Low): Cosmetic issues, minimal customer impact

Response Time Targets
• P0: Immediate response (within 15 minutes)
• P1: 1 hour response time
• P2: 4 hour response time
• P3: Next business day

INCIDENT RESPONSE PROCESS

1. DETECTION AND ALERTING
• Automated monitoring alerts
• Customer reports via support channels
• Internal team discovery
• Security monitoring systems

2. INITIAL RESPONSE (First 15 minutes)
• Acknowledge incident in monitoring system
• Assess severity and impact
• Notify incident commander
• Begin initial investigation

3. ESCALATION AND COMMUNICATION
• Notify stakeholders based on severity
• Create incident communication channel
• Update status page if customer-facing
• Begin customer communication

4. INVESTIGATION AND DIAGNOSIS
• Gather logs and system metrics
• Identify root cause
• Document timeline of events
• Assess scope of impact

5. RESOLUTION AND RECOVERY
• Implement fix or workaround
• Verify system functionality
• Monitor for stability
• Confirm customer impact resolved

6. POST-INCIDENT REVIEW
• Conduct blameless post-mortem
• Document lessons learned
• Identify process improvements
• Update runbooks and procedures

COMMUNICATION TEMPLATES

Internal Notification (P0/P1)
Subject: [P{severity}] {incident_title}
- Impact: {impact_description}
- Status: {current_status}
- ETA: {estimated_resolution}
- Updates: Every {update_frequency} minutes

Customer Communication
Subject: Service Update - {service_name}
We are currently experiencing {issue_description}. 
Our team is actively working on a resolution.
Next update: {next_update_time}

ESCALATION MATRIX
• P0 Incidents: CEO, CTO, VP Engineering
• P1 Incidents: VP Engineering, Engineering Managers
• P2 Incidents: Engineering Managers, Team Leads
• P3 Incidents: Team Leads, Individual Engineers

ON-CALL PROCEDURES
• Primary on-call: First responder
• Secondary on-call: Escalation point
• Manager on-call: Executive decisions
• Rotation schedule: Weekly rotation

TOOLS AND RESOURCES
• Monitoring: Grafana dashboards
• Alerting: PagerDuty integration
• Communication: Slack incident channels
• Documentation: Confluence runbooks

COMMON SCENARIOS

Database Issues
1. Check connection pool status
2. Review slow query logs
3. Verify disk space and memory
4. Consider read replica failover

API Performance Issues
1. Check response time metrics
2. Review error rate trends
3. Analyze traffic patterns
4. Scale resources if needed

Search Service Degradation
1. Verify Elasticsearch cluster health
2. Check index status and size
3. Review query performance
4. Consider index optimization

This playbook should be reviewed quarterly and updated based on incident learnings.

Emergency Contact: +1-555-0199 (24/7 hotline)
""",
                "metadata": {"procedure_type": "incident_response", "criticality": "high", "review_frequency": "quarterly"}
            }
        ]
    
    def _get_healthcare_templates(self) -> List[Dict]:
        """Healthcare industry document templates"""
        return [
            {
                "title": "HIPAA Privacy Policy {year}",
                "content": """HIPAA PRIVACY POLICY
Healthcare Information Privacy and Security

EFFECTIVE DATE: {date}
VERSION: {version}

POLICY STATEMENT
This policy establishes procedures for protecting patient health information (PHI) in compliance with the Health Insurance Portability and Accountability Act (HIPAA).

SCOPE
This policy applies to all workforce members, business associates, and third parties who have access to PHI.

DEFINITIONS
• PHI: Individually identifiable health information
• Covered Entity: Healthcare providers, health plans, healthcare clearinghouses
• Business Associate: Third parties that handle PHI on behalf of covered entities

PRIVACY REQUIREMENTS

Minimum Necessary Standard
• Access to PHI limited to minimum necessary for job function
• Regular review of access permissions
• Role-based access controls implemented

Patient Rights
• Right to access their own health records
• Right to request amendments to their records
• Right to an accounting of disclosures
• Right to request restrictions on use/disclosure

SECURITY SAFEGUARDS

Administrative Safeguards
• Security officer designated
• Workforce training on HIPAA requirements
• Access management procedures
• Incident response procedures

Physical Safeguards
• Facility access controls
• Workstation use restrictions
• Device and media controls
• Secure disposal of PHI

Technical Safeguards
• Access control (unique user identification)
• Audit controls and monitoring
• Integrity controls
• Transmission security (encryption)

BREACH NOTIFICATION
• Risk assessment within 24 hours
• Patient notification within 60 days
• HHS notification within 60 days
• Media notification if breach affects 500+ individuals

VIOLATIONS AND PENALTIES
Violations may result in:
• Civil penalties up to $1.5 million per incident
• Criminal penalties up to $250,000 and 10 years imprisonment
• Immediate termination of employment

Contact: Privacy Officer at privacy@{company_domain}
""",
                "metadata": {"regulation": "HIPAA", "industry": "healthcare", "compliance_level": "required"}
            },
            {
                "title": "Patient Safety Protocol",
                "content": """PATIENT SAFETY PROTOCOL
Comprehensive Safety Guidelines

MEDICATION ADMINISTRATION

Five Rights of Medication Administration
1. Right Patient - Verify patient identity using two identifiers
2. Right Medication - Check medication name and verify order
3. Right Dose - Calculate and verify dosage accuracy
4. Right Route - Confirm administration method (oral, IV, etc.)
5. Right Time - Administer at prescribed intervals

High-Alert Medications
• Insulin and hypoglycemic agents
• Anticoagulants (warfarin, heparin)
• Chemotherapy agents
• Concentrated electrolytes
• Opioid analgesics

INFECTION CONTROL

Standard Precautions
• Hand hygiene before and after patient contact
• Personal protective equipment (PPE) use
• Safe injection practices
• Respiratory hygiene/cough etiquette

Isolation Precautions
• Contact precautions for MRSA, C. diff
• Droplet precautions for influenza, pertussis
• Airborne precautions for tuberculosis, measles

FALL PREVENTION

Risk Assessment
• Morse Fall Scale assessment on admission
• Daily reassessment for high-risk patients
• Environmental safety checks

Prevention Strategies
• Bed alarms for high-risk patients
• Non-slip footwear
• Clear pathways and adequate lighting
• Assistance with ambulation

EMERGENCY PROCEDURES

Code Blue (Cardiac Arrest)
1. Call 911 and announce "Code Blue" with location
2. Begin CPR immediately
3. Retrieve crash cart and AED
4. Assign roles: team leader, compressions, airway, medications

Code Red (Fire Emergency)
1. R.A.C.E. protocol: Rescue, Alarm, Contain, Evacuate
2. Remove patients from immediate danger
3. Activate fire alarm
4. Close doors to contain fire
5. Evacuate per facility plan

This protocol must be reviewed annually by all clinical staff.

Emergency Contact: Charge Nurse {phone_number}
""",
                "metadata": {"protocol_type": "patient_safety", "review_frequency": "annual", "training_required": "yes"}
            },
            {
                "title": "Medical Device Maintenance Log",
                "content": """MEDICAL DEVICE MAINTENANCE LOG
Equipment Safety and Compliance Tracking

DEVICE INFORMATION
Device Name: Ventilator Model VT-3000
Serial Number: VT{serial_number}
Manufacturer: MedTech Solutions
Installation Date: {date}
Last Calibration: {calibration_date}

MAINTENANCE SCHEDULE

Daily Checks
• Visual inspection for damage
• Function test of alarms
• Battery backup verification
• Cleaning and disinfection

Weekly Maintenance
• Filter replacement
• Tubing inspection
• Pressure calibration check
• Software updates if available

Monthly Maintenance
• Complete functional testing
• Electrical safety inspection
• Preventive maintenance tasks
• Documentation review

Annual Certification
• Biomedical engineering inspection
• Calibration verification
• Safety testing
• Regulatory compliance check

INCIDENT REPORTING
Any device malfunction must be reported immediately to:
• Biomedical Engineering: ext. 2150
• Risk Management: ext. 2175
• FDA MedWatch (if required): 1-800-FDA-1088

REGULATORY COMPLIANCE
• FDA 21 CFR Part 820 (Quality System Regulation)
• Joint Commission standards
• State health department requirements
• Manufacturer recommendations

Maintenance performed by: {technician_name}
Next scheduled maintenance: {next_maintenance_date}
""",
                "metadata": {"device_type": "ventilator", "regulatory": "FDA", "maintenance_cycle": "monthly"}
            }
        ]
    
    def _get_real_estate_templates(self) -> List[Dict]:
        """Real estate industry document templates"""
        return [
            {
                "title": "Property Purchase Agreement",
                "content": """REAL ESTATE PURCHASE AGREEMENT

BUYER: {buyer_name}
SELLER: {seller_name}
PROPERTY ADDRESS: {property_address}
PURCHASE PRICE: ${purchase_price:,}

TERMS AND CONDITIONS

Purchase Price and Financing
• Total Purchase Price: ${purchase_price:,}
• Earnest Money Deposit: ${earnest_money:,}
• Down Payment: {down_payment_percent}%
• Financing Contingency: {financing_days} days

Property Description
• Legal Description: {legal_description}
• Parcel ID: {parcel_id}
• Square Footage: {square_footage:,} sq ft
• Lot Size: {lot_size} acres
• Year Built: {year_built}

Inspections and Contingencies
• Home Inspection: {inspection_days} days
• Appraisal Contingency: Property must appraise at purchase price
• Title Contingency: Clear and marketable title required
• Environmental Inspection: Radon, lead, asbestos testing

Closing Information
• Closing Date: {closing_date}
• Possession Date: {possession_date}
• Title Company: {title_company}
• Closing Location: {closing_location}

Seller Disclosures
• Property Condition Disclosure completed
• Lead-based paint disclosure (if built before 1978)
• Flood zone disclosure
• HOA information provided

Inclusions/Exclusions
Included: All fixtures, built-in appliances, window treatments
Excluded: Personal property, decorative items, outdoor furniture

Default and Remedies
• Time is of the essence
• Specific performance available
• Attorney fees to prevailing party

This agreement is binding upon execution by all parties.

Buyer Signature: _________________ Date: _______
Seller Signature: ________________ Date: _______
""",
                "metadata": {"transaction_type": "purchase", "property_type": "residential", "contract_status": "active"}
            },
            {
                "title": "Property Appraisal Report",
                "content": """UNIFORM RESIDENTIAL APPRAISAL REPORT

PROPERTY ADDRESS: {property_address}
BORROWER: {borrower_name}
LENDER: {lender_name}
APPRAISAL DATE: {date}

PROPERTY DESCRIPTION
Property Type: Single Family Residence
Design: {design_style}
Year Built: {year_built}
Gross Living Area: {square_footage:,} sq ft
Total Rooms: {total_rooms}
Bedrooms: {bedrooms}
Bathrooms: {bathrooms}

SITE DESCRIPTION
Site Area: {lot_size} acres
Zoning: {zoning_classification}
Utilities: All public utilities available
Street: Paved, public street
Drainage: Adequate

IMPROVEMENTS DESCRIPTION
Foundation: {foundation_type}
Exterior Walls: {exterior_material}
Roof: {roof_material}
Heating/Cooling: {hvac_system}
Electrical: {electrical_system}
Plumbing: {plumbing_system}

SALES COMPARISON APPROACH

Comparable Sale #1
Address: {comp1_address}
Sale Price: ${comp1_price:,}
Sale Date: {comp1_date}
Square Footage: {comp1_sqft:,}
Price per Sq Ft: ${comp1_psf}

Comparable Sale #2
Address: {comp2_address}
Sale Price: ${comp2_price:,}
Sale Date: {comp2_date}
Square Footage: {comp2_sqft:,}
Price per Sq Ft: ${comp2_psf}

Comparable Sale #3
Address: {comp3_address}
Sale Price: ${comp3_price:,}
Sale Date: {comp3_date}
Square Footage: {comp3_sqft:,}
Price per Sq Ft: ${comp3_psf}

RECONCILIATION AND FINAL VALUE OPINION

Market Value Conclusion: ${appraised_value:,}

This appraisal is subject to the assumptions and limiting conditions.

Appraiser: {appraiser_name}, Certified Residential Appraiser
License #: {license_number}
""",
                "metadata": {"appraisal_type": "residential", "purpose": "purchase", "effective_date": "{date}"}
            },
            {
                "title": "Property Management Agreement",
                "content": """PROPERTY MANAGEMENT AGREEMENT

OWNER: {owner_name}
PROPERTY MANAGER: {company}
PROPERTY: {property_address}

MANAGEMENT SERVICES

Tenant Relations
• Tenant screening and selection
• Lease preparation and execution
• Rent collection and deposit handling
• Tenant communication and issue resolution
• Eviction proceedings if necessary

Property Maintenance
• Routine maintenance coordination
• Emergency repair response (24/7)
• Vendor management and oversight
• Property inspections (monthly)
• Preventive maintenance scheduling

Financial Management
• Monthly financial statements
• Rent collection and late fee assessment
• Security deposit management
• Tax document preparation (1099s)
• Annual budget preparation

COMPENSATION
Management Fee: {management_fee_percent}% of gross monthly rent
Leasing Fee: {leasing_fee_percent}% of first month's rent
Maintenance Markup: {maintenance_markup}% on repairs over ${markup_threshold}

TERMS
• Agreement Term: {term_length} years
• Automatic renewal unless 60-day notice given
• Either party may terminate with 30-day notice
• Owner reserves right to approve expenses over ${approval_threshold:,}

INSURANCE AND LIABILITY
• Property manager maintains E&O insurance
• Owner maintains property insurance
• Both parties maintain general liability coverage

This agreement governed by laws of {jurisdiction}.

Owner Signature: _________________ Date: _______
Manager Signature: _______________ Date: _______
""",
                "metadata": {"agreement_type": "property_management", "term_years": "3", "auto_renewal": "yes"}
            }
        ]
    
    def _get_academic_templates(self) -> List[Dict]:
        """Academic institution document templates"""
        return [
            {
                "title": "Research Proposal: {research_topic}",
                "content": """RESEARCH PROPOSAL
{research_topic}

PRINCIPAL INVESTIGATOR: {author_name}
DEPARTMENT: {department}
INSTITUTION: {institution_name}
SUBMISSION DATE: {date}

ABSTRACT
This research investigates {research_objective}. The study aims to {research_goal} through {methodology_type} analysis. Expected outcomes include {expected_outcomes}.

BACKGROUND AND SIGNIFICANCE
{research_background}

The significance of this research lies in its potential to {research_impact}. Previous studies have shown {previous_findings}, but gaps remain in {research_gaps}.

RESEARCH OBJECTIVES
Primary Objective: {primary_objective}
Secondary Objectives:
• {secondary_obj_1}
• {secondary_obj_2}
• {secondary_obj_3}

METHODOLOGY
Study Design: {study_design}
Sample Size: {sample_size} participants
Data Collection: {data_collection_method}
Analysis Plan: {analysis_method}

Timeline: {timeline_months} months
Budget: ${budget:,}

ETHICAL CONSIDERATIONS
• IRB approval required
• Informed consent procedures
• Data privacy and confidentiality
• Risk mitigation strategies

EXPECTED OUTCOMES
This research will contribute to {field_contribution} and provide {practical_applications}.

REFERENCES
{reference_count} peer-reviewed sources cited.

Principal Investigator Signature: ________________
Department Chair Approval: ___________________
""",
                "metadata": {"research_type": "proposal", "department": "{department}", "funding_required": "yes"}
            },
            {
                "title": "Course Syllabus: {course_name}",
                "content": """COURSE SYLLABUS
{course_name}
{course_code} | {credit_hours} Credit Hours

INSTRUCTOR: {instructor_name}
OFFICE: {office_location}
EMAIL: {instructor_email}
OFFICE HOURS: {office_hours}

COURSE DESCRIPTION
{course_description}

This course examines {course_focus} through {teaching_method}. Students will develop {learning_outcomes}.

LEARNING OBJECTIVES
Upon completion of this course, students will be able to:
1. {objective_1}
2. {objective_2}
3. {objective_3}
4. {objective_4}

REQUIRED MATERIALS
• Textbook: {textbook_title}
• Course packet available at bookstore
• Access to online learning platform
• Calculator (scientific)

COURSE SCHEDULE
Week 1-4: {module_1}
Week 5-8: {module_2}
Week 9-12: {module_3}
Week 13-16: {module_4}

ASSESSMENT
Participation: {participation_percent}%
Assignments: {assignments_percent}%
Midterm Exam: {midterm_percent}%
Final Project: {final_percent}%

GRADING SCALE
A: 90-100%    B: 80-89%    C: 70-79%    D: 60-69%    F: Below 60%

POLICIES
Attendance: Regular attendance expected
Late Work: 10% penalty per day late
Academic Integrity: Plagiarism will result in course failure
Accommodations: Students with disabilities should contact Disability Services

IMPORTANT DATES
Midterm Exam: {midterm_date}
Final Project Due: {final_due_date}
Final Exam: {final_exam_date}

Questions? Email {instructor_email} or visit during office hours.
""",
                "metadata": {"semester": "{semester}", "department": "{department}", "level": "undergraduate"}
            },
            {
                "title": "Graduate Thesis: {thesis_title}",
                "content": """GRADUATE THESIS
{thesis_title}

SUBMITTED BY: {author_name}
STUDENT ID: {student_id}
DEGREE PROGRAM: {degree_program}
ADVISOR: {advisor_name}
SUBMISSION DATE: {date}

ABSTRACT
{thesis_abstract}

This thesis presents {research_contribution} through {research_methodology}. Key findings include {key_findings}.

TABLE OF CONTENTS
Chapter 1: Introduction
Chapter 2: Literature Review
Chapter 3: Methodology
Chapter 4: Results and Analysis
Chapter 5: Discussion and Conclusions

CHAPTER 1: INTRODUCTION

1.1 Background
{introduction_background}

1.2 Problem Statement
{problem_statement}

1.3 Research Questions
Primary Research Question: {primary_question}
Secondary Questions:
• {secondary_q1}
• {secondary_q2}

1.4 Significance of Study
{study_significance}

CHAPTER 2: LITERATURE REVIEW
{literature_review_summary}

CHAPTER 3: METHODOLOGY
Research Design: {research_design}
Population: {target_population}
Sample Size: {sample_size}
Data Collection: {data_collection}
Analysis: {analysis_method}

CHAPTER 4: RESULTS
{results_summary}

Statistical analysis revealed {statistical_findings}. The correlation between {variable_1} and {variable_2} was {correlation_strength}.

CHAPTER 5: CONCLUSIONS
{conclusions_summary}

Future research should explore {future_research_directions}.

REFERENCES
{reference_count} scholarly sources cited following APA format.

Committee Approval:
Advisor: _________________ Date: _______
Committee Member: ________ Date: _______
Committee Member: ________ Date: _______
""",
                "metadata": {"thesis_type": "masters", "defense_date": "{defense_date}", "committee_size": "3"}
            }
        ]
    
    def _get_manufacturing_templates(self) -> List[Dict]:
        """Manufacturing industry document templates"""
        return [
            {
                "title": "Quality Control Specification",
                "content": """QUALITY CONTROL SPECIFICATION
Product: {product_name}
Part Number: {part_number}
Revision: {version}

DIMENSIONAL SPECIFICATIONS
Length: {length} ± {length_tolerance} mm
Width: {width} ± {width_tolerance} mm
Height: {height} ± {height_tolerance} mm
Weight: {weight} ± {weight_tolerance} grams

MATERIAL SPECIFICATIONS
Primary Material: {material_type}
Grade: {material_grade}
Hardness: {hardness_rating} HRC
Surface Finish: {surface_finish} Ra

TESTING REQUIREMENTS

Incoming Inspection
• Visual inspection for defects
• Dimensional verification (100% check)
• Material certification review
• Certificate of conformance required

In-Process Testing
• Dimensional checks every {check_frequency} units
• Surface finish verification
• Functional testing at {test_intervals}
• Statistical process control monitoring

Final Inspection
• Complete dimensional inspection
• Functional performance testing
• Packaging and labeling verification
• Final quality sign-off required

ACCEPTANCE CRITERIA
• Zero critical defects allowed
• Major defects: < {major_defect_limit}%
• Minor defects: < {minor_defect_limit}%
• Cpk value: > {cpk_requirement}

NON-CONFORMING MATERIAL
• Immediate quarantine of defective parts
• Root cause analysis required
• Corrective action implementation
• Supplier notification within 24 hours

DOCUMENTATION
• Inspection records retained for {retention_years} years
• Test certificates filed by lot number
• Non-conformance reports tracked
• Supplier performance metrics updated

Quality Manager: {quality_manager}
Approved by: {approver_name}
Effective Date: {date}
""",
                "metadata": {"product_line": "automotive", "quality_standard": "ISO_9001", "revision": "{version}"}
            },
            {
                "title": "Safety Data Sheet (SDS)",
                "content": """SAFETY DATA SHEET
According to OSHA Hazard Communication Standard

SECTION 1: IDENTIFICATION
Product Name: {chemical_name}
Product Code: {product_code}
Manufacturer: {company}
Emergency Phone: +1-800-424-9300 (CHEMTREC)

SECTION 2: HAZARD IDENTIFICATION
Classification: {hazard_classification}
Signal Word: {signal_word}
Hazard Statements: {hazard_statements}
Precautionary Statements: {precautionary_statements}

SECTION 3: COMPOSITION
Chemical Name: {chemical_name}
CAS Number: {cas_number}
Concentration: {concentration}%

SECTION 4: FIRST AID MEASURES
Inhalation: Remove to fresh air. Seek medical attention if symptoms persist.
Skin Contact: Wash with soap and water for 15 minutes.
Eye Contact: Flush with water for 15 minutes. Remove contact lenses.
Ingestion: Do not induce vomiting. Seek immediate medical attention.

SECTION 5: FIRE-FIGHTING MEASURES
Extinguishing Media: {extinguishing_media}
Special Hazards: {fire_hazards}
Protective Equipment: Full protective gear and SCBA required

SECTION 6: ACCIDENTAL RELEASE MEASURES
Personal Precautions: Wear appropriate PPE
Environmental Precautions: Prevent release to waterways
Cleanup Methods: {cleanup_procedure}

SECTION 7: HANDLING AND STORAGE
Handling: {handling_precautions}
Storage: {storage_requirements}
Temperature: Store between {min_temp}°C and {max_temp}°C

SECTION 8: EXPOSURE CONTROLS
Exposure Limits: {exposure_limit} ppm (8-hour TWA)
Engineering Controls: {engineering_controls}
PPE Required: {ppe_requirements}

This SDS prepared in accordance with OSHA HCS 2012.
Revision Date: {date}
""",
                "metadata": {"chemical_class": "industrial", "hazard_level": "moderate", "osha_compliant": "yes"}
            }
        ]
    
    def _get_retail_templates(self) -> List[Dict]:
        """Retail industry document templates"""
        return [
            {
                "title": "Inventory Management Policy",
                "content": """INVENTORY MANAGEMENT POLICY
Retail Operations Manual

POLICY STATEMENT
This policy establishes procedures for effective inventory management to optimize stock levels, minimize losses, and ensure product availability.

INVENTORY CLASSIFICATION

A-Class Items (High Value)
• 20% of items, 80% of value
• Daily monitoring required
• Automated reorder points
• Manager approval for adjustments

B-Class Items (Medium Value)
• 30% of items, 15% of value
• Weekly monitoring
• Standard reorder procedures
• Supervisor approval required

C-Class Items (Low Value)
• 50% of items, 5% of value
• Monthly monitoring
• Bulk ordering strategies
• Staff-level management

RECEIVING PROCEDURES
1. Verify shipment against purchase order
2. Inspect for damage or defects
3. Update inventory system immediately
4. Store according to product requirements
5. Process vendor invoices within 24 hours

CYCLE COUNTING
• A-items: Monthly full count
• B-items: Quarterly count
• C-items: Annual count
• Variance tolerance: ±{variance_tolerance}%

LOSS PREVENTION
• Security camera monitoring
• Electronic article surveillance (EAS)
• Regular shrinkage analysis
• Employee bag checks
• Vendor compliance audits

SEASONAL PLANNING
• Forecast demand 90 days in advance
• Adjust safety stock for promotions
• Plan markdown schedules
• Coordinate with marketing campaigns

PERFORMANCE METRICS
• Inventory turnover: Target {turnover_target}x annually
• Stockout rate: < {stockout_target}%
• Shrinkage rate: < {shrinkage_target}%
• Gross margin: > {margin_target}%

TECHNOLOGY SYSTEMS
• POS integration with inventory
• Barcode scanning for all transactions
• Automated low-stock alerts
• Real-time reporting dashboard

Contact: Operations Manager at ops@{company_domain}
""",
                "metadata": {"policy_type": "inventory", "review_frequency": "annual", "compliance_required": "yes"}
            }
        ]
    
    async def generate_realistic_users(self, session: AsyncSession) -> Dict[str, User]:
        """Generate realistic business users"""
        logger.info("👥 Creating realistic business users...")
        
        # Generate users based on real business roles
        departments = ["engineering", "sales", "marketing", "finance", "hr", "operations", "legal"]
        
        users_to_create = []
        
        # Admin users (C-level and senior management)
        admin_titles = ["CEO", "CTO", "CFO", "CHRO", "COO"]
        for i, title in enumerate(admin_titles):
            domain = random.choice(self.business_domains)
            first_name = fake.first_name()
            last_name = fake.last_name()
            
            users_to_create.append({
                "key": f"admin_{title.lower()}",
                "email": f"{first_name.lower()}.{last_name.lower()}@{domain}",
                "username": f"{first_name.lower()}_{last_name.lower()}",
                "full_name": f"{first_name} {last_name}",
                "title": title,
                "department": "executive",
                "role": UserRole.ADMIN,
                "is_verified": True
            })
        
        # Reviewer users (managers and senior staff)
        reviewer_roles = [
            ("Engineering Manager", "engineering"),
            ("Legal Counsel", "legal"),
            ("Senior Financial Analyst", "finance"),
            ("Quality Assurance Lead", "engineering"),
            ("Compliance Manager", "legal")
        ]
        
        for title, dept in reviewer_roles:
            domain = random.choice(self.business_domains)
            first_name = fake.first_name()
            last_name = fake.last_name()
            
            users_to_create.append({
                "key": f"reviewer_{dept}_{i}",
                "email": f"{first_name.lower()}.{last_name.lower()}@{domain}",
                "username": f"{first_name.lower()}_{last_name.lower()}",
                "full_name": f"{first_name} {last_name}",
                "title": title,
                "department": dept,
                "role": UserRole.REVIEWER,
                "is_verified": True
            })
        
        # Uploader users (content creators and specialists)
        uploader_roles = [
            ("Technical Writer", "engineering"),
            ("Marketing Specialist", "marketing"),
            ("HR Business Partner", "hr"),
            ("Sales Operations Analyst", "sales"),
            ("Financial Analyst", "finance"),
            ("Operations Coordinator", "operations")
        ]
        
        for title, dept in uploader_roles:
            domain = random.choice(self.business_domains)
            first_name = fake.first_name()
            last_name = fake.last_name()
            
            users_to_create.append({
                "key": f"uploader_{dept}_{i}",
                "email": f"{first_name.lower()}.{last_name.lower()}@{domain}",
                "username": f"{first_name.lower()}_{last_name.lower()}",
                "full_name": f"{first_name} {last_name}",
                "title": title,
                "department": dept,
                "role": UserRole.UPLOADER,
                "is_verified": random.choice([True, True, True, False])  # Mostly verified
            })
        
        # Viewer users (general staff and external users)
        viewer_roles = [
            ("Software Engineer", "engineering"),
            ("Sales Representative", "sales"),
            ("Marketing Coordinator", "marketing"),
            ("Customer Success Manager", "sales"),
            ("External Consultant", "external"),
            ("Intern", "various")
        ]
        
        for title, dept in viewer_roles:
            domain = random.choice(self.business_domains) if dept != "external" else "consultant-firm.com"
            first_name = fake.first_name()
            last_name = fake.last_name()
            
            users_to_create.append({
                "key": f"viewer_{dept}_{i}",
                "email": f"{first_name.lower()}.{last_name.lower()}@{domain}",
                "username": f"{first_name.lower()}_{last_name.lower()}",
                "full_name": f"{first_name} {last_name}",
                "title": title,
                "department": dept,
                "role": UserRole.VIEWER,
                "is_verified": dept != "external"  # External users need verification
            })
        
        # Compliance users (audit and compliance specialists)
        compliance_roles = [
            ("Chief Compliance Officer", "compliance"),
            ("Internal Auditor", "finance"),
            ("Data Protection Officer", "legal"),
            ("Risk Management Specialist", "operations")
        ]
        
        for title, dept in compliance_roles:
            domain = random.choice(self.business_domains)
            first_name = fake.first_name()
            last_name = fake.last_name()
            
            users_to_create.append({
                "key": f"compliance_{dept}_{i}",
                "email": f"{first_name.lower()}.{last_name.lower()}@{domain}",
                "username": f"{first_name.lower()}_{last_name.lower()}",
                "full_name": f"{first_name} {last_name}",
                "title": title,
                "department": dept,
                "role": UserRole.COMPLIANCE,
                "is_verified": True
            })
        
        # Create users in database
        created_users = {}
        
        for user_data in users_to_create:
            # Check if user exists
            result = await session.execute(
                select(User).where(User.email == user_data["email"])
            )
            existing_user = result.scalar_one_or_none()
            
            if not existing_user:
                # Generate secure password
                password = fake.password(length=12, special_chars=True, digits=True, upper_case=True, lower_case=True)
                
                user = User(
                    email=user_data["email"],
                    username=user_data["username"],
                    full_name=user_data["full_name"],
                    hashed_password=get_password_hash(password),
                    role=user_data["role"],
                    is_active=True,
                    is_verified=user_data["is_verified"]
                )
                
                session.add(user)
                await session.flush()
                
                created_users[user_data["key"]] = {
                    "user": user,
                    "password": password,
                    "title": user_data["title"],
                    "department": user_data["department"]
                }
                
                logger.info(f"Created {user_data['role'].value}: {user_data['full_name']} ({user_data['title']})")
            else:
                created_users[user_data["key"]] = {
                    "user": existing_user,
                    "password": "existing_user",
                    "title": user_data.get("title", "Unknown"),
                    "department": user_data.get("department", "Unknown")
                }
        
        return created_users
    
    async def generate_realistic_documents(self, session: AsyncSession, users: Dict[str, Any]) -> List[Document]:
        """Generate realistic business documents"""
        logger.info("📄 Creating realistic business documents...")
        
        created_documents = []
        target_documents = 1200  # Generate 1200+ documents
        
        # Calculate documents per category
        categories = list(self.document_categories.keys())
        docs_per_category = target_documents // len(categories)
        
        logger.info(f"🎯 Target: {target_documents} documents ({docs_per_category} per category)")
        
        # Generate multiple variations for each category
        for category, config in self.document_categories.items():
            templates = config["templates"]
            category_count = 0
            
            # Generate multiple documents per template to reach target
            while category_count < docs_per_category:
                for template in templates:
                    if category_count >= docs_per_category:
                        break
                # Select appropriate uploader based on document type
                uploader_key = self._select_uploader_for_category(category, users)
                if not uploader_key or uploader_key not in users:
                    continue
                
                uploader_data = users[uploader_key]
                uploader = uploader_data["user"]
                
                # Add variation to template for uniqueness
                varied_template = self._add_document_variation(template, category, category_count)
                
                # Generate realistic content using varied template
                content = self._generate_document_content(varied_template, category, uploader_data)
                
                # Create realistic filename with variation
                timestamp = fake.date_between(start_date='-2y', end_date='today').strftime('%Y%m%d')
                variation_suffix = f"_v{random.randint(1, 5)}" if random.random() < 0.3 else ""
                dept_suffix = f"_{uploader_data.get('department', '')}" if random.random() < 0.4 else ""
                filename = f"{varied_template['title'].lower().replace(' ', '_').replace(':', '').replace('{', '').replace('}', '')}_{timestamp}{variation_suffix}{dept_suffix}.{random.choice(['pdf', 'docx', 'txt', 'xlsx', 'pptx'])}"
                
                # Generate file
                content_bytes = content.encode('utf-8')
                file_hash = hashlib.sha256(content_bytes).hexdigest()
                
                # Save to storage
                storage_path = self.storage_path / f"{file_hash}.txt"  # Store as text for simplicity
                storage_path.write_bytes(content_bytes)
                
                # Determine access level based on content sensitivity
                access_level = self._determine_access_level(template, category)
                
                # Create document record
                document = Document(
                    uuid=uuid.uuid4(),
                    filename=filename,
                    file_type="txt",  # Simplified for demonstration
                    file_size=len(content_bytes),
                    file_hash=file_hash,
                    storage_path=str(storage_path),
                    status="indexed",
                    virus_scan_status="clean",
                    title=template["title"],
                    description=f"Generated {category} document demonstrating {template.get('purpose', 'business functionality')}",
                    tags=self._generate_realistic_tags(category, template),
                    full_text=content,
                    language="en",
                    access_level=access_level,
                    uploaded_by=uploader.id,
                    custom_metadata={
                        "category": category,
                        "generator": "realistic_seed",
                        "uploader_department": uploader_data["department"],
                        "uploader_title": uploader_data["title"],
                        "business_purpose": template.get("purpose", "operational"),
                        "generated_at": datetime.now().isoformat()
                    }
                )
                
                session.add(document)
                created_documents.append(document)
                category_count += 1
                
                if category_count % 20 == 0:  # Progress logging
                    logger.info(f"📄 {category.title()}: {category_count}/{docs_per_category} documents created")
                
                # Commit in batches to avoid memory issues
                if len(created_documents) % 100 == 0:
                    await session.commit()
                    logger.info(f"💾 Committed batch: {len(created_documents)} documents total")
        
        await session.flush()
        logger.info(f"✅ Created {len(created_documents)} realistic business documents")
        return created_documents
    
    def _select_uploader_for_category(self, category: str, users: Dict[str, Any]) -> str:
        """Select appropriate uploader based on document category"""
        category_uploaders = {
            "legal": [k for k in users.keys() if "legal" in k or ("admin" in k and "legal" in users[k]["department"])],
            "finance": [k for k in users.keys() if "finance" in k or ("admin" in k and "cfo" in k)],
            "hr": [k for k in users.keys() if "hr" in k or ("admin" in k and "chro" in k)],
            "technical": [k for k in users.keys() if "engineering" in k or ("admin" in k and "cto" in k)],
            "marketing": [k for k in users.keys() if "marketing" in k],
            "operations": [k for k in users.keys() if "operations" in k or ("admin" in k and "coo" in k)]
        }
        
        # Fall back to any uploader role if no specific match
        uploaders = category_uploaders.get(category, [])
        if not uploaders:
            uploaders = [k for k in users.keys() if users[k]["user"].role in [UserRole.UPLOADER, UserRole.ADMIN]]
        
        return random.choice(uploaders) if uploaders else None
    
    def _generate_document_content(self, template: Dict, category: str, uploader_data: Dict) -> str:
        """Generate realistic document content from template"""
        content = template["content"]
        
        # Replace placeholders with realistic data
        replacements = {
            "{date}": fake.date_between(start_date='-1y', end_date='today').strftime('%B %d, %Y'),
            "{company}": fake.company(),
            "{company_domain}": random.choice(self.business_domains),
            "{employee_name}": uploader_data["user"].full_name,
            "{author_name}": uploader_data["user"].full_name,
            "{approver_name}": fake.name(),
            "{jurisdiction}": fake.state(),
            "{version}": f"{random.randint(1,5)}.{random.randint(0,9)}",
            "{year}": str(fake.date_between(start_date='-1y', end_date='today').year),
            "{quarter}": f"Q{random.randint(1,4)}",
            "{month}": fake.month_name(),
            
            # Financial data
            "{revenue}": random.randint(500000, 5000000),
            "{net_income}": random.randint(50000, 500000),
            "{gross_profit}": random.randint(200000, 2000000),
            "{operating_expenses}": random.randint(150000, 1500000),
            "{ebitda}": random.randint(100000, 1000000),
            "{total_assets}": random.randint(1000000, 10000000),
            "{cash}": random.randint(100000, 2000000),
            
            # Metrics
            "{revenue_change}": random.uniform(-10, 25),
            "{gross_margin}": random.uniform(60, 85),
            "{net_margin}": random.uniform(10, 25),
            "{performance_trend}": random.choice(["strong", "steady", "improving", "mixed"]),
            
            # HR data
            "{vacation_days}": random.randint(15, 25),
            "{sick_days}": random.randint(5, 10),
            "{personal_days}": random.randint(2, 5),
            "{holiday_count}": random.randint(10, 15),
            "{health_contribution}": random.randint(75, 90),
            "{match_percent}": random.randint(3, 6),
            "{training_budget}": random.randint(2000, 5000),
            
            # Product data
            "{product_name}": f"{fake.word().title()} {random.choice(['Pro', 'Enterprise', 'Suite', 'Platform'])}",
            "{launch_date}": fake.date_between(start_date='today', end_date='+6m').strftime('%B %d, %Y'),
            "{value_proposition}": random.choice([
                "increase operational efficiency",
                "reduce costs and improve margins", 
                "enhance customer experience",
                "accelerate digital transformation"
            ]),
            
            # Healthcare data
            "{patient_id}": f"PT{random.randint(100000, 999999)}",
            "{medical_record_number}": f"MR{random.randint(1000000, 9999999)}",
            "{diagnosis_code}": f"{random.choice(['M', 'F', 'G', 'I'])}{random.randint(10, 99)}.{random.randint(0, 9)}",
            "{physician_name}": fake.name(),
            "{hospital_name}": f"{fake.city()} Medical Center",
            "{phone_number}": fake.phone_number(),
            "{serial_number}": random.randint(100000, 999999),
            "{calibration_date}": fake.date_between(start_date='-3m', end_date='today').strftime('%B %d, %Y'),
            "{technician_name}": fake.name(),
            "{next_maintenance_date}": fake.date_between(start_date='today', end_date='+3m').strftime('%B %d, %Y'),
            
            # Real Estate data
            "{buyer_name}": fake.name(),
            "{seller_name}": fake.name(),
            "{property_address}": fake.address(),
            "{purchase_price}": random.randint(250000, 800000),
            "{earnest_money}": random.randint(5000, 20000),
            "{down_payment_percent}": random.randint(10, 25),
            "{financing_days}": random.randint(30, 45),
            "{legal_description}": f"Lot {random.randint(1, 50)}, Block {random.randint(1, 20)}, {fake.city()} Subdivision",
            "{parcel_id}": f"{random.randint(100, 999)}-{random.randint(100, 999)}-{random.randint(100, 999)}",
            "{square_footage}": random.randint(1200, 4500),
            "{lot_size}": round(random.uniform(0.15, 2.5), 2),
            "{year_built}": random.randint(1980, 2020),
            "{inspection_days}": random.randint(7, 14),
            "{closing_date}": fake.date_between(start_date='today', end_date='+60d').strftime('%B %d, %Y'),
            "{possession_date}": fake.date_between(start_date='today', end_date='+60d').strftime('%B %d, %Y'),
            "{title_company}": f"{fake.city()} Title & Escrow",
            "{closing_location}": fake.address(),
            "{borrower_name}": fake.name(),
            "{lender_name}": f"{fake.company()} Bank",
            "{design_style}": random.choice(["Colonial", "Ranch", "Contemporary", "Traditional", "Craftsman"]),
            "{total_rooms}": random.randint(6, 12),
            "{bedrooms}": random.randint(2, 5),
            "{bathrooms}": random.randint(1, 4),
            "{zoning_classification}": random.choice(["R-1", "R-2", "R-3", "PUD"]),
            "{foundation_type}": random.choice(["Concrete Slab", "Crawl Space", "Full Basement"]),
            "{exterior_material}": random.choice(["Vinyl Siding", "Brick", "Stone", "Stucco"]),
            "{roof_material}": random.choice(["Asphalt Shingle", "Metal", "Tile", "Slate"]),
            "{hvac_system}": random.choice(["Central Air/Heat", "Heat Pump", "Forced Air"]),
            "{electrical_system}": f"{random.randint(100, 200)} Amp Service",
            "{plumbing_system}": random.choice(["Copper", "PEX", "CPVC"]),
            "{appraised_value}": random.randint(240000, 820000),
            "{appraiser_name}": fake.name(),
            "{license_number}": f"CRA{random.randint(100000, 999999)}",
            
            # Academic data
            "{research_topic}": random.choice([
                "Machine Learning Applications in Healthcare",
                "Sustainable Energy Solutions for Urban Development",
                "Social Media Impact on Consumer Behavior",
                "Blockchain Technology in Supply Chain Management",
                "Climate Change Effects on Agricultural Productivity"
            ]),
            "{research_objective}": random.choice([
                "the effectiveness of AI-driven diagnostic tools",
                "sustainable practices in modern business",
                "consumer behavior patterns in digital markets",
                "emerging technology adoption rates"
            ]),
            "{research_goal}": random.choice([
                "improve diagnostic accuracy",
                "reduce environmental impact",
                "enhance customer engagement",
                "optimize operational efficiency"
            ]),
            "{methodology_type}": random.choice(["quantitative", "qualitative", "mixed-methods", "experimental"]),
            "{expected_outcomes}": random.choice([
                "improved patient outcomes and reduced costs",
                "significant environmental benefits",
                "enhanced business performance metrics",
                "validated theoretical frameworks"
            ]),
            "{department}": random.choice(["Computer Science", "Business Administration", "Engineering", "Psychology", "Biology"]),
            "{institution_name}": f"{fake.city()} University",
            "{course_name}": random.choice([
                "Advanced Database Systems",
                "Financial Analysis and Planning",
                "Organizational Behavior",
                "Software Engineering Principles",
                "Research Methods in Psychology"
            ]),
            "{course_code}": f"{random.choice(['CS', 'BUS', 'ENG', 'PSY', 'BIO'])}{random.randint(300, 600)}",
            "{credit_hours}": random.randint(3, 4),
            "{instructor_name}": f"Dr. {fake.name()}",
            "{office_location}": f"Room {random.randint(100, 500)}",
            "{instructor_email}": f"{fake.first_name().lower()}.{fake.last_name().lower()}@university.edu",
            "{office_hours}": "Tuesday/Thursday 2:00-4:00 PM",
            
            # Manufacturing data
            "{part_number}": f"PN-{random.randint(10000, 99999)}",
            "{material_type}": random.choice(["Aluminum 6061", "Steel 4140", "Stainless 316", "Titanium Grade 2"]),
            "{material_grade}": random.choice(["Grade A", "Grade B", "Premium", "Standard"]),
            "{hardness_rating}": random.randint(30, 60),
            "{surface_finish}": round(random.uniform(0.8, 3.2), 1),
            "{length}": round(random.uniform(10, 100), 2),
            "{width}": round(random.uniform(5, 50), 2),
            "{height}": round(random.uniform(2, 20), 2),
            "{weight}": round(random.uniform(50, 500), 1),
            "{length_tolerance}": round(random.uniform(0.01, 0.1), 2),
            "{width_tolerance}": round(random.uniform(0.01, 0.1), 2),
            "{height_tolerance}": round(random.uniform(0.01, 0.1), 2),
            "{weight_tolerance}": round(random.uniform(1, 10), 1),
            "{check_frequency}": random.randint(50, 200),
            "{test_intervals}": f"every {random.randint(2, 8)} hours",
            "{major_defect_limit}": round(random.uniform(0.5, 2.0), 1),
            "{minor_defect_limit}": round(random.uniform(3.0, 8.0), 1),
            "{cpk_requirement}": round(random.uniform(1.33, 2.0), 2),
            "{retention_years}": random.randint(5, 10),
            "{quality_manager}": fake.name(),
            
            # Chemical/Safety data
            "{chemical_name}": random.choice([
                "Isopropyl Alcohol", "Acetone", "Methylene Chloride", 
                "Toluene", "Benzene", "Ethyl Acetate"
            ]),
            "{product_code}": f"CHM-{random.randint(1000, 9999)}",
            "{cas_number}": f"{random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(0, 9)}",
            "{concentration}": round(random.uniform(85, 99), 1),
            "{hazard_classification}": random.choice(["Flammable Liquid", "Toxic", "Corrosive", "Irritant"]),
            "{signal_word}": random.choice(["DANGER", "WARNING"]),
            "{exposure_limit}": random.randint(50, 500),
            "{min_temp}": random.randint(-20, 5),
            "{max_temp}": random.randint(25, 40),
            
            # Retail data
            "{variance_tolerance}": round(random.uniform(1.0, 5.0), 1),
            "{turnover_target}": random.randint(4, 12),
            "{stockout_target}": round(random.uniform(1.0, 5.0), 1),
            "{shrinkage_target}": round(random.uniform(0.5, 2.0), 1),
            "{margin_target}": round(random.uniform(25, 45), 1)
        }
        
        # Apply replacements
        for placeholder, value in replacements.items():
            content = content.replace(placeholder, str(value))
        
        return content
    
    def _determine_access_level(self, template: Dict, category: str) -> str:
        """Determine appropriate access level based on content"""
        if category in ["finance", "hr"] and "confidential" in template.get("metadata", {}):
            return "confidential"
        elif category == "legal" or "agreement" in template["title"].lower():
            return "private"
        elif category in ["marketing", "technical"] and "internal" in template.get("metadata", {}):
            return "internal"
        else:
            return "public"
    
    def _generate_realistic_tags(self, category: str, template: Dict) -> List[str]:
        """Generate realistic tags based on content"""
        base_tags = [category]
        
        # Add content-specific tags
        title_words = template["title"].lower().split()
        content_tags = [word for word in title_words if len(word) > 3 and word not in ["the", "and", "for", "with"]]
        
        # Add category-specific tags
        category_tags = {
            "legal": ["compliance", "policy", "agreement", "terms"],
            "finance": ["budget", "revenue", "expenses", "analysis"],
            "hr": ["employee", "policy", "benefits", "training"],
            "technical": ["documentation", "api", "system", "guide"],
            "marketing": ["campaign", "strategy", "analysis", "proposal"],
            "operations": ["procedure", "process", "workflow", "manual"],
            "healthcare": ["patient", "medical", "hipaa", "safety", "protocol"],
            "real_estate": ["property", "contract", "appraisal", "listing", "disclosure"],
            "academic": ["research", "thesis", "course", "university", "education"],
            "manufacturing": ["quality", "specification", "safety", "production", "iso"],
            "retail": ["inventory", "sales", "customer", "merchandise", "store"]
        }
        
        base_tags.extend(random.sample(category_tags.get(category, []), k=min(3, len(category_tags.get(category, [])))))
        base_tags.extend(content_tags[:2])
        
        return list(set(base_tags))  # Remove duplicates
    
    def _add_document_variation(self, template: Dict, category: str, variation_num: int) -> Dict:
        """Add variation to document template for uniqueness"""
        varied_template = template.copy()
        
        # Add variation to title
        title_variations = {
            "legal": ["Agreement", "Contract", "Policy", "Terms", "Framework", "Protocol"],
            "finance": ["Report", "Analysis", "Statement", "Summary", "Dashboard", "Forecast"],
            "hr": ["Policy", "Handbook", "Guide", "Manual", "Procedure", "Framework"],
            "technical": ["Guide", "Documentation", "Manual", "Specification", "Reference", "Tutorial"],
            "marketing": ["Strategy", "Campaign", "Analysis", "Proposal", "Plan", "Report"],
            "operations": ["Procedure", "Protocol", "Manual", "Guide", "Playbook", "Framework"],
            "healthcare": ["Policy", "Protocol", "Guideline", "Procedure", "Manual", "Standard"],
            "real_estate": ["Agreement", "Contract", "Report", "Disclosure", "Analysis", "Summary"],
            "academic": ["Research", "Study", "Analysis", "Review", "Thesis", "Paper"],
            "manufacturing": ["Specification", "Standard", "Protocol", "Manual", "Guide", "Procedure"],
            "retail": ["Policy", "Manual", "Guide", "Procedure", "Standard", "Protocol"]
        }
        
        # Add variation suffixes
        variation_suffixes = [
            f"Q{random.randint(1,4)} {random.randint(2020, 2025)}",
            f"{random.choice(['Draft', 'Final', 'Revised', 'Updated', 'Amended'])}",
            f"Version {random.randint(1, 10)}.{random.randint(0, 9)}",
            f"{random.choice(['Annual', 'Monthly', 'Quarterly', 'Weekly'])}",
            f"{fake.company().split()[0]}",
            f"{random.choice(['North', 'South', 'East', 'West', 'Central'])} Region",
            f"Department {random.choice(['A', 'B', 'C', 'Alpha', 'Beta', 'Gamma'])}",
            f"{random.choice(['Phase', 'Stage', 'Level'])} {random.randint(1, 5)}"
        ]
        
        # Modify title with variations
        base_title = template["title"]
        if variation_num > 0:
            if random.random() < 0.6:  # 60% chance of adding suffix
                suffix = random.choice(variation_suffixes)
                base_title = f"{base_title} - {suffix}"
            
            if random.random() < 0.4:  # 40% chance of changing document type
                variations = title_variations.get(category, ["Document"])
                new_type = random.choice(variations)
                base_title = base_title.replace(template["title"].split()[0], new_type)
        
        varied_template["title"] = base_title
        
        # Add content variations
        content_variations = [
            "CONFIDENTIAL - Internal Use Only\n\n",
            "DRAFT - For Review\n\n", 
            "FINAL VERSION\n\n",
            "UPDATED EDITION\n\n",
            "",  # No prefix
        ]
        
        content_prefix = random.choice(content_variations)
        varied_template["content"] = content_prefix + template["content"]
        
        return varied_template
    
    async def generate_realistic_conversations(self, session: AsyncSession, users: Dict[str, Any], documents: List[Document]) -> List[Conversation]:
        """Generate realistic business conversations"""
        logger.info("💬 Creating realistic business conversations...")
        
        conversation_scenarios = [
            {
                "title": "Contract Review Discussion",
                "user_type": "reviewer",
                "document_category": "legal",
                "messages": [
                    {"role": "user", "content": "I need to review the new software license agreement. Can you summarize the key terms and highlight any potential issues?"},
                    {"role": "assistant", "content": "Based on the license agreement, here are the key terms: [1] Non-exclusive license with standard restrictions on reverse engineering, [2] Termination clause allows either party to end with written notice, [3] Liability is limited to indirect damages only. The main concerns I see are the broad termination clause and lack of service level guarantees."},
                    {"role": "user", "content": "What about the intellectual property provisions? Are our derivative works protected?"},
                    {"role": "assistant", "content": "The agreement doesn't explicitly address derivative works. I recommend adding a clause that clarifies ownership of any customizations or integrations we develop using their software."}
                ]
            },
            {
                "title": "Budget Analysis Deep Dive",
                "user_type": "finance",
                "document_category": "finance", 
                "messages": [
                    {"role": "user", "content": "Looking at our Q4 financial report, can you explain the variance in our operating expenses compared to budget?"},
                    {"role": "assistant", "content": "The operating expense variance shows we're 12% over budget, primarily driven by: [1] Unplanned technology infrastructure costs ($150K), [2] Higher than expected professional services fees ($85K), and [3] Increased marketing spend for the product launch ($65K). The technology costs were necessary for scaling, and the marketing investment is showing positive ROI."},
                    {"role": "user", "content": "How does this impact our cash flow projections for next quarter?"},
                    {"role": "assistant", "content": "With current burn rate and the additional expenses, we're projecting 18 months of runway instead of the planned 24 months. However, if the marketing investment continues to drive the current 15% MoM revenue growth, we'll be cash flow positive by Q3 next year."}
                ]
            },
            {
                "title": "Technical Documentation Review",
                "user_type": "technical",
                "document_category": "technical",
                "messages": [
                    {"role": "user", "content": "I'm reviewing the API integration guide. The authentication section seems incomplete. Can you help identify what's missing?"},
                    {"role": "assistant", "content": "Looking at the API guide, I notice several gaps in the authentication section: [1] No examples of token refresh workflows, [2] Missing error handling for expired tokens, [3] No guidance on rate limiting headers, [4] Webhook authentication is not covered. These are critical for production integrations."},
                    {"role": "user", "content": "Can you suggest improvements for the error handling section?"},
                    {"role": "assistant", "content": "I recommend adding: [1] Complete error code reference with descriptions, [2] Example error responses for each endpoint, [3] Retry logic guidelines for transient errors, [4] Debugging tips for common integration issues. This would significantly improve the developer experience."}
                ]
            },
            {
                "title": "Compliance Audit Preparation",
                "user_type": "compliance",
                "document_category": "compliance",
                "messages": [
                    {"role": "user", "content": "We have an upcoming SOC 2 audit. Can you help me identify which documents and processes we need to review for data security controls?"},
                    {"role": "assistant", "content": "For SOC 2 data security controls, you'll need to review: [1] Data classification policies and procedures, [2] Access control documentation showing role-based permissions, [3] Encryption implementation for data at rest and in transit, [4] Incident response procedures and any security incidents, [5] Employee security training records. I can help you gather evidence for each control area."},
                    {"role": "user", "content": "What about the audit logs? How far back should our documentation go?"},
                    {"role": "assistant", "content": "For SOC 2, you typically need 12 months of audit logs demonstrating consistent control operation. Our system retains logs for 7 years, so we're well covered. Focus on showing: user access reviews, privilege changes, failed login attempts, and administrative actions. The audit trail should demonstrate continuous monitoring and timely response to anomalies."}
                ]
            }
        ]
        
        created_conversations = []
        
        for scenario in conversation_scenarios:
            # Find appropriate user
            user_key = self._find_user_by_type(scenario["user_type"], users)
            if not user_key:
                continue
                
            user_data = users[user_key]
            user = user_data["user"]
            
            conversation = Conversation(
                title=scenario["title"],
                user_id=user.id,
                tenant_id=uuid.uuid4(),
                metadata={
                    "conversation_type": "business_discussion",
                    "category": scenario["document_category"],
                    "user_department": user_data["department"],
                    "user_title": user_data["title"],
                    "business_context": True,
                    "generated_at": datetime.now().isoformat()
                }
            )
            
            session.add(conversation)
            await session.flush()
            
            # Add realistic messages with business context
            for i, msg_data in enumerate(scenario["messages"]):
                message = Message(
                    conversation_id=conversation.id,
                    role=msg_data["role"],
                    content=msg_data["content"],
                    metadata={
                        "message_index": i,
                        "business_context": True,
                        "expertise_level": "professional",
                        "timestamp": (datetime.now() - timedelta(days=random.randint(1, 30)) + timedelta(minutes=i*5)).isoformat()
                    }
                )
                session.add(message)
            
            created_conversations.append(conversation)
            logger.info(f"Created business conversation: {scenario['title']} ({user_data['title']})")
        
        return created_conversations
    
    def _find_user_by_type(self, user_type: str, users: Dict[str, Any]) -> str:
        """Find user by type/department"""
        type_mapping = {
            "reviewer": [k for k in users.keys() if users[k]["user"].role == UserRole.REVIEWER],
            "finance": [k for k in users.keys() if "finance" in users[k]["department"]],
            "technical": [k for k in users.keys() if "engineering" in users[k]["department"]],
            "compliance": [k for k in users.keys() if users[k]["user"].role == UserRole.COMPLIANCE]
        }
        
        candidates = type_mapping.get(user_type, [])
        return random.choice(candidates) if candidates else None
    
    async def generate_realistic_audit_trail(self, session: AsyncSession, users: Dict[str, Any], documents: List[Document]):
        """Generate realistic audit trail showing actual business workflows"""
        logger.info("📊 Creating realistic audit trail...")
        
        # Simulate realistic business workflows over past 6 months
        start_date = datetime.now() - timedelta(days=180)
        
        # Document lifecycle events
        for document in documents:
            uploader = None
            for user_data in users.values():
                if user_data["user"].id == document.uploaded_by:
                    uploader = user_data
                    break
            
            if not uploader:
                continue
            
            # Upload event
            upload_time = fake.date_time_between(start_date=start_date, end_date='now')
            audit_log = AuditLog(
                user_id=uploader["user"].id,
                user_email=uploader["user"].email,
                user_role=uploader["user"].role.value,
                action="upload",
                resource_type="document",
                resource_id=str(document.id),
                ip_address=fake.ipv4_private(),
                user_agent=fake.user_agent(),

                details={
                    "filename": document.filename,
                    "file_size": document.file_size,
                    "department": uploader["department"],
                    "business_justification": f"Required for {uploader['department']} operations"
                }
            )
            session.add(audit_log)
            
            # Simulate document views by appropriate roles
            viewers = self._get_potential_viewers(document, users)
            for viewer_key in random.sample(viewers, k=min(len(viewers), random.randint(1, 4))):
                viewer_data = users[viewer_key]
                view_time = fake.date_time_between(start_date=upload_time, end_date='now')
                
                audit_log = AuditLog(
                    user_id=viewer_data["user"].id,
                    user_email=viewer_data["user"].email,
                    user_role=viewer_data["user"].role.value,
                    action="view",
                    resource_type="document",
                    resource_id=str(document.id),
                    ip_address=fake.ipv4_private(),
                    user_agent=fake.user_agent(),

                    details={
                        "filename": document.filename,
                        "access_reason": f"Required for {viewer_data['department']} review",
                        "view_duration": random.randint(30, 600)  # seconds
                    }
                )
                session.add(audit_log)
        
        # User management events (admin actions)
        admin_users = [k for k, v in users.items() if v["user"].role == UserRole.ADMIN]
        
        for admin_key in admin_users:
            admin_data = users[admin_key]
            
            # Simulate user management activities
            management_actions = ["user_created", "role_updated", "access_granted", "password_reset"]
            
            for _ in range(random.randint(2, 5)):
                action = random.choice(management_actions)
                target_user_key = random.choice(list(users.keys()))
                target_user_data = users[target_user_key]
                
                audit_log = AuditLog(
                    user_id=admin_data["user"].id,
                    user_email=admin_data["user"].email,
                    user_role=admin_data["user"].role.value,
                    action=action,
                    resource_type="user",
                    resource_id=str(target_user_data["user"].id),
                    ip_address=fake.ipv4_private(),
                    user_agent=fake.user_agent(),

                    details={
                        "target_user": target_user_data["user"].email,
                        "admin_justification": f"Routine {action.replace('_', ' ')} for business operations",
                        "approval_level": "manager_approved"
                    }
                )
                session.add(audit_log)
        
        logger.info("Created realistic audit trail covering 6 months of business operations")
    
    def _get_potential_viewers(self, document: Document, users: Dict[str, Any]) -> List[str]:
        """Get users who would realistically view this document"""
        viewers = []
        
        # Admins can view everything
        viewers.extend([k for k, v in users.items() if v["user"].role == UserRole.ADMIN])
        
        # Compliance can view everything for audit purposes
        viewers.extend([k for k, v in users.items() if v["user"].role == UserRole.COMPLIANCE])
        
        # Reviewers can view most documents
        if document.access_level in ["public", "internal", "private"]:
            viewers.extend([k for k, v in users.items() if v["user"].role == UserRole.REVIEWER])
        
        # Department-specific access
        if hasattr(document, 'custom_metadata') and document.custom_metadata:
            doc_dept = document.custom_metadata.get("uploader_department", "")
            viewers.extend([k for k, v in users.items() if v["department"] == doc_dept])
        
        # Public documents - everyone can view
        if document.access_level == "public":
            viewers.extend(list(users.keys()))
        
        return list(set(viewers))  # Remove duplicates
    
    async def run_generation(self, clean_existing: bool = False):
        """Run the complete realistic seed data generation"""
        logger.info("🚀 Generating realistic business data for inDoc...")
        
        async with AsyncSessionLocal() as session:
            if clean_existing:
                await self._clean_test_data(session)
            
            # Generate realistic users
            users = await self.generate_realistic_users(session)
            
            # Generate realistic documents
            documents = await self.generate_realistic_documents(session, users)
            
            # Generate realistic conversations
            conversations = await self.generate_realistic_conversations(session, users, documents)
            
            # Generate realistic audit trail
            await self.generate_realistic_audit_trail(session, users, documents)
            
            await session.commit()
            
            # Print business summary
            await self._print_business_summary(session, users)
    
    async def _clean_test_data(self, session: AsyncSession):
        """Clean existing test data"""
        logger.info("🧹 Cleaning existing test data...")
        
        # Delete test data (preserve original admin user)
        await session.execute(delete(AuditLog).where(AuditLog.user_email.like('%@%')))
        await session.execute(delete(Message))
        await session.execute(delete(Conversation))
        await session.execute(delete(Document))
        await session.execute(delete(User).where(User.email != 'admin@indoc.local'))
        
        await session.commit()
        logger.info("✅ Test data cleaned")
    
    async def _print_business_summary(self, session: AsyncSession, users: Dict[str, Any]):
        """Print business-focused summary"""
        logger.info("📋 BUSINESS DATA SUMMARY")
        logger.info("=" * 60)
        
        # Department breakdown
        departments = {}
        for user_data in users.values():
            dept = user_data["department"]
            role = user_data["user"].role.value
            if dept not in departments:
                departments[dept] = {}
            departments[dept][role] = departments[dept].get(role, 0) + 1
        
        logger.info("🏢 ORGANIZATIONAL STRUCTURE")
        for dept, roles in departments.items():
            logger.info(f"  {dept.title()}: {sum(roles.values())} employees")
            for role, count in roles.items():
                logger.info(f"    - {role}: {count}")
        
        # Document summary
        result = await session.execute(select(Document))
        documents = result.scalars().all()
        
        doc_categories = {}
        access_levels = {}
        
        for doc in documents:
            if hasattr(doc, 'custom_metadata') and doc.custom_metadata:
                category = doc.custom_metadata.get("category", "unknown")
                doc_categories[category] = doc_categories.get(category, 0) + 1
            
            access_levels[doc.access_level] = access_levels.get(doc.access_level, 0) + 1
        
        logger.info("\n📄 DOCUMENT PORTFOLIO")
        for category, count in doc_categories.items():
            logger.info(f"  {category.title()}: {count} documents")
        
        logger.info("\n🔒 ACCESS LEVEL DISTRIBUTION")
        for level, count in access_levels.items():
            logger.info(f"  {level.title()}: {count} documents")
        
        # Audit activity
        result = await session.execute(select(AuditLog))
        audit_count = len(result.scalars().all())
        
        logger.info(f"\n📊 AUDIT ACTIVITY: {audit_count} events logged")
        
        # Business user credentials
        logger.info("\n🔑 BUSINESS USER CREDENTIALS")
        logger.info("=" * 60)
        logger.info(f"{'Role':<12} | {'Name':<25} | {'Department':<15} | {'Email':<35}")
        logger.info("-" * 60)
        
        for user_data in users.values():
            user = user_data["user"]
            logger.info(f"{user.role.value:<12} | {user.full_name:<25} | {user_data['department']:<15} | {user.email}")
        
        logger.info("=" * 60)
        logger.info("💡 Passwords are randomly generated - use 'Forgot Password' or reset via admin")


async def main():
    """Main function"""
    generator = RealisticSeedGenerator()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--clean":
        logger.warning("⚠️  This will clean existing data and generate fresh realistic business data!")
        
        # Check for auto-confirmation
        force_yes = "--yes" in sys.argv or os.getenv("INDOC_YES") == "1"
        if not force_yes:
            response = input("Continue? (y/N): ")
            if response.lower() != 'y':
                logger.info("Cancelled")
                return
        else:
            logger.info("Auto-confirmed via environment variable")
            
        await generator.run_generation(clean_existing=True)
    else:
        await generator.run_generation(clean_existing=False)


if __name__ == "__main__":
    asyncio.run(main())
