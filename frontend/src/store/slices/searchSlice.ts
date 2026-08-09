import { createSlice, PayloadAction } from '@reduxjs/toolkit'

interface SearchResult {
  id: string
  filename: string
  title: string
  snippet: string
  score: number
}

interface SearchState {
  query: string
  results: SearchResult[]
  isSearching: boolean
  totalResults: number
  executionTime: number
}

const initialState: SearchState = {
  query: '',
  results: [],
  isSearching: false,
  totalResults: 0,
  executionTime: 0,
}

const searchSlice = createSlice({
  name: 'search',
  initialState,
  reducers: {
    setQuery: (state, action: PayloadAction<string>) => {
      state.query = action.payload
    },
    setResults: (state, action: PayloadAction<SearchResult[]>) => {
      state.results = action.payload
    },
    setSearching: (state, action: PayloadAction<boolean>) => {
      state.isSearching = action.payload
    },
    setSearchMetrics: (state, action: PayloadAction<{ total: number; time: number }>) => {
      state.totalResults = action.payload.total
      state.executionTime = action.payload.time
    },
    clearSearch: (state) => {
      state.query = ''
      state.results = []
      state.totalResults = 0
      state.executionTime = 0
    },
  },
})

export const { setQuery, setResults, setSearching, setSearchMetrics, clearSearch } = searchSlice.actions
export default searchSlice.reducer