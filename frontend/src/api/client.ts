import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 응답 인터셉터
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // 인증 만료 시 로그인 페이지로 리다이렉트
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// API 함수들
export const authApi = {
  login: (email: string, password: string) =>
    apiClient.post('/auth/login', { email, password }),
  logout: () => apiClient.post('/auth/logout'),
  me: () => apiClient.get('/auth/me'),
}

export const usersApi = {
  getCareUsers: (params?: { page?: number; limit?: number }) =>
    apiClient.get('/users/care-users', { params }),
  getCareUser: (id: string) =>
    apiClient.get(`/users/care-users/${id}`),
  createCareUser: (data: any) =>
    apiClient.post('/users/care-users', data),
}

export const casesApi = {
  getCases: (params?: { status?: string; page?: number; limit?: number }) =>
    apiClient.get('/cases', { params }),
  getCase: (id: string) =>
    apiClient.get(`/cases/${id}`),
  updateCaseStatus: (id: string, status: string) =>
    apiClient.patch(`/cases/${id}/status`, { status }),
}

export const devicesApi = {
  getDevices: (params?: { status?: string; page?: number; limit?: number }) =>
    apiClient.get('/devices', { params }),
  getDevice: (id: string) =>
    apiClient.get(`/devices/${id}`),
}

export const statsApi = {
  getDashboard: () =>
    apiClient.get('/health'),
}
