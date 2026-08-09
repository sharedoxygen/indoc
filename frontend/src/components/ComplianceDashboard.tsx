import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  CardActions,
  Button,
  Chip,
  Switch,
  FormControlLabel,
  Alert,
  AlertTitle,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
  LinearProgress,
  Badge,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';
import {
  Security as SecurityIcon,
  HealthAndSafety as HipaaIcon,
  CreditCard as PciIcon,
  Shield as ShieldIcon,
  Warning as WarningIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Visibility as ViewIcon,
  Download as DownloadIcon,
  Settings as SettingsIcon,
  Timeline as TimelineIcon,
  Assessment as ReportIcon,
  NotificationImportant as AlertIcon,
  Lock as EncryptionIcon,
  Audit as AuditIcon,
  Gavel as ComplianceIcon,
} from '@mui/icons-material';
import { formatDistanceToNow } from 'date-fns';

interface ComplianceMode {
  mode: string;
  name: string;
  description: string;
  features: Record<string, any>;
  requirements: string[];
  recommended_for: string[];
}

interface ComplianceStatus {
  current_mode: string;
  configuration: Record<string, any>;
  health_checks: Record<string, any>;
  recommendations: string[];
  alerts: Array<{
    level: string;
    message: string;
  }>;
  last_updated: string;
}

interface PHIScanResult {
  phi_found: boolean;
  detections: Array<{
    type: string;
    description: string;
    sensitivity: string;
    matched_text: string;
    redacted_replacement: string;
  }>;
  redacted_text: string;
  high_sensitivity_count: number;
  scan_timestamp: string;
  compliance_mode: string;
}

