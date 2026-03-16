import axios from 'axios'

const BASE = 'http://localhost:8000'

export const api = {
  health: () =>
    axios.get(`${BASE}/api/health`),

  analyze: (formData) =>
    axios.post(`${BASE}/api/analyze`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  submitQualitative: (data) =>
    axios.post(`${BASE}/api/qualitative`, data),

  generateCAM: (analysisId) =>
    axios.post(`${BASE}/api/generate-cam?analysis_id=${analysisId}`, {}, {
      responseType: 'blob',
    }),

  getAnalysis: (analysisId) =>
    axios.get(`${BASE}/api/analysis/${analysisId}`),
}