import { createSlice, PayloadAction } from '@reduxjs/toolkit'

interface Document {
  id: string
  filename: string
  title: string
  file_type: string
  status: string
  created_at: string
}

interface DocumentState {
  documents: Document[]
  currentDocument: Document | null
  isLoading: boolean
  error: string | null
}

const initialState: DocumentState = {
  documents: [],
  currentDocument: null,
  isLoading: false,
  error: null,
}

const documentSlice = createSlice({
  name: 'document',
  initialState,
  reducers: {
    setDocuments: (state, action: PayloadAction<Document[]>) => {
      state.documents = action.payload
    },
    setCurrentDocument: (state, action: PayloadAction<Document | null>) => {
      state.currentDocument = action.payload
    },
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload
    },
  },
})

export const { setDocuments, setCurrentDocument, setLoading, setError } = documentSlice.actions
export default documentSlice.reducer