export const ComplianceDashboard: React.FC = () => {
  const [complianceModes, setComplianceModes] = useState<ComplianceMode[]>([]);
  const [complianceStatus, setComplianceStatus] = useState<ComplianceStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showModeDialog, setShowModeDialog] = useState(false);
  const [selectedMode, setSelectedMode] = useState('');
  const [justification, setJustification] = useState('');
  const [scanText, setScanText] = useState('');
  const [scanResult, setScanResult] = useState<PHIScanResult | null>(null);
  const [showScanDialog, setShowScanDialog] = useState(false);

  useEffect(() => {
    loadComplianceData();
  }, []);

  const loadComplianceData = async () => {
    try {
      setIsLoading(true);
      
      // Mock API calls - replace with actual API
      const modes: ComplianceMode[] = [
        {
          mode: 'standard',
          name: 'Standard',
          description: 'Basic security with standard audit logging',
          features: {
            phi_detection: 'basic',
            audit_retention_days: 90,
            encryption_required: false,
          },
          requirements: ['Basic audit logging', 'Standard access controls'],
          recommended_for: ['General business documents', 'Internal communications'],
        },
        {
          mode: 'hipaa',
          name: 'HIPAA Compliant',
          description: 'Healthcare compliance with PHI protection',
          features: {
            phi_detection: 'comprehensive',
            audit_retention_days: 2555,
            encryption_required: true,
            auto_redaction: true,
          },
          requirements: [
            'Business Associate Agreement (BAA) required',
            'Patient consent for data processing',
            'Minimum necessary rule enforcement',
            'Employee HIPAA training required',
          ],
          recommended_for: ['Healthcare organizations', 'Patient records', 'Medical research'],
        },
        {
          mode: 'pci_dss',
          name: 'PCI DSS',
          description: 'Payment card industry compliance',
          features: {
            phi_detection: 'financial',
            audit_retention_days: 365,
            encryption_required: true,
            tokenization: true,
          },
          requirements: [
            'Secure cardholder data storage',
            'Strong access control measures',
            'Regular security testing',
          ],
          recommended_for: ['Payment processing', 'E-commerce', 'Financial services'],
        },
      ];

      const status: ComplianceStatus = {
        current_mode: 'standard',
        configuration: {
          phi_detection: 'basic',
          audit_retention_days: 90,
          encryption_required: false,
          auto_redaction: false,
        },
        health_checks: {
          encryption_enabled: false,
          audit_logging: 'standard',
          phi_detection: 'basic',
          auto_redaction: false,
        },
        recommendations: [
          'Consider enabling enhanced compliance mode for better security',
          'Review data handling procedures',
          'Implement regular security training',
        ],
        alerts: [
          {
            level: 'info',
            message: 'Consider enabling enhanced compliance mode for better security',
          },
        ],
        last_updated: new Date().toISOString(),
      };

      setComplianceModes(modes);
      setComplianceStatus(status);
    } catch (error) {
      console.error('Error loading compliance data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleModeChange = async () => {
    if (!selectedMode) return;

    try {
      // Mock API call to change compliance mode
      console.log('Changing compliance mode to:', selectedMode, 'Justification:', justification);
      
      // Update local state
      setComplianceStatus(prev => prev ? {
        ...prev,
        current_mode: selectedMode,
      } : null);
      
      setShowModeDialog(false);
      setSelectedMode('');
      setJustification('');
    } catch (error) {
      console.error('Error changing compliance mode:', error);
    }
  };

  const handlePHIScan = async () => {
    if (!scanText.trim()) return;

    try {
      // Mock PHI scan result
      const result: PHIScanResult = {
        phi_found: scanText.toLowerCase().includes('ssn') || scanText.toLowerCase().includes('patient'),
        detections: scanText.toLowerCase().includes('ssn') ? [
          {
            type: 'SSN',
            description: 'Social Security Number',
            sensitivity: 'high',
            matched_text: '123-45-6789',
            redacted_replacement: '[REDACTED-SSN]',
          },
        ] : [],
        redacted_text: scanText.replace(/\b\d{3}-\d{2}-\d{4}\b/g, '[REDACTED-SSN]'),
        high_sensitivity_count: scanText.toLowerCase().includes('ssn') ? 1 : 0,
        scan_timestamp: new Date().toISOString(),
        compliance_mode: complianceStatus?.current_mode || 'standard',
      };

      setScanResult(result);
    } catch (error) {
      console.error('Error scanning for PHI:', error);
    }
  };

  const getComplianceModeInfo = (mode: string) => {
    return complianceModes.find(m => m.mode === mode);
  };

  const getModeIcon = (mode: string) => {
    switch (mode) {
      case 'hipaa':
        return <HipaaIcon color="warning" />;
      case 'pci_dss':
        return <PciIcon color="error" />;
      case 'maximum':
        return <ShieldIcon color="success" />;
      default:
        return <SecurityIcon color="primary" />;
    }
  };

  const getHealthCheckColor = (value: any) => {
    if (typeof value === 'boolean') {
      return value ? 'success' : 'error';
    }
    if (value === 'comprehensive' || value === 'maximum') return 'success';
    if (value === 'detailed' || value === 'enhanced') return 'warning';
    return 'default';
  };

  if (isLoading) {
    return (
      <Box sx={{ p: 3 }}>
        <LinearProgress />
        <Typography variant="body2" sx={{ mt: 2, textAlign: 'center' }}>
          Loading compliance dashboard...
        </Typography>
      </Box>
    );
  }

  const currentModeInfo = getComplianceModeInfo(complianceStatus?.current_mode || 'standard');

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        🔐 Compliance Dashboard
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        Monitor and manage compliance settings, PHI detection, and regulatory requirements.
      </Typography>

      <Grid container spacing={3}>
        {/* Current Compliance Mode */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                {getModeIcon(complianceStatus?.current_mode || 'standard')}
                <Box sx={{ ml: 2 }}>
                  <Typography variant="h6">
                    Current Mode: {currentModeInfo?.name}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {currentModeInfo?.description}
                  </Typography>
                </Box>
              </Box>

              <Divider sx={{ my: 2 }} />

              <Typography variant="subtitle2" gutterBottom>
                Configuration:
              </Typography>
              <List dense>
                {Object.entries(complianceStatus?.health_checks || {}).map(([key, value]) => (
                  <ListItem key={key}>
                    <ListItemIcon>
                      <Chip
                        size="small"
                        color={getHealthCheckColor(value)}
                        label={
                          typeof value === 'boolean'
                            ? value ? 'Enabled' : 'Disabled'
                            : String(value)
                        }
                      />
                    </ListItemIcon>
                    <ListItemText
                      primary={key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    />
                  </ListItem>
                ))}
              </List>
            </CardContent>
            <CardActions>
              <Button
                variant="outlined"
                startIcon={<SettingsIcon />}
                onClick={() => setShowModeDialog(true)}
              >
                Change Mode
              </Button>
              <Button
                variant="outlined"
                startIcon={<ReportIcon />}
              >
                Generate Report
              </Button>
            </CardActions>
          </Card>
        </Grid>

        {/* Alerts & Recommendations */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <AlertIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                Alerts & Recommendations
              </Typography>

              {complianceStatus?.alerts?.map((alert, index) => (
                <Alert
                  key={index}
                  severity={alert.level as any}
                  sx={{ mb: 1 }}
                >
                  {alert.message}
                </Alert>
              ))}

              <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>
                Recommendations:
              </Typography>
              <List dense>
                {complianceStatus?.recommendations?.map((rec, index) => (
                  <ListItem key={index}>
                    <ListItemIcon>
                      <CheckIcon fontSize="small" />
                    </ListItemIcon>
                    <ListItemText primary={rec} />
                  </ListItem>
                ))}
              </List>
            </CardContent>
          </Card>
        </Grid>

        {/* PHI Scanner */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                🔍 PHI Scanner
              </Typography>
              <Typography variant="body2" color="text.secondary" paragraph>
                Scan text for Protected Health Information (PHI) and other sensitive data.
              </Typography>

              <TextField
                fullWidth
                multiline
                rows={4}
                placeholder="Enter text to scan for PHI..."
                value={scanText}
                onChange={(e) => setScanText(e.target.value)}
                sx={{ mb: 2 }}
              />

              <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                <Button
                  variant="contained"
                  onClick={handlePHIScan}
                  disabled={!scanText.trim()}
                >
                  Scan for PHI
                </Button>
                <Button
                  variant="outlined"
                  onClick={() => setScanResult(null)}
                >
                  Clear Results
                </Button>
              </Box>

              {scanResult && (
                <Paper sx={{ p: 2, bgcolor: scanResult.phi_found ? 'error.50' : 'success.50' }}>
                  <Typography variant="h6" gutterBottom>
                    Scan Results
                    <Chip
                      label={scanResult.phi_found ? 'PHI Detected' : 'No PHI Found'}
                      color={scanResult.phi_found ? 'error' : 'success'}
                      sx={{ ml: 2 }}
                    />
                  </Typography>

                  {scanResult.phi_found && (
                    <>
                      <Typography variant="subtitle2" gutterBottom>
                        Detections ({scanResult.detections.length}):
                      </Typography>
                      <TableContainer>
                        <Table size="small">
                          <TableHead>
                            <TableRow>
                              <TableCell>Type</TableCell>
                              <TableCell>Sensitivity</TableCell>
                              <TableCell>Found</TableCell>
                              <TableCell>Redacted</TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {scanResult.detections.map((detection, index) => (
                              <TableRow key={index}>
                                <TableCell>{detection.type}</TableCell>
                                <TableCell>
                                  <Chip
                                    label={detection.sensitivity}
                                    color={detection.sensitivity === 'high' ? 'error' : 'warning'}
                                    size="small"
                                  />
                                </TableCell>
                                <TableCell>
                                  <code>{detection.matched_text}</code>
                                </TableCell>
                                <TableCell>
                                  <code>{detection.redacted_replacement}</code>
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </TableContainer>

                      <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>
                        Redacted Text:
                      </Typography>
                      <Paper sx={{ p: 2, bgcolor: 'grey.100' }}>
                        <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap' }}>
                          {scanResult.redacted_text}
                        </Typography>
                      </Paper>
                    </>
                  )}
                </Paper>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Available Compliance Modes */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Available Compliance Modes
              </Typography>
              <Grid container spacing={2}>
                {complianceModes.map((mode) => (
                  <Grid item xs={12} md={4} key={mode.mode}>
                    <Paper
                      sx={{
                        p: 2,
                        border: complianceStatus?.current_mode === mode.mode ? '2px solid' : '1px solid',
                        borderColor: complianceStatus?.current_mode === mode.mode ? 'primary.main' : 'divider',
                      }}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                        {getModeIcon(mode.mode)}
                        <Typography variant="h6" sx={{ ml: 1 }}>
                          {mode.name}
                        </Typography>
                        {complianceStatus?.current_mode === mode.mode && (
                          <Chip label="Current" size="small" color="primary" sx={{ ml: 'auto' }} />
                        )}
                      </Box>
                      <Typography variant="body2" color="text.secondary" paragraph>
                        {mode.description}
                      </Typography>
                      
                      <Typography variant="subtitle2" gutterBottom>
                        Recommended for:
                      </Typography>
                      <Stack direction="column" spacing={0.5}>
                        {mode.recommended_for.slice(0, 2).map((use, index) => (
                          <Typography key={index} variant="caption" color="text.secondary">
                            • {use}
                          </Typography>
                        ))}
                      </Stack>
                    </Paper>
                  </Grid>
                ))}
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Change Mode Dialog */}
      <Dialog open={showModeDialog} onClose={() => setShowModeDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Change Compliance Mode</DialogTitle>
        <DialogContent>
          <FormControl fullWidth sx={{ mt: 2, mb: 2 }}>
            <InputLabel>Compliance Mode</InputLabel>
            <Select
              value={selectedMode}
              onChange={(e) => setSelectedMode(e.target.value)}
              label="Compliance Mode"
            >
              {complianceModes.map((mode) => (
                <MenuItem key={mode.mode} value={mode.mode}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {getModeIcon(mode.mode)}
                    {mode.name}
                  </Box>
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <TextField
            fullWidth
            multiline
            rows={3}
            label="Justification (Optional)"
            placeholder="Explain why you're changing the compliance mode..."
            value={justification}
            onChange={(e) => setJustification(e.target.value)}
            sx={{ mb: 2 }}
          />

          {selectedMode && (
            <Alert severity="warning">
              <AlertTitle>Important</AlertTitle>
              Changing compliance mode will affect how sensitive data is handled and may require
              additional configuration changes.
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowModeDialog(false)}>Cancel</Button>
          <Button onClick={handleModeChange} variant="contained" disabled={!selectedMode}>
            Change Mode
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ComplianceDashboard;
