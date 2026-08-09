import { useState, useEffect, useCallback } from 'react';
import { createDefaultPipelineSteps } from '../components/DocumentProcessingPipeline';

interface ProcessingStep {
    id: string;
    label: string;
    icon: React.ReactElement;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    progress?: number;
    message?: string;
    duration?: number;
    details?: string[];
}

interface DocumentProcessingState {
    documentId: string;
    filename: string;
    fileType: string;
    fileSize: number;
    status: 'uploaded' | 'processing' | 'indexed' | 'failed';
    currentStep: string;
    steps: ProcessingStep[];
    startTime: Date;
    estimatedCompletion?: Date;
    errorMessage?: string;
}

interface ProcessingUpdate {
    documentId: string;
    step: string;
    status: 'processing' | 'completed' | 'failed';
    progress?: number;
    message?: string;
    details?: string[];
    errorMessage?: string;
}

export const useDocumentProcessing = () => {
    const [processingDocuments, setProcessingDocuments] = useState<Map<string, DocumentProcessingState>>(new Map());
    const [ws, setWs] = useState<WebSocket | null>(null);

    // Initialize WebSocket connection for real-time updates
    useEffect(() => {
        const connectWebSocket = () => {
            // Get JWT token from localStorage or Redux store
            const token = localStorage.getItem('token') || '';
            const websocket = new WebSocket(`ws://localhost:8000/ws/processing?token=${token}`);
            
            websocket.onopen = () => {
                console.log('📡 Processing WebSocket connected');
                setWs(websocket);
            };

            websocket.onmessage = (event) => {
                try {
                    const update: ProcessingUpdate = JSON.parse(event.data);
                    handleProcessingUpdate(update);
                } catch (error) {
                    console.error('Failed to parse processing update:', error);
                }
            };

            websocket.onclose = () => {
                console.log('📡 Processing WebSocket disconnected, reconnecting...');
                setTimeout(connectWebSocket, 3000); // Reconnect after 3 seconds
            };

            websocket.onerror = (error) => {
                console.error('Processing WebSocket error:', error);
            };
        };

        connectWebSocket();

        return () => {
            if (ws) {
                ws.close();
            }
        };
    }, []);

    const handleProcessingUpdate = useCallback((update: ProcessingUpdate) => {
        setProcessingDocuments(prev => {
            const newMap = new Map(prev);
            const doc = newMap.get(update.documentId);
            
            if (!doc) return prev;

            // Update the specific step
            const updatedSteps = doc.steps.map(step => {
                if (step.id === update.step) {
                    return {
                        ...step,
                        status: update.status,
                        progress: update.progress,
                        message: update.message || step.message,
                        details: update.details || step.details
                    };
                }
                return step;
            });

            // Determine overall document status
            let documentStatus: 'uploaded' | 'processing' | 'indexed' | 'failed' = 'processing';
            if (update.status === 'failed') {
                documentStatus = 'failed';
            } else if (updatedSteps.every(step => step.status === 'completed')) {
                documentStatus = 'indexed';
            }

            // Update next step to processing if current completed
            if (update.status === 'completed') {
                const currentStepIndex = updatedSteps.findIndex(s => s.id === update.step);
                if (currentStepIndex >= 0 && currentStepIndex < updatedSteps.length - 1) {
                    updatedSteps[currentStepIndex + 1] = {
                        ...updatedSteps[currentStepIndex + 1],
                        status: 'processing',
                        progress: 0
                    };
                }
            }

            const updatedDoc: DocumentProcessingState = {
                ...doc,
                status: documentStatus,
                currentStep: update.step,
                steps: updatedSteps,
                errorMessage: update.errorMessage || doc.errorMessage
            };

            newMap.set(update.documentId, updatedDoc);
            return newMap;
        });
    }, []);

    const addDocumentToProcessing = useCallback((
        documentId: string,
        filename: string,
        fileType: string,
        fileSize: number
    ) => {
        const newDoc: DocumentProcessingState = {
            documentId,
            filename,
            fileType,
            fileSize,
            status: 'uploaded',
            currentStep: 'upload',
            steps: createDefaultPipelineSteps(filename),
            startTime: new Date()
        };

        setProcessingDocuments(prev => {
            const newMap = new Map(prev);
            newMap.set(documentId, newDoc);
            return newMap;
        });
    }, []);

    const removeDocumentFromProcessing = useCallback((documentId: string) => {
        setProcessingDocuments(prev => {
            const newMap = new Map(prev);
            newMap.delete(documentId);
            return newMap;
        });
    }, []);

    const retryProcessing = useCallback((documentId: string) => {
        const doc = processingDocuments.get(documentId);
        if (!doc) return;

        // Reset failed steps to pending
        const resetSteps = doc.steps.map(step => ({
            ...step,
            status: step.status === 'failed' ? 'pending' as const : step.status,
            progress: undefined,
            message: step.status === 'failed' ? undefined : step.message
        }));

        // Find first failed/pending step and set to processing
        const firstPendingIndex = resetSteps.findIndex(s => s.status === 'pending');
        if (firstPendingIndex >= 0) {
            resetSteps[firstPendingIndex] = {
                ...resetSteps[firstPendingIndex],
                status: 'processing',
                progress: 0
            };
        }

        const updatedDoc: DocumentProcessingState = {
            ...doc,
            status: 'processing',
            steps: resetSteps,
            errorMessage: undefined,
            startTime: new Date()
        };

        setProcessingDocuments(prev => {
            const newMap = new Map(prev);
            newMap.set(documentId, updatedDoc);
            return newMap;
        });

        // Send retry request to backend
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'retry_processing',
                documentId
            }));
        }
    }, [processingDocuments, ws]);

    const cancelProcessing = useCallback((documentId: string) => {
        // Send cancel request to backend
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'cancel_processing',
                documentId
            }));
        }

        removeDocumentFromProcessing(documentId);
    }, [ws, removeDocumentFromProcessing]);

    // Convert Map to Array for easier consumption by components
    const processingDocumentsArray = Array.from(processingDocuments.values());

    // Get processing statistics
    const getProcessingStats = useCallback(() => {
        const docs = processingDocumentsArray;
        return {
            total: docs.length,
            processing: docs.filter(d => d.status === 'processing').length,
            completed: docs.filter(d => d.status === 'indexed').length,
            failed: docs.filter(d => d.status === 'failed').length
        };
    }, [processingDocumentsArray]);

    return {
        processingDocuments: processingDocumentsArray,
        addDocumentToProcessing,
        removeDocumentFromProcessing,
        retryProcessing,
        cancelProcessing,
        getProcessingStats,
        isConnected: ws?.readyState === WebSocket.OPEN
    };
};